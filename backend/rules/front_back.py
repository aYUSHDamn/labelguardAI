"""
Front vs back of pack (pure Python, zero LLM).

The vision call notes what the FRONT shows (pictured foods, implied messages).
These rules check each promise against the BACK: the ingredient list, its order,
its percentages, the additives and the score.
"""
from __future__ import annotations

import re

from rules.text import contains_term, norm

# A front picture of X is backed up if any of these appear in the ingredients.
SYNONYMS = {
    "chocolate": ["chocolate", "cocoa"],
    "cocoa": ["cocoa", "chocolate"],
    "cream": ["cream", "milk", "malai"],
    "nuts": ["nut", "almond", "cashew", "pista", "pistachio", "walnut", "hazelnut", "peanut", "badam", "kaju"],
    "dry fruits": ["almond", "cashew", "raisin", "pista", "pistachio", "date", "fig", "apricot", "badam", "kaju"],
    "fruit": ["fruit", "mango", "apple", "orange", "strawberry", "pineapple", "banana", "guava", "berry"],
    "milk": ["milk", "milk solids", "milk powder", "dairy"],
    "grains": ["oat", "wheat", "millet", "ragi", "jowar", "bajra", "barley", "rice"],
    "multigrain": ["oat", "wheat", "millet", "ragi", "jowar", "bajra", "barley", "corn", "rice"],
    "honey": ["honey"],
    "ghee": ["ghee"],
    "jaggery": ["jaggery", "gur"],
}
SOUTHAMPTON = {"102", "104", "110", "122", "124", "129"}
FLAVOUR_WORDS = ["flavour", "flavor", "flavouring", "nature identical"]
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
STOP_WORDS = {"made", "with", "real", "pure", "natural", "nature", "goodness", "every", "loaded", "full",
              "fresh", "only", "best", "from", "taste", "tasty", "flavour", "flavor", "alphonso"}
GRAIN_WORDS = ["wheat", "whole wheat", "atta", "oat", "oats", "millet", "ragi", "grain", "multigrain", "jowar", "bajra"]
REFINED = ["maida", "refined wheat flour", "refined flour"]


def _short(ing: str) -> str:
    """'Masala tastemaker [Mixed spices (24%) ...]' -> 'Masala tastemaker'."""
    return re.split(r"[\[(]", ing)[0].strip() or ing[:40]


def _singular(w: str) -> str:
    w = w.strip().lower()
    if w.endswith("oes") and len(w) > 4:   # mangoes -> mango, tomatoes -> tomato
        return w[:-2]
    if w.endswith("ies") and len(w) > 4:   # berries -> berry
        return w[:-3] + "y"
    return w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 3 else w


def _find(ingredients: list[str], item: str):
    """Return (position, ingredient text, percent or None) for the first ingredient matching item."""
    terms = SYNONYMS.get(item.lower(), SYNONYMS.get(_singular(item), [_singular(item), item.lower()]))
    for pos, ing in enumerate(ingredients, start=1):
        t = norm(ing)
        if any(contains_term(t, x) for x in terms):
            m = _PCT.search(t)
            return pos, ing, float(m.group(1)) if m else None
    return None


