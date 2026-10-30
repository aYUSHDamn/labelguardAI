"""
Transparent, deterministic health score (0-100). Same input -> same score, always.

    score = 100
            - sugar_penalty      (max 35)  solids: 0.875 pts per g/100g  (40 g -> 35)
                                           drinks: 3.5 pts per g/100ml   (10 g -> 35)
            - sodium_penalty     (max 25)  0.025 pts per mg/100g          (1000 mg -> 25)
            - sat_fat_penalty    (max 20)  solids: 2 pts per g (10 g -> 20); drinks: 4 pts per g
            - energy_penalty     (max 10)  solids: (kcal - 250) / 30;  drinks: (kcal - 40) / 8
            - additive_penalty   (max 15)  high concern 5, medium 2, low 0.5 each
            - processing_penalty (0/5/10)  minimally processed 0, processed 5, ultra-processed 10
            + fiber_bonus        (max 8)   1.6 pts per g/100g
            + protein_bonus      (max 7)   0.7 pts per g/100g
    clamp to 0..100 and round half up.

Grades: >= 70 green "Good choice", 50-69 amber "Okay occasionally", < 50 red "Limit this".
Missing nutrients contribute 0 and are reported in `missing` so the user knows.
"""
from __future__ import annotations

import math

from config import LIQUID_CATEGORIES
from rules.text import contains_term

FORMULA = {
    "base": 100,
    "components": [
        {"key": "sugar", "label": "Sugar", "max": 35, "rule": "solids 0.875 pts per g/100g; drinks 3.5 pts per g/100ml"},
        {"key": "sodium", "label": "Sodium", "max": 25, "rule": "0.025 pts per mg/100g (1000 mg = 25)"},
        {"key": "sat_fat", "label": "Saturated fat", "max": 20, "rule": "solids 2 pts per g; drinks 4 pts per g"},
        {"key": "energy", "label": "Energy density", "max": 10, "rule": "solids (kcal-250)/30; drinks (kcal-40)/8"},
        {"key": "additives", "label": "Additives", "max": 15, "rule": "high concern 5, medium 2, low 0.5 each"},
        {"key": "processing", "label": "Processing level", "max": 10, "rule": "minimal 0, processed 5, ultra-processed 10"},
        {"key": "fiber", "label": "Fibre bonus", "max": 8, "rule": "+1.6 pts per g/100g"},
        {"key": "protein", "label": "Protein bonus", "max": 7, "rule": "+0.7 pts per g/100g"},
    ],
    "grades": [
        {"min": 70, "label": "Good choice", "color": "green"},
        {"min": 50, "label": "Okay occasionally", "color": "amber"},
        {"min": 0, "label": "Limit this", "color": "red"},
    ],
    "text": __doc__.strip(),
}

# Additive classes / words that mark ultra-processing (NOVA group 4 style heuristic).
UPF_CLASSES = {"colour", "flavour_enhancer", "sweetener", "emulsifier", "thickener", "humectant"}
UPF_WORDS = ["artificial flavour", "artificial flavouring", "added flavour", "flavouring substances",
             "nature identical", "emulsifier", "flavour enhancer", "sweetener", "stabilizer", "stabiliser",
             "thickener", "humectant", "colour", "hydrogenated", "maltodextrin", "invert sugar",
             "glucose syrup", "liquid glucose", "protein isolate", "modified starch", "interesterified"]


def _r1(x: float) -> float:
    return math.floor(x * 10 + 0.5) / 10


def processing_level(ingredients: list[str], additives: list[dict]) -> int:
    """1 = minimally processed, 3 = processed (also used when unknown), 4 = ultra-processed."""
    if not ingredients:
        return 3  # no ingredient list: can't claim "minimally processed", take the middle penalty
    text = " , ".join(ingredients).lower()
    if any(a.get("class") in UPF_CLASSES for a in additives) or any(contains_term(text, w) for w in UPF_WORDS):
        return 4
    if len(ingredients) <= 2 and not additives:
        return 1
    return 3


def grade_for(score: int) -> dict:
    for g in FORMULA["grades"]:
        if score >= g["min"]:
            return {"label": g["label"], "color": g["color"]}
    return {"label": "Limit this", "color": "red"}


def health_score(nutrition: dict, category: str, additives: list[dict], ingredients: list[str]) -> dict:
    liquid = category in LIQUID_CATEGORIES
    n = nutrition or {}
    missing = [k for k in ("sugar_g", "sodium_mg", "sat_fat_g", "energy_kcal") if n.get(k) is None]
    comps = []

    def add(key, label, value, points, detail):
        comps.append({"key": key, "label": label, "value": value, "points": _r1(points), "detail": detail})

    sugar = n.get("sugar_g")
    if sugar is not None:
        add("sugar", "Sugar", sugar, -min(35.0, sugar * (3.5 if liquid else 0.875)),
            f"{sugar} g per 100{'ml' if liquid else 'g'}")
    sodium = n.get("sodium_mg")
    if sodium is not None:
        add("sodium", "Sodium", sodium, -min(25.0, sodium * 0.025), f"{sodium} mg per 100g")
    sat = n.get("sat_fat_g")
    if sat is not None:
        add("sat_fat", "Saturated fat", sat, -min(20.0, sat * (4 if liquid else 2)), f"{sat} g per 100g")
    kcal = n.get("energy_kcal")
    if kcal is not None:
        e = (kcal - 40) / 8 if liquid else (kcal - 250) / 30
        add("energy", "Energy density", kcal, -min(10.0, max(0.0, e)), f"{kcal} kcal per 100g")

    weights = {"high": 5.0, "medium": 2.0, "low": 0.5}
    add_pen = min(15.0, sum(weights.get(a.get("concern"), 0.0) for a in additives))
    add("additives", "Additives", len(additives), -add_pen,
        f"{sum(1 for a in additives if a.get('concern') == 'high')} high, "
        f"{sum(1 for a in additives if a.get('concern') == 'medium')} medium concern")

    level = processing_level(ingredients, additives)
    add("processing", "Processing level", level, -{1: 0.0, 3: 5.0, 4: 10.0}[level],
        "unknown (no ingredient list), counted as processed" if not ingredients else
        {1: "minimally processed", 3: "processed", 4: "ultra-processed markers found"}[level])

    fiber = n.get("fiber_g")
    if fiber is not None:
        add("fiber", "Fibre bonus", fiber, min(8.0, fiber * 1.6), f"{fiber} g per 100g")
    protein = n.get("protein_g")
    if protein is not None:
        add("protein", "Protein bonus", protein, min(7.0, protein * 0.7), f"{protein} g per 100g")

    raw = round(100 + sum(c["points"] for c in comps), 1)  # avoid float drift before rounding
    score = int(max(0, min(100, math.floor(raw + 0.5))))
    return {
        "score": score,
        **grade_for(score),
        "components": comps,
        "processing_level": level,
        "missing": missing,
        "data_complete": not ("sugar_g" in missing and "sodium_mg" in missing),
        "basis": "per 100ml" if liquid else "per 100g",
    }
