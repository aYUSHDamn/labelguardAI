"""
Extra modules (all zero-LLM):
  /api/products       product explorer over the Indian products table, with family verdicts
  /api/lookup         ingredient / INS decoder ("what is E471, is it OK for my family?")
  /api/insights       patterns across everything you've scanned
  /api/allergy-card   printable allergy & diet card per member (with Indian names)
  /api/shopping       shopping list CRUD
  /api/admin/reset    clear demo history
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import db
from alternatives.ranker import fallback_candidates
from config import CATEGORIES
from errors import APIError
from pipeline import current_household
from rules import data
from rules.engine import AVOID, WARN, analyze, analyze_product, evaluate_member
from rules.text import contains_term, extract_codes, norm
from schemas import Extraction

router = APIRouter(prefix="/api", tags=["extras"])
RANK = {"SAFE": 0, "WARN": 1, "AVOID": 2}


# --------------------------------------------------------------- explorer
@router.get("/products", summary="Browse Indian packaged products with scores and family verdicts")
def products(category: Optional[str] = None, q: Optional[str] = None, member: Optional[str] = None,
             safe_only: bool = False, sort: str = "score"):
    household = current_household()
    targets = [m for m in household.members if member in (None, "", "all") or m.name == member] or household.members
    cats = [category] if category in CATEGORIES else [c for c in CATEGORIES if c != "other"]
    out = []
    for cat in cats:
        for cand in fallback_candidates(cat):
            ex: Extraction = cand["extraction"]
            name = f"{ex.brand} {ex.product_name}".lower()
            if q and q.lower() not in name:
                continue
            pa = analyze_product(ex)
            verdicts = [evaluate_member(m, pa, ex) for m in targets]
            worst = max((v["status"] for v in verdicts), key=RANK.get, default="SAFE")
            if safe_only and worst == AVOID:
                continue
            n = ex.nutrition_per_100g
            out.append({
                "code": cand["code"], "product_name": ex.product_name, "brand": ex.brand, "category": ex.category,
                "score": pa["score"]["score"], "color": pa["score"]["color"], "label": pa["score"]["label"],
                "status": worst, "price_inr": cand["price_inr"],
                "members": [{"member": v["member"], "status": v["status"],
                             "reason": v["flags"][0]["reason"] if v["flags"] else None} for v in verdicts],
                "sugar_g": n.sugar_g, "sodium_mg": n.sodium_mg, "sat_fat_g": n.sat_fat_g, "protein_g": n.protein_g,
                "fiber_g": n.fiber_g, "energy_kcal": n.energy_kcal,
                "sugar_sources": len(pa["hidden_sugars"]),
                "flagged_additives": sum(1 for a in pa["additives"] if a["concern"] in ("medium", "high")),
                "ingredients": ex.ingredients,
            })
    keys = {"score": lambda p: -p["score"], "sugar": lambda p: p["sugar_g"] if p["sugar_g"] is not None else 999,
            "sodium": lambda p: p["sodium_mg"] if p["sodium_mg"] is not None else 99999,
            "protein": lambda p: -(p["protein_g"] or 0), "price": lambda p: p["price_inr"] or 99999}
    out.sort(key=lambda p: (keys.get(sort, keys["score"])(p), p["product_name"]))
    return {"products": out, "count": len(out),
            "categories": [c for c in CATEGORIES if c != "other" and fallback_candidates(c)],
            "note": "Nutrition values are approximate, compiled for this demo. Check the pack before buying."}


# ------------------------------------------------------------- ingredient decoder
@router.get("/lookup", summary="Decode an ingredient / INS code and check it against your family")
def lookup(q: str):
    query = q.strip()
    if len(query) < 2:
        raise APIError(400, "too_short", "Type at least 2 characters, e.g. E471, maltodextrin or gelatin.")
    t = norm(query)
    codes = extract_codes(t) or extract_codes(f"ins {t}")
    entries = []

    for a in data.additives().values():
        if a.ins in codes or t == a.ins or contains_term(a.name.lower(), t) or any(t == al or contains_term(al, t) for al in a.aliases):
            entries.append({"type": "Additive", "title": f"{a.name} (INS {a.ins} / E{a.ins})", "summary": a.purpose,
                            "details": [f"Class: {a.cls.replace('_', ' ')}", f"Concern: {a.concern}", a.note]})
    for alias, row in data.sugar_aliases().items():
        if contains_term(alias, t) or contains_term(t, alias):
            entries.append({"type": "Hidden sugar", "title": alias.title(), "summary": row["note"],
                            "details": [f"Sugar family: {row['group'].replace('_', ' ')}",
                                        "Counts as added sugar in our checks"]})
    for key, al in data.allergen_table()["by_key"].items():
        if any(contains_term(k, t) or contains_term(t, k) for k in al["keywords"] + al["synonyms"] if not k.startswith("ins:")):
            entries.append({"type": "Allergen", "title": al["display"], "summary": "Allergen group we check for",
                            "details": ["Also listed as: " + ", ".join(k for k in al["keywords"] if not k.startswith("ins:"))[:200]]})
    for rule in data.diet_rules():
        hit = [x for x in rule.terms if (x.startswith("ins:") and x[4:] in codes) or (not x.startswith("ins:") and (contains_term(x, t) or contains_term(t, x)))]
        if hit:
            st = ", ".join(f"{d}: {s}" for d, s in rule.status.items())
            names = [x for x in rule.terms if not x.startswith("ins:")]
            title = (hit[0] if not hit[0].startswith("ins:") else (names[0] if names else hit[0].replace("ins:", "INS ")))
            entries.append({"type": "Diet rule", "title": title.title(), "summary": rule.reason,
                            "details": [f"Affects: {st}"]})

    # Run the real rules engine on this one ingredient for every family member.
    probe = Extraction(ingredients=[query if not codes else f"{query} (INS {codes[0]})"])
    result = analyze(probe, current_household())
    family = [{"member": m["member"], "status": m["status"],
               "reasons": [f["reason"] for f in m["flags"] if f["category"] in ("allergen", "diet", "avoid_list", "child", "additive", "condition")]}
              for m in result["members"]]
    return {"query": query, "entries": entries[:12], "family": family, "found": bool(entries)}


# --------------------------------------------------------------------- insights
@router.get("/insights", summary="Patterns across everything you've scanned")
def insights():
    household = current_household()
    scans = db.all_scans_full(200)
    if not scans:
        return {"scan_count": 0}
    sugar_names, additive_names, claims = Counter(), Counter(), Counter()
    by_cat, status_counts = defaultdict(list), {m.name: Counter() for m in household.members}
    misleading, products = 0, []
    for s in scans:
        ex = Extraction.model_validate(s["extraction"])
        a = analyze(ex, household)
        for h in a["hidden_sugars"]:
            sugar_names[h["alias"]] += 1
        for x in a["additives"]:
            if x["concern"] in ("medium", "high"):
                additive_names[f"{x['name']} (INS {x['code']})"] += 1
        for c in a["claims"]:
            if c["verdict"] == "misleading":
                misleading += 1
                claims[c["claim"]] += 1
        by_cat[ex.category].append(a["score"]["score"])
        for m in a["members"]:
            status_counts.setdefault(m["member"], Counter())[m["status"]] += 1
        products.append({"scan_id": s["id"], "product": ex.product_name or f"Scan {s['id']}", "score": a["score"]["score"]})
    uniq = {p["product"]: p for p in products}.values()
    return {
        "scan_count": len(scans),
        "avg_score": round(mean(p["score"] for p in products)),
        "misleading_claims": misleading,
        "top_sugar_names": sugar_names.most_common(8),
        "top_additives": additive_names.most_common(8),
        "top_misleading_claims": claims.most_common(5),
        "category_scores": sorted(([c.replace("_", " "), round(mean(v)), len(v)] for c, v in by_cat.items()),
                                  key=lambda x: x[1]),
        "member_status": [{"member": k, "SAFE": v["SAFE"], "WARN": v["WARN"], "AVOID": v["AVOID"]}
                          for k, v in status_counts.items()],
        "best": sorted(uniq, key=lambda p: -p["score"])[:3],
        "worst": sorted(uniq, key=lambda p: p["score"])[:3],
    }


# ---------------------------------------------------------------- allergy card
JAIN_AVOID = ["onion", "garlic", "potato", "carrot", "beetroot", "radish", "ginger (fresh)", "mushroom", "honey",
              "yeast", "gelatin", "egg", "meat & fish"]
DIET_NOTES = {
    "vegetarian": ["No meat, fish or egg", "Watch for gelatin, carmine (E120), animal rennet, E471 (source unclear)"],
    "eggetarian": ["No meat or fish (eggs OK)", "Watch for gelatin, carmine (E120)"],
    "vegan": ["No meat, fish, egg, dairy (milk, ghee, paneer, whey, casein) or honey"],
    "jain": ["Avoid: " + ", ".join(JAIN_AVOID)],
    "halal": ["No pork, lard or alcohol", "Check gelatin and E471 source"],
}


@router.get("/allergy-card", summary="Printable allergy & diet card per member, with Indian names")
def allergy_card():
    table = data.allergen_table()["by_key"]
    cards = []
    for m in current_household().members:
        allergies = []
        for raw in m.allergens:
            key = data.resolve_allergen(raw)
            entry = table.get(key) if key else None
            names = [k for k in (entry["keywords"] if entry else [raw]) if not k.startswith("ins:")]
            allergies.append({"name": entry["display"] if entry else raw.title(), "also_called": names[:14]})
        cards.append({
            "member": m.name, "relation": m.relation, "age": m.age, "allergies": allergies,
            "diets": [{"diet": d, "notes": DIET_NOTES.get(d, [])} for d in m.diet_rules],
            "conditions": [c.replace("_", " ") for c in m.conditions],
            "avoid": m.avoid_ingredients,
            "limits": m.limits.model_dump(),
        })
    return {"cards": cards}


# ---------------------------------------------------------------- shopping list
class ShoppingItem(BaseModel):
    product_name: str
    brand: Optional[str] = None
    code: Optional[str] = None
    score: Optional[int] = None
    note: Optional[str] = None


class ShoppingUpdate(BaseModel):
    done: bool


@router.get("/shopping", summary="Shopping list")
def shopping_get():
    return db.shopping_list()


@router.post("/shopping", summary="Add to shopping list")
def shopping_add(item: ShoppingItem):
    return {"id": db.shopping_add(item.product_name, item.brand, item.code, item.score, item.note)}


@router.patch("/shopping/{item_id}", summary="Tick / untick an item")
def shopping_patch(item_id: int, upd: ShoppingUpdate):
    db.shopping_update(item_id, upd.done)
    return {"ok": True}


@router.delete("/shopping/{item_id}", summary="Remove an item")
def shopping_del(item_id: int):
    db.shopping_delete(item_id)
    return {"ok": True}


# ----------------------------------------------------------------------- reset
@router.post("/admin/reset", summary="Demo helper: clear scans, logs, feedback and shopping list (keeps profile)")
def reset():
    db.reset_history()
    return {"reset": True}
