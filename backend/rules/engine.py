"""
The deterministic rules engine.

analyze_product(extraction)            -> profile-independent facts + health score
evaluate_member(member, analysis, ex)  -> SAFE / WARN / AVOID flags with reason + evidence
analyze(extraction, household)         -> both, for the whole household

No LLM calls, no randomness, no network: the same input always gives the same output.
"""
from __future__ import annotations

from config import LIQUID_CATEGORIES
from rules import data
from rules.claims import HYDROGENATED, check_claims
from rules.front_back import front_back_check
from rules.scoring import health_score
from rules.text import contains_term, extract_codes, find_terms, norm, strip_phrases
from schemas import Extraction, Household, Member

SAFE, WARN, AVOID = "SAFE", "WARN", "AVOID"
_RANK = {SAFE: 0, WARN: 1, AVOID: 2}

CHILD_RELATIONS = {"son", "daughter", "child", "kid", "grandson", "granddaughter", "grandchild", "baby", "toddler"}
SOUTHAMPTON_SIX = {"102", "104", "110", "122", "124", "129"}
PHOSPHATES = {"338", "339", "340", "341", "343", "450", "451", "452"}
HIGH_GI_SUGARS = {"maltodextrin", "glucose", "dextrose", "glucose syrup", "liquid glucose", "corn syrup",
                  "high fructose corn syrup", "malt syrup", "rice syrup", "brown rice syrup"}
SUGAR_ALIAS_EXCLUDE = ["caramel colour", "caramel color", "sugar free", "no added sugar", "sugar-free"]
AVOID_SYNONYMS = {
    "palm oil": ["palm oil", "palmolein", "palm fat", "palm kernel oil", "palm"],
    "maida": ["maida", "refined wheat flour", "refined flour"],
    "msg": ["msg", "monosodium glutamate", "ins:621"],
    "artificial colours": ["class:colour"],
    "artificial colors": ["class:colour"],
    "preservatives": ["class:preservative"],
    "artificial sweeteners": ["class:sweetener"],
    "sweeteners": ["class:sweetener"],
    "trans fat": HYDROGENATED,
    "hydrogenated oil": HYDROGENATED,
    "caffeine": ["caffeine", "coffee"],
}

# FSA-style traffic-light thresholds per 100 g (solids) / per 100 ml (liquids): (low_max, high_min)
TRAFFIC = {
    "sugar_g": {"solid": (5, 22.5), "liquid": (2.5, 11.25)},
    "sodium_mg": {"solid": (120, 600), "liquid": (120, 600)},
    "sat_fat_g": {"solid": (1.5, 5), "liquid": (0.75, 2.5)},
    "fat_g": {"solid": (3, 17.5), "liquid": (1.5, 8.75)},
}


# ----------------------------------------------------------------- product level
def find_hidden_sugars(ingredients: list[str]) -> list[dict]:
    aliases = data.sugar_aliases()
    out, seen = [], set()
    for pos, ing in enumerate(ingredients, start=1):
        t = strip_phrases(norm(ing), SUGAR_ALIAS_EXCLUDE)
        for alias in find_terms(t, list(aliases)):
            if alias in seen:
                continue
            seen.add(alias)
            row = aliases[alias]
            out.append({"alias": alias, "ingredient": ing, "position": pos, "group": row["group"],
                        "note": row["note"], "hidden": alias not in ("sugar", "sucrose", "cane sugar")})
    return out


def find_additives(ingredients: list[str]) -> list[dict]:
    table = data.additives()
    found: dict[str, dict] = {}
    for ing in ingredients:
        t = norm(ing)
        for code in extract_codes(t):
            a = table.get(code) or table.get(code.rstrip("abcdef"))
            if a is None:
                # Unknown code: report it, but it carries no score penalty.
                found.setdefault(code, {"code": code, "name": f"INS {code}", "class": "unknown",
                                        "purpose": "Not in our additive table", "concern": "unknown",
                                        "note": "", "evidence": ing})
                continue
            found.setdefault(a.ins, _additive_dict(a, ing))
        for a in table.values():
            if a.ins not in found and any(contains_term(t, al) for al in a.aliases):
                found[a.ins] = _additive_dict(a, ing)
    order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    return sorted(found.values(), key=lambda x: (order.get(x["concern"], 4), x["code"]))


def _additive_dict(a: data.Additive, evidence: str) -> dict:
    return {"code": a.ins, "name": a.name, "class": a.cls, "purpose": a.purpose,
            "concern": a.concern, "note": a.note, "evidence": evidence}