def front_back_check(ex, pa: dict) -> list[dict]:
    """ex: Extraction; pa: product analysis (hidden_sugars, additives, score, ...)."""
    out = []
    ingredients = ex.ingredients
    if not (ex.front_highlights or ex.front_messages):
        return out

    # 1. Foods pictured / named on the front vs where they really are on the list.
    for item in ex.front_highlights:
        if not ingredients:
            out.append({"front": item, "kind": "picture", "verdict": "unknown",
                        "reason": "Ingredient list not readable, so this can't be checked.", "evidence": None})
            continue
        hit = _find(ingredients, item)
        if not hit:
            if any(g in item.lower() for g in GRAIN_WORDS):
                first = ingredients[0]
                refined = any(contains_term(norm(first), r) for r in REFINED)
                reason = (f"Front highlights {item}, but the main ingredient is '{_short(first)}'"
                          + (" (refined flour)." if refined else ".") + f" No {item} is listed.")
                ev = _short(first)
            else:
                fl = next((i for i in ingredients if any(contains_term(norm(i), w) for w in FLAVOUR_WORDS)), None)
                reason = (f"Shown on the front, but there is no {item} in the ingredients"
                          + (f"; the taste likely comes from '{_short(fl)}'" if fl else "") + ".")
                ev = _short(fl) if fl else None
            out.append({"front": item, "kind": "picture", "verdict": "misleading", "reason": reason, "evidence": ev})
            continue
        pos, ing, pct = hit
        named = bool(ex.product_name) and contains_term(norm(ex.product_name), _singular(item))
        if pct is not None and pct < 5:
            verdict, reason = "misleading", f"Pictured on the front, but only {pct:g}% of the product."
        elif named and pct is not None and pct < 15:
            verdict, reason = "misleading", (f"The product is named after {item}, but it is only {pct:g}% "
                                             f"(#{pos} on the list, after {', '.join(_short(i) for i in ingredients[:pos - 1][:2])}).")
        elif pct is not None and pct < 15:
            verdict, reason = "marketing", f"Featured on the front; it is {pct:g}% of the product (#{pos} on the list)."
        elif pos > 4 and pct is None:
            verdict, reason = "marketing", f"Featured on the front, but it's #{pos} on the ingredient list (smaller amount than {pos - 1} others)."
        else:
            verdict, reason = "ok", f"Real ingredient: #{pos} on the list" + (f", {pct:g}%." if pct is not None else ".")
        out.append({"front": item, "kind": "picture", "verdict": verdict, "reason": reason, "evidence": _short(ing)})

    # 2. Messages the front gives vs what the back shows.
    additive_codes = {a["code"] for a in pa["additives"]}
    colours = [a["name"] for a in pa["additives"] if a.get("class") == "colour"]
    flavours = [i for i in ingredients if any(contains_term(norm(i), w) for w in FLAVOUR_WORDS)]
    score = pa["score"]["score"]
    sugar = ex.nutrition_per_100g.sugar_g
    claim_verdicts = {c["claim"].lower(): c for c in pa.get("claims", [])}
    for msg in ex.front_messages:
        m = msg.lower()
        verdict, reason, ev = "ok", "Nothing on the back contradicts this.", None
        made_hit = None
        if ingredients and re.search(r"made with|real|pure|loaded with|full of", m):
            for word in re.findall(r"[a-z]+", m):
                if len(word) > 3 and word not in STOP_WORDS:
                    hit = _find(ingredients, word)
                    if hit and hit[2] is not None:
                        made_hit = hit
                        break
        is_natural = any(k in m for k in ("natural", "nature", "farm", "homemade", "home-style", "fresh"))
        if m in claim_verdicts and claim_verdicts[m]["verdict"] in ("misleading", "ok") and not is_natural:
            c = claim_verdicts[m]
            verdict, reason = c["verdict"], c["reason"]
        elif any(k in m for k in ("preservative",)):
            pres = [a["name"] for a in pa["additives"] if a.get("class") == "preservative"]
            if pres:
                verdict, reason, ev = "misleading", f"Front says '{msg}', but the back lists {', '.join(pres)}.", ", ".join(pres)
        elif made_hit and made_hit[2] is not None and made_hit[2] < 15:
            pos, ing, pct = made_hit
            verdict, reason, ev = "misleading", f"Front says '{msg}', but it is only {pct:g}% of the product.", _short(ing)
        elif any(k in m for k in ("kid", "child", "school", "growing")):
            issues = []
            if additive_codes & SOUTHAMPTON:
                issues.append("colours linked to hyperactivity in children")
            if sugar is not None and sugar > (11.25 if pa["liquid"] else 22.5):
                issues.append(f"high sugar ({sugar:g} g/100{'ml' if pa['liquid'] else 'g'})")
            if issues:
                verdict, reason = "misleading", "Aimed at children, but contains " + " and ".join(issues) + "."
        elif any(k in m for k in ("natural", "nature", "real", "pure", "farm", "homemade", "home-style", "fresh")):
            issues = colours + [_short(f) for f in flavours[:1]]
            if len(pa["additives"]) >= 3:
                issues.append(f"{len(pa['additives'])} additives")
            if issues:
                verdict, reason, ev = "misleading", f"Front suggests '{msg}', but the back lists {', '.join(issues[:3])}.", ", ".join(issues[:3])
        elif any(k in m for k in ("health", "fit", "energy", "power", "strong", "immunity", "nutri", "wholesome", "light")):
            if score < 50:
                verdict, reason = "misleading", f"Front suggests '{msg}', but the product scores {score}/100 ({pa['score']['label']})."
            else:
                verdict, reason = "marketing", f"Vague wording; the product scores {score}/100."
        else:
            verdict, reason = "marketing", "General marketing message; no specific rule for it."
        out.append({"front": msg, "kind": "message", "verdict": verdict, "reason": reason, "evidence": ev})
    return out
