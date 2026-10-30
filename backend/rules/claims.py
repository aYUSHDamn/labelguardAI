"""
Claim checker: compares front-of-pack claims with the actual numbers and ingredients.
Thresholds follow FSSAI (Advertising & Claims) Regulations 2018, per 100 g (solids)
or per 100 ml (liquids). Verdicts: ok | misleading | marketing | unknown.
"""
from __future__ import annotations

import re

from rules.text import contains_term

REFINED_FLOUR = ["maida", "refined wheat flour", "refined flour", "wheat flour", "all purpose flour"]
SYNTHETIC_COLOURS = {"102", "104", "110", "122", "124", "127", "129", "133", "143", "171", "150c", "150d"}
GLUTAMATE_SOURCES = ["yeast extract", "hydrolysed vegetable protein", "hydrolyzed vegetable protein",
                     "hydrolysed protein", "autolysed yeast", "soy sauce"]
HYDROGENATED = ["partially hydrogenated", "hydrogenated vegetable", "hydrogenated vegetable fat",
                "hydrogenated vegetable oil", "vanaspati", "hydrogenated fat"]


def check_claims(ex: dict, ctx: dict) -> list[dict]:
    """
    ex  : extraction dict (claims, nutrition_per_100g, ingredients, category)
    ctx : {'liquid', 'hidden_sugars', 'additives', 'allergens', 'diet_findings', 'score'}
    """
    n = ex.get("nutrition_per_100g") or {}
    liquid = ctx["liquid"]
    unit = "100ml" if liquid else "100g"
    ingredients = [i.lower() for i in ex.get("ingredients") or []]
    text = " , ".join(ingredients)
    sugar, added, sodium = n.get("sugar_g"), n.get("added_sugar_g"), n.get("sodium_mg")
    fat, sat, protein, fiber, kcal = (n.get("fat_g"), n.get("sat_fat_g"), n.get("protein_g"),
                                      n.get("fiber_g"), n.get("energy_kcal"))
    additive_codes = {a["code"] for a in ctx["additives"]}
    additive_classes = {a.get("class") for a in ctx["additives"]}
    allergen_keys = {a["key"] for a in ctx["allergens"] if a["source"] == "ingredients"}
    results = []

    for claim in ex.get("claims") or []:
        c = claim.lower().strip()
        verdict, reason = None, None

        if re.search(r"no (added )?sugar added|no added sugar|zero added sugar|without added sugar", c):
            added_aliases = [h["alias"] for h in ctx["hidden_sugars"]]
            if added_aliases:
                verdict, reason = "misleading", f"Ingredients include sugar sources: {', '.join(added_aliases[:4])}"
            elif added is not None and added > 0.5:
                verdict, reason = "misleading", f"Label lists {added} g added sugar per {unit}"
            else:
                verdict, reason = "ok", "No added sugar sources found in the ingredient list"
        elif re.search(r"sugar[- ]?free|zero sugar|0\s*g? sugar", c):
            if sugar is None:
                verdict, reason = "unknown", "Sugar value not readable"
            elif sugar > 0.5:
                verdict, reason = "misleading", f"'Sugar free' needs <= 0.5 g/{unit}; label shows {sugar} g"
            else:
                verdict, reason = "ok", f"{sugar} g sugar per {unit}"
        elif re.search(r"low sugar|less sugar|lite sugar|reduced sugar", c):
            limit = 2.5 if liquid else 5
            if sugar is None:
                verdict, reason = "unknown", "Sugar value not readable"
            elif sugar > limit:
                verdict = "misleading" if c.startswith("low") else "marketing"
                reason = f"'Low sugar' needs <= {limit} g/{unit}; label shows {sugar} g"
            else:
                verdict, reason = "ok", f"{sugar} g sugar per {unit}"
        elif re.search(r"low (salt|sodium)|less salt|reduced salt", c):
            if sodium is None:
                verdict, reason = "unknown", "Sodium value not readable"
            elif sodium > 120:
                verdict, reason = "misleading", f"'Low sodium' needs <= 120 mg/{unit}; label shows {sodium} mg"
            else:
                verdict, reason = "ok", f"{sodium} mg sodium per {unit}"
        elif re.search(r"low fat|lite|light|less fat", c) and "sugar" not in c:
            limit = 1.5 if liquid else 3
            if fat is None:
                verdict, reason = "unknown", "Fat value not readable"
            elif fat > limit:
                verdict = "misleading" if "low" in c else "marketing"
                reason = f"'Low fat' needs <= {limit} g/{unit}; label shows {fat} g"
            else:
                verdict, reason = "ok", f"{fat} g fat per {unit}"
        elif re.search(r"(high|rich|good source of|source of|packed with) protein|protein[- ]rich", c):
            strong = bool(re.search(r"high|rich|packed", c))
            if protein is None:
                verdict, reason = "unknown", "Protein value not readable"
            else:
                share = (protein * 4 / kcal) if kcal else None
                need = 0.20 if strong else 0.10
                ok = share >= need if share is not None else protein >= (10 if strong else 5)
                verdict = "ok" if ok else "misleading"
                pct = f"{round(share * 100)}% of calories" if share is not None else f"{protein} g/{unit}"
                reason = f"Protein is {pct}; '{claim}' needs >= {int(need * 100)}% of calories"
        elif re.search(r"(high|rich|good source of|source of) fib(re|er)|fib(re|er)[- ]rich", c):
            need = 6 if re.search(r"high|rich", c) else 3
            if fiber is None:
                verdict, reason = "unknown", "Fibre value not readable"
            else:
                verdict = "ok" if fiber >= need else "misleading"
                reason = f"{fiber} g fibre per {unit}; claim needs >= {need} g"
        elif re.search(r"multigrain|multi-grain|whole ?wheat|whole ?grain|atta|made with oats|millet", c):
            first = ingredients[0] if ingredients else ""
            if not ingredients:
                verdict, reason = "unknown", "Ingredient list not readable"
            elif any(contains_term(first, r) for r in REFINED_FLOUR) and not contains_term(first, "whole wheat"):
                verdict, reason = "misleading", f"First (largest) ingredient is '{ingredients[0]}', a refined flour"
            else:
                verdict, reason = "ok", f"First ingredient is '{ingredients[0]}'"
        elif re.search(r"no (added )?preservative|preservative[- ]free|without preservative", c):
            pres = [a["name"] for a in ctx["additives"] if a.get("class") == "preservative"]
            verdict = "misleading" if pres else "ok"
            reason = f"Contains preservative(s): {', '.join(pres)}" if pres else "No preservatives found in ingredients"
        elif re.search(r"no (artificial|synthetic) colou?r|no added colou?r", c):
            cols = [a["name"] for a in ctx["additives"] if a["code"] in SYNTHETIC_COLOURS]
            verdict = "misleading" if cols else "ok"
            reason = f"Contains synthetic colour(s): {', '.join(cols)}" if cols else "No synthetic colours found"
        elif re.search(r"no (added )?msg|msg[- ]free|no monosodium", c):
            if "621" in additive_codes:
                verdict, reason = "misleading", "Contains MSG (INS 621)"
            else:
                hidden = [g for g in GLUTAMATE_SOURCES if contains_term(text, g)]
                hidden += [a["name"] for a in ctx["additives"] if a["code"] in ("627", "631", "635")]
                if hidden:
                    verdict, reason = "marketing", f"No MSG, but contains other glutamate/enhancer sources: {', '.join(hidden)}"
                else:
                    verdict, reason = "ok", "No MSG or glutamate sources found"
        elif re.search(r"trans[- ]?fat[- ]?free|zero trans|0\s*g? trans|no trans", c):
            hyd = [h for h in HYDROGENATED if contains_term(text, h)]
            tf = n.get("trans_fat_g")
            if hyd:
                verdict, reason = "misleading", f"Contains {hyd[0]} (a trans-fat source)"
            elif tf is not None and tf > 0.2:
                verdict, reason = "misleading", f"Label shows {tf} g trans fat per {unit}"
            else:
                verdict, reason = "ok", "No hydrogenated fats found"
        elif re.search(r"cholesterol[- ]free|no cholesterol|zero cholesterol", c):
            animal = {"milk", "egg", "fish", "crustacean"} & allergen_keys
            verdict = "ok" if animal else "marketing"
            reason = ("Contains animal ingredients, claim is meaningful" if animal
                      else "Plant foods never contain cholesterol; the claim is true but meaningless")
        elif re.search(r"gluten[- ]free", c):
            verdict = "misleading" if "gluten" in allergen_keys else "ok"
            reason = "Ingredients contain gluten sources" if verdict == "misleading" else "No gluten sources found"
        elif re.search(r"\bvegan\b|plant[- ]based", c):
            bad = [f["ingredient"] for f in ctx["diet_findings"] if f["status"].get("vegan") == "avoid"
                   or f["status"].get("vegetarian") == "avoid" or f["category"] == "dairy"]
            verdict = "misleading" if bad else "ok"
            reason = f"Contains non-vegan ingredient(s): {', '.join(bad[:3])}" if bad else "No animal ingredients found"
        elif re.search(r"baked,? not fried|baked not fried", c):
            if fat is not None and fat > 17.5:
                verdict, reason = "marketing", f"Baked, but still {fat} g fat per {unit} (high)"
            else:
                verdict, reason = "ok", "Fat level is not high"
        elif re.search(r"healthy|health|nutritious|wholesome|guilt[- ]free|goodness|natural|immunity|energy|"
                       r"diet|fit|smart|power", c):
            score = ctx["score"]
            issues = []
            if sugar is not None and sugar > (11.25 if liquid else 22.5):
                issues.append(f"high sugar ({sugar} g)")
            if sodium is not None and sodium > 600:
                issues.append(f"high sodium ({sodium} mg)")
            if sat is not None and sat > (2.5 if liquid else 5):
                issues.append(f"high saturated fat ({sat} g)")
            if issues or score < 50:
                verdict = "misleading"
                reason = f"Vague health claim, but {', '.join(issues) or 'low health score'} (score {score}/100)"
            else:
                verdict, reason = "marketing", "Vague claim with no legal definition; numbers look reasonable"
        else:
            verdict, reason = "marketing", "No rule for this claim; treat as marketing text"

        results.append({"claim": claim, "verdict": verdict, "reason": reason})
    return results