def _allergen_hits(entry: dict, texts: list[str], codes_per_text: list[list[str]]) -> list[dict]:
    hits = []
    words = [k for k in entry["keywords"] if not k.startswith("ins:")]
    code_kw = {k[4:] for k in entry["keywords"] if k.startswith("ins:")}
    for text, codes in zip(texts, codes_per_text):
        t = strip_phrases(norm(text), entry.get("exclude", []))
        matched = find_terms(t, words)
        if code_kw & set(codes):
            matched.append("INS " + ",".join(sorted(code_kw & set(codes))))
        if matched:
            hits.append({"ingredient": text, "matched": matched})
    return hits


def find_allergens(ingredients: list[str], may_contain: list[str]) -> list[dict]:
    table = data.allergen_table()["by_key"]
    ing_codes = [extract_codes(i) for i in ingredients]
    mc_codes = [extract_codes(i) for i in may_contain]
    out = []
    for key, entry in table.items():
        hits = _allergen_hits(entry, ingredients, ing_codes)
        if hits:
            out.append({"key": key, "display": entry["display"], "source": "ingredients", "evidence": hits})
            continue
        trace = _allergen_hits(entry, may_contain, mc_codes)
        if trace:
            out.append({"key": key, "display": entry["display"], "source": "may_contain", "evidence": trace})
    return out


def find_diet_findings(ingredients: list[str]) -> list[dict]:
    milk_exclude = data.allergen_table()["by_key"]["milk"].get("exclude", [])
    out = []
    for ing in ingredients:
        base = norm(ing)
        codes = set(extract_codes(base))
        for rule in data.diet_rules():
            t = strip_phrases(base, milk_exclude) if rule.category == "dairy" else base
            matched = [term for term in rule.terms
                       if (term.startswith("ins:") and term[4:] in codes)
                       or (not term.startswith("ins:") and contains_term(t, term))]
            if matched:
                out.append({"ingredient": ing, "matched": matched[0], "category": rule.category,
                            "status": dict(rule.status), "reason": rule.reason})
    return out


def _level(field: str, value, liquid: bool):
    if value is None or field not in TRAFFIC:
        return None
    lo, hi = TRAFFIC[field]["liquid" if liquid else "solid"]
    return "high" if value > hi else ("low" if value <= lo else "medium")


def serving_analysis(ex: Extraction, liquid: bool) -> dict:
    g = ex.serving_size_g
    p100, pserv = ex.nutrition_per_100g.model_dump(), ex.nutrition_per_serving.model_dump()
    rows, notes = [], []
    fields = [("energy_kcal", "Energy", "kcal"), ("sugar_g", "Sugar", "g"), ("added_sugar_g", "Added sugar", "g"),
              ("sodium_mg", "Sodium", "mg"), ("fat_g", "Total fat", "g"), ("sat_fat_g", "Saturated fat", "g"),
              ("protein_g", "Protein", "g"), ("fiber_g", "Fibre", "g")]
    for key, label, unit in fields:
        a, s = p100.get(key), pserv.get(key)
        computed = False
        if s is None and a is not None and g:
            s, computed = round(a * g / 100, 1), True
        if a is None and s is None:
            continue
        level = _level(key, a, liquid)
        hidden = bool(level == "high" and g and g <= 30)
        rows.append({"nutrient": key, "label": label, "unit": unit, "per_100g": a, "per_serving": s,
                     "per_serving_computed": computed, "level_per_100g": level, "hidden_by_small_serving": hidden})
        if hidden:
            notes.append(f"{label}: one {g:g}{'ml' if liquid else 'g'} serving shows only {s} {unit}, "
                         f"but per 100{'ml' if liquid else 'g'} it is {a} {unit} (HIGH). Small servings make it look better.")
        if a is not None and pserv.get(key) is not None and g:
            expected = a * g / 100
            if expected > 0 and abs(pserv[key] - expected) / expected > 0.25:
                notes.append(f"{label}: per-serving value ({pserv[key]}) does not match per-100g x serving "
                             f"size ({expected:.1f}). Double-check the label.")
    return {"serving_size": ex.serving_size, "serving_size_g": g, "rows": rows, "notes": notes,
            "basis": "per 100ml" if liquid else "per 100g"}


