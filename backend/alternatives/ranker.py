"""
Alternatives engine (zero LLM).

1. Candidates = Open Food Facts search for the same category  +  local Indian fallback CSV.
2. Each candidate is scored with the SAME rules engine and formula as the scanned product.
3. Drop candidates that are AVOID for any target member or do not beat the scanned score.
4. Re-rank with stored thumbs up/down feedback, return top 3 with a one-line reason.
"""
from __future__ import annotations

import re
from typing import Optional

import db
from alternatives import off_client
from rules import data
from rules.engine import AVOID, WARN, analyze_product, evaluate_member
from schemas import Extraction, Household
from rules.text import split_ingredients


def _key(name: str, brand: str) -> str:
    return re.sub(r"[^a-z0-9]", "", f"{brand or ''}{name or ''}".lower())


def fallback_candidates(category: str) -> list[dict]:
    out = []
    for row in data.fallback_products():
        if row["category"] != category:
            continue
        num = lambda k: float(row[k]) if row.get(k) not in (None, "") else None  # noqa: E731
        ex = Extraction(
            product_name=row["product_name"], brand=row["brand"], category=row["category"],
            ingredients=split_ingredients(row["ingredients"]),
            nutrition_per_100g={"energy_kcal": num("energy_kcal"), "sugar_g": num("sugar_g"),
                                "sodium_mg": num("sodium_mg"), "fat_g": num("fat_g"), "sat_fat_g": num("sat_fat_g"),
                                "protein_g": num("protein_g"), "fiber_g": num("fiber_g")},
            may_contain=[x for x in row["may_contain"].split(";") if x], confidence=1.0,
        )
        out.append({"code": row["code"], "extraction": ex, "source": "fallback_db", "approximate": True,
                    "image_url": None, "price_inr": num("price_inr")})
    return out


def off_candidates(category: str) -> list[dict]:
    out = []
    for p in off_client.search_category(category):
        ex = off_client.product_to_extraction(p, category)
        if ex and ex.product_name:
            out.append({"code": p.get("code") or _key(ex.product_name, ex.brand), "extraction": ex,
                        "source": "open_food_facts", "approximate": False,
                        "image_url": p.get("image_front_small_url"), "price_inr": None})
    return out


def _pct_less(base, cand) -> Optional[int]:
    if base is None or cand is None or base <= 0:
        return None
    return round((base - cand) / base * 100)


def reason_line(base: Extraction, base_pa: dict, cand: Extraction, cand_pa: dict) -> str:
    b, c = base.nutrition_per_100g, cand.nutrition_per_100g
    parts = []
    for label, bv, cv in (("sugar", b.sugar_g, c.sugar_g), ("sodium", b.sodium_mg, c.sodium_mg),
                          ("saturated fat", b.sat_fat_g, c.sat_fat_g)):
        pct = _pct_less(bv, cv)
        if pct is not None and pct >= 20:
            parts.append(f"{pct}% less {label}")
    flagged = lambda pa: [a for a in pa["additives"] if a["concern"] in ("medium", "high")]  # noqa: E731
    if flagged(base_pa) and not flagged(cand_pa):
        parts.append("no flagged additives")
    if c.fiber_g is not None and (b.fiber_g or 0) + 2 <= c.fiber_g:
        parts.append(f"{c.fiber_g:g} g fibre")
    if cand_pa["sugar_source_count"] < base_pa["sugar_source_count"] and base_pa["sugar_source_count"] >= 2:
        parts.append(f"{cand_pa['sugar_source_count']} sugar source(s) vs {base_pa['sugar_source_count']}")
    if not parts:
        parts.append(f"higher score ({cand_pa['score']['score']} vs {base_pa['score']['score']})")
    return ", ".join(parts[:3])


def feedback_adjustment(code: str, brand: str, ex: Extraction, price, feedback: list[dict]) -> tuple[float, list[str]]:
    """Deterministic re-ranking from stored feedback. Returns (points, explanations)."""
    adj, why = 0.0, []
    sugar = ex.nutrition_per_100g.sugar_g or 0
    too_sweet = sum(1 for f in feedback if f["vote"] < 0 and f["reason"] == "too_sweet")
    expensive_prices = []
    for f in feedback:
        same_product = f["product_code"] == code
        same_brand = brand and f["brand"] and f["brand"].lower() == brand.lower()
        if same_product:
            adj += 8 * f["vote"]
            if f["vote"] < 0 and f["reason"] == "not_available":
                adj -= 12
        if same_brand and f["vote"] < 0 and f["reason"] == "dont_like_brand":
            adj -= 10
        elif same_brand and f["vote"] > 0 and not same_product:
            adj += 2
        if f["vote"] < 0 and f["reason"] == "too_expensive":
            expensive_prices.append(f.get("_price"))
    if too_sweet and sugar > 5:
        adj -= min(15.0, too_sweet * sugar * 0.3)
        why.append("you said alternatives were too sweet")
    if price and any(p and price >= p for p in expensive_prices):
        adj -= 5
        why.append("similar price to one you found too expensive")
    adj = max(-30.0, min(20.0, adj))
    if adj > 0:
        why.append("you liked this before")
    elif adj < 0 and not why:
        why.append("based on your earlier feedback")
    return round(adj, 1), why