def analyze_product(ex: Extraction) -> dict:
    liquid = ex.category in LIQUID_CATEGORIES
    hidden_sugars = find_hidden_sugars(ex.ingredients)
    additives = find_additives(ex.ingredients)
    allergens = find_allergens(ex.ingredients, ex.may_contain)
    diet_findings = find_diet_findings(ex.ingredients)
    score = health_score(ex.nutrition_per_100g.model_dump(), ex.category, additives, ex.ingredients)
    claims = check_claims(ex.model_dump(), {"liquid": liquid, "hidden_sugars": hidden_sugars, "additives": additives,
                                            "allergens": allergens, "diet_findings": diet_findings,
                                            "score": score["score"]})
    warnings = []
    if ex.confidence < 0.6:
        warnings.append(f"Low extraction confidence ({ex.confidence:.0%}). Retake the photo in good light if results look wrong.")
    if ex.per_100g_computed:
        warnings.append(f"This label only gives per-serving values; per-100 g values were calculated from the "
                        f"{ex.serving_size_g:g} g serving size so products can be compared fairly.")
    if not ex.ingredients:
        warnings.append("No ingredient list in this photo, so allergen, diet and hidden-sugar checks could not run. "
                        "Paste or photograph the ingredients panel too for a full check.")
    if ex.unreadable_fields:
        warnings.append("Unreadable on the label: " + ", ".join(ex.unreadable_fields))
    if not score["data_complete"]:
        warnings.append("Sugar and sodium values are missing, so the score is based on partial data.")
    result = {
        "liquid": liquid,
        "hidden_sugars": hidden_sugars,
        "sugar_source_count": len(hidden_sugars),
        "additives": additives,
        "allergens": allergens,
        "diet_findings": diet_findings,
        "score": score,
        "claims": claims,
        "serving": serving_analysis(ex, liquid),
        "data_warnings": warnings,
    }
    result["front_back"] = front_back_check(ex, result)
    return result


# ------------------------------------------------------------------ member level
def _effective_diet_status(diet: str, f: dict):
    s = f["status"]
    worst = lambda *xs: "avoid" if "avoid" in xs else ("check" if "check" in xs else None)  # noqa: E731
    if diet == "vegetarian":
        return s.get("vegetarian")
    if diet == "eggetarian":
        return None if f["category"] == "egg" else s.get("vegetarian")
    if diet == "vegan":
        return worst(s.get("vegan"), s.get("vegetarian"))
    if diet == "jain":
        return worst(s.get("jain"), s.get("vegetarian"))
    if diet == "halal":
        return s.get("halal")
    return None


def _is_child(m: Member) -> bool:
    return (m.relation or "").lower() in CHILD_RELATIONS or (m.age is not None and m.age < 12)


def evaluate_member(m: Member, pa: dict, ex: Extraction) -> dict:
    flags: list[dict] = []

    def flag(status, category, reason, evidence):
        flags.append({"status": status, "category": category, "reason": reason, "evidence": evidence})

    n = ex.nutrition_per_100g
    liquid = pa["liquid"]
    unit = "100ml" if liquid else "100g"
    text = " , ".join(norm(i) for i in ex.ingredients)
    present = {a["key"]: a for a in pa["allergens"]}
    table = data.allergen_table()["by_key"]
    additive_codes = {a["code"] for a in pa["additives"]}

    # 1. Allergies -------------------------------------------------------------
    extra_avoid = []
    for raw in m.allergens:
        key = data.resolve_allergen(raw)
        if key is None:
            extra_avoid.append(raw)  # unknown allergen word: fall back to plain text match
            continue
        a = present.get(key)
        ev = lambda a: "; ".join(h["ingredient"] for h in a["evidence"])[:200]  # noqa: E731
        if a and a["source"] == "ingredients":
            flag(AVOID, "allergen", f"Contains {a['display']} (listed allergy)", ev(a))
        elif a:
            flag(WARN, "allergen", f"May contain traces of {a['display']}", ev(a))
        else:
            parent = table[key].get("parent")
            if parent and parent in present:
                p = present[parent]
                verb = "Contains" if p["source"] == "ingredients" else "May contain"
                flag(WARN, "allergen",
                     f"{verb} {p['display'].lower()} that may include {table[key]['display'].lower()} - check the pack",
                     ev(p))

    # 2. Diet rules (Jain / vegetarian / vegan / halal) ---------------------------
    for diet in m.diet_rules:
        for f in pa["diet_findings"]:
            st = _effective_diet_status(diet, f)
            if st == "avoid":
                flag(AVOID, "diet", f"Not {diet}: {f['reason']}", f["ingredient"])
            elif st == "check":
                flag(WARN, "diet", f"{diet.title()} status unclear: {f['reason']} (source unclear, check with the brand)",
                     f["ingredient"])

    # 3. Medical conditions -------------------------------------------------------
    conds = set(m.conditions)
    sugar_lo, sugar_hi = TRAFFIC["sugar_g"]["liquid" if liquid else "solid"]
    if conds & {"diabetes", "prediabetes", "pcos"}:
        if n.sugar_g is None:
            if pa["hidden_sugars"]:
                flag(WARN, "condition", "Sugar value unreadable but sugar is in the ingredients",
                     ", ".join(h["alias"] for h in pa["hidden_sugars"][:4]))
        elif n.sugar_g > sugar_hi:
            flag(AVOID, "condition", f"High sugar ({n.sugar_g} g/{unit}) for blood-sugar control", f"sugar {n.sugar_g} g")
        elif n.sugar_g > sugar_lo:
            flag(WARN, "condition", f"Moderate sugar ({n.sugar_g} g/{unit})", f"sugar {n.sugar_g} g")
        hi_gi = [h["alias"] for h in pa["hidden_sugars"] if h["alias"] in HIGH_GI_SUGARS]
        if hi_gi:
            flag(WARN, "condition", "Contains fast-acting (high-GI) sugars", ", ".join(hi_gi))
        if pa["sugar_source_count"] >= 3:
            flag(WARN, "condition", f"Sugar appears under {pa['sugar_source_count']} different names",
                 ", ".join(h["alias"] for h in pa["hidden_sugars"]))
    if conds & {"hypertension", "heart_disease", "kidney_disease"} and n.sodium_mg is not None:
        if n.sodium_mg > 600:
            flag(AVOID, "condition", f"High sodium ({n.sodium_mg:g} mg/{unit}) for blood pressure", f"sodium {n.sodium_mg:g} mg")
        elif n.sodium_mg > 300:
            flag(WARN, "condition", f"Moderate sodium ({n.sodium_mg:g} mg/{unit})", f"sodium {n.sodium_mg:g} mg")
    if conds & {"high_cholesterol", "heart_disease"}:
        sat_hi = 2.5 if liquid else 5
        if n.sat_fat_g is not None and n.sat_fat_g > sat_hi:
            flag(AVOID, "condition", f"High saturated fat ({n.sat_fat_g} g/{unit})", f"sat fat {n.sat_fat_g} g")
        elif n.sat_fat_g is not None and n.sat_fat_g > sat_hi * 0.3:
            flag(WARN, "condition", f"Moderate saturated fat ({n.sat_fat_g} g/{unit})", f"sat fat {n.sat_fat_g} g")
        hyd = [h for h in HYDROGENATED if contains_term(text, h)]
        if hyd or (n.trans_fat_g or 0) > 0.2:
            flag(AVOID, "condition", "Contains trans-fat sources", hyd[0] if hyd else f"trans fat {n.trans_fat_g} g")
    if "lactose_intolerance" in conds:
        t = strip_phrases(text, table["milk"].get("exclude", []))
        lac = find_terms(t, data.allergen_table()["lactose_keywords"])
        if lac:
            flag(WARN, "condition", "Contains dairy with lactose (lactose intolerance)", ", ".join(lac))
    if "celiac" in conds and "gluten" in present:
        g = present["gluten"]
        flag(AVOID if g["source"] == "ingredients" else WARN, "condition",
             "Contains gluten (celiac)" if g["source"] == "ingredients" else "May contain gluten (celiac)",
             "; ".join(h["ingredient"] for h in g["evidence"])[:200])
    if "kidney_disease" in conds and additive_codes & PHOSPHATES:
        flag(WARN, "condition", "Contains phosphate additives (kidney disease)",
             ", ".join(f"INS {c}" for c in sorted(additive_codes & PHOSPHATES)))
    if "pregnancy" in conds:
        if contains_term(text, "caffeine") or contains_term(text, "coffee"):
            flag(WARN, "condition", "Contains caffeine (limit in pregnancy)", "caffeine")
        if "954" in additive_codes:
            flag(WARN, "condition", "Contains saccharin (often advised against in pregnancy)", "INS 954")
    if "obesity" in conds and n.energy_kcal is not None and n.energy_kcal > 400:
        flag(WARN, "condition", f"Energy-dense ({n.energy_kcal:g} kcal/{unit})", f"{n.energy_kcal:g} kcal")

    # 4. Ingredients the person wants to avoid ------------------------------------
    additive_classes = {a["class"]: a for a in pa["additives"]}
    for raw in list(m.avoid_ingredients) + extra_avoid:
        term = raw.lower().strip()
        if term in ("sugar", "added sugar", "sugars"):
            if pa["hidden_sugars"]:
                flag(AVOID, "avoid_list", "Contains sugar (on your avoid list)",
                     ", ".join(h["alias"] for h in pa["hidden_sugars"][:5]))
            continue
        hit = None
        for syn in AVOID_SYNONYMS.get(term, [term]):
            if syn.startswith("class:"):
                if syn[6:] in additive_classes:
                    hit = additive_classes[syn[6:]]["name"]
            elif syn.startswith("ins:"):
                if syn[4:] in additive_codes:
                    hit = f"INS {syn[4:]}"
            elif contains_term(text, syn):
                hit = next((i for i in ex.ingredients if contains_term(norm(i), syn)), syn)
            if hit:
                break
        if hit:
            flag(AVOID, "avoid_list", f"Contains {raw} (on your avoid list)", hit)

    # 5. Personal daily limits per serving -----------------------------------------
    g = ex.serving_size_g
    if g:
        sugar_s = (ex.nutrition_per_serving.sugar_g if ex.nutrition_per_serving.sugar_g is not None
                   else (n.sugar_g * g / 100 if n.sugar_g is not None else None))
        sodium_s = (ex.nutrition_per_serving.sodium_mg if ex.nutrition_per_serving.sodium_mg is not None
                    else (n.sodium_mg * g / 100 if n.sodium_mg is not None else None))
        if sugar_s is not None and m.limits.sugar_g_per_day:
            pct = sugar_s / m.limits.sugar_g_per_day * 100
            if pct >= 40:
                flag(WARN, "limit", f"One serving uses {pct:.0f}% of {m.name}'s daily sugar limit "
                                    f"({m.limits.sugar_g_per_day:g} g)", f"{sugar_s:.1f} g sugar per serving")
        if sodium_s is not None and m.limits.sodium_mg_per_day:
            pct = sodium_s / m.limits.sodium_mg_per_day * 100
            if pct >= 30:
                flag(WARN, "limit", f"One serving uses {pct:.0f}% of {m.name}'s daily sodium limit "
                                    f"({m.limits.sodium_mg_per_day:g} mg)", f"{sodium_s:.0f} mg sodium per serving")

    # 6. Children -----------------------------------------------------------------
    if _is_child(m):
        cols = sorted(additive_codes & SOUTHAMPTON_SIX)
        if cols:
            flag(WARN, "child", "Contains colours linked to hyperactivity in some children",
                 ", ".join(f"INS {c}" for c in cols))
        if contains_term(text, "caffeine"):
            flag(WARN, "child", "Contains caffeine (not advised for children)", "caffeine")
        sweet = [a["name"] for a in pa["additives"] if a["class"] == "sweetener" and a["code"] != "960"]
        if sweet:
            flag(WARN, "child", "Contains artificial sweeteners", ", ".join(sweet))

    # 7. High-concern additives (everyone) -------------------------------------------
    for a in pa["additives"]:
        if a["concern"] == "high":
            flag(WARN, "additive", f"{a['name']} (INS {a['code']}): {a['note']}", a["evidence"])

    # de-duplicate, worst first
    uniq, seen = [], set()
    for f in flags:
        k = (f["status"], f["category"], f["reason"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    uniq.sort(key=lambda f: -_RANK[f["status"]])
    status = uniq[0]["status"] if uniq else SAFE
    if status == AVOID:
        summary = f"Not suitable for {m.name}: {uniq[0]['reason']}"
    elif status == WARN:
        summary = f"OK with caution for {m.name}: {uniq[0]['reason']}"
    else:
        summary = f"No conflicts found with {m.name}'s profile"
    return {"member": m.name, "relation": m.relation, "status": status, "summary": summary, "flags": uniq}


def household_verdict(score: dict, members: list[dict]) -> str:
    avoid = [m["member"] for m in members if m["status"] == AVOID]
    warn = [m["member"] for m in members if m["status"] == WARN]
    line = f"{score['label']} ({score['score']}/100)."
    if avoid:
        line += f" Not suitable for {', '.join(avoid)}."
    if warn:
        line += f" Caution for {', '.join(warn)}."
    if not avoid and not warn:
        line += " No conflicts with your household's profiles."
    return line


def analyze(ex: Extraction, household: Household) -> dict:
    pa = analyze_product(ex)
    members = [evaluate_member(m, pa, ex) for m in household.members]
    pa["members"] = members
    pa["verdict"] = household_verdict(pa["score"], members)
    pa["overall_status"] = max((m["status"] for m in members), key=lambda s: _RANK[s], default=SAFE)
    return pa