def swap_impact(base: Extraction, cand: Extraction, weekly_grams: Optional[float]) -> Optional[str]:
    """'Swapping saves ~X g sugar a week' - from what was logged, else one serving a day."""
    grams, basis = weekly_grams, "based on what your family logged this week"
    if not grams:
        serving = base.serving_size_g or 30
        grams, basis = serving * 7, f"if you have one {serving:g} g serving a day"
    b, c = base.nutrition_per_100g, cand.nutrition_per_100g
    parts = []
    if b.sugar_g is not None and c.sugar_g is not None and b.sugar_g > c.sugar_g:
        saved = (b.sugar_g - c.sugar_g) * grams / 100
        if saved >= 1:
            parts.append(f"{saved:.0f} g sugar (~{saved / 4:.0f} tsp)")
    if b.sodium_mg is not None and c.sodium_mg is not None and b.sodium_mg > c.sodium_mg:
        saved = (b.sodium_mg - c.sodium_mg) * grams / 100
        if saved >= 50:
            parts.append(f"{saved:.0f} mg sodium")
    return f"Swapping saves {' and '.join(parts)} a week, {basis}." if parts else None


def find_alternatives(base: Extraction, household: Household, member: Optional[str] = None,
                      limit: int = 3, weekly_grams: Optional[float] = None) -> dict:
    base_pa = analyze_product(base)
    base_score = base_pa["score"]["score"]
    targets = [m for m in household.members if member in (None, "", "all") or m.name == member] or household.members

    candidates = off_candidates(base.category) + fallback_candidates(base.category)
    feedback = db.all_feedback()
    prices = {c["code"]: c["price_inr"] for c in candidates}
    for f in feedback:
        f["_price"] = prices.get(f["product_code"])

    seen = {_key(base.product_name, base.brand)}
    results, considered, excluded = [], 0, {"not_better": 0, "unsafe": 0}
    for cand in candidates:
        ex: Extraction = cand["extraction"]
        k = _key(ex.product_name, ex.brand)
        if k in seen:
            continue
        seen.add(k)
        considered += 1
        pa = analyze_product(ex)
        score = pa["score"]["score"]
        if score <= base_score:
            excluded["not_better"] += 1
            continue
        verdicts = [evaluate_member(m, pa, ex) for m in targets]
        if any(v["status"] == AVOID for v in verdicts):
            excluded["unsafe"] += 1
            continue
        warns = [f"{v['member']}: {v['flags'][0]['reason']}" for v in verdicts if v["status"] == WARN]
        adj, adj_why = feedback_adjustment(cand["code"], ex.brand, ex, cand["price_inr"], feedback)
        rank_value = score + adj - 3 * len(warns)
        results.append({
            "code": cand["code"], "product_name": ex.product_name, "brand": ex.brand,
            "score": score, "color": pa["score"]["color"], "label": pa["score"]["label"],
            "reason": reason_line(base, base_pa, ex, pa), "warnings": warns,
            "swap_impact": swap_impact(base, ex, weekly_grams), "category": ex.category,
            "source": cand["source"], "approximate": cand["approximate"], "image_url": cand["image_url"],
            "price_inr": cand["price_inr"], "rank_value": round(rank_value, 1),
            "feedback_adjustment": adj, "feedback_note": "; ".join(adj_why) or None,
            "nutrition_per_100g": ex.nutrition_per_100g.model_dump(),
        })
    results.sort(key=lambda r: (-r["rank_value"], -r["score"], r["product_name"] or ""))
    return {
        "base": {"product_name": base.product_name, "score": base_score, "category": base.category},
        "for_members": [m.name for m in targets],
        "alternatives": results[:limit],
        "considered": considered, "excluded": excluded,
        "sources_used": sorted({c["source"] for c in candidates}),
        "note": ("Fallback products use approximate nutrition values compiled for this demo; "
                 "check the pack before buying."),
    }
