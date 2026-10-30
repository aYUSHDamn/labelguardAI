"""
Deterministic keyword profile parser.

Used as the FALLBACK when Gemini is unavailable, and as a baseline in the
profile-parser evaluation. Handles the common patterns well; the LLM handles
messier free text better.
"""
from __future__ import annotations

import re

from rules.data import allergen_table, resolve_allergen
from rules.text import contains_term
from schemas import CONDITION_SYNONYMS, DIET_SYNONYMS, Household

RELATIONS = {
    "son": "son", "daughter": "daughter", "wife": "spouse", "husband": "spouse", "spouse": "spouse",
    "mother": "mother", "mom": "mother", "mum": "mother", "amma": "mother", "father": "father",
    "dad": "father", "papa": "father", "grandmother": "grandmother", "grandma": "grandmother",
    "dadi": "grandmother", "nani": "grandmother", "grandfather": "grandfather", "grandpa": "grandfather",
    "dada": "grandfather", "nana": "grandfather", "brother": "sibling", "sister": "sibling",
    "kid": "child", "child": "child", "baby": "child",
}
FAMILY_WORDS = ["we", "we're", "we are", "our family", "whole family", "all of us", "everyone", "family"]
AMBIGUOUS_CONDITION_KEYS = {"sugar", "bp", "cholesterol", "weight loss"}


def _clauses(text: str) -> list[str]:
    parts = re.split(r"[.;\n]|,(?![^()]*\))|\bbut\b|\balso\b", text.lower())
    return [p.strip() for p in parts if p and p.strip()]


def _relation_in(clause: str):
    for word, rel in RELATIONS.items():
        if re.search(rf"\b{word}\b", clause):
            return word, rel
    return None, None


def parse_profile_keywords(text: str) -> Household:
    members: dict[str, dict] = {"Me": _blank("Me", "self")}
    family_wide: list[str] = []
    current = "Me"
    # "my son Rohan" -> use the real name when one follows the relation word
    names = {m.group(1).lower(): m.group(2) for m in re.finditer(r"\b[Mm]y\s+([a-z]+)\s+([A-Z][a-z]+)\b", text)
             if m.group(1).lower() in RELATIONS and m.group(2).lower() not in ("is", "has", "and")}
    for clause in _clauses(text):
        word, rel = _relation_in(clause)
        if word:
            current = names.get(word, word.title())
            members.setdefault(current, _blank(current, rel))
        elif any(re.search(rf"\b{re.escape(w)}\b", clause) for w in FAMILY_WORDS):
            family_wide.append(clause)
            continue
        else:
            # Clauses without a relation word belong to the writer, unless the
            # previous clause started describing someone else ("my son is 8, lactose intolerant").
            current = current if current != "Me" and _is_continuation(clause) else "Me"
        _apply(members[current], clause)

    for clause in family_wide:
        for m in members.values():
            _apply(m, clause, diets_only=True)
    # Drop an empty "Me" if the text was only about other people.
    if len(members) > 1 and _is_empty(members["Me"]):
        members.pop("Me")
    return Household(members=list(members.values()))


def _is_continuation(clause: str) -> bool:
    return bool(re.match(r"^(is|he|she|who|age|aged|\d+)\b", clause)) or \
        any(contains_term(clause, k) for k in ("lactose intolerant", "lactose intolerance"))


def _blank(name: str, relation: str) -> dict:
    return {"name": name, "relation": relation, "age": None, "allergens": [], "diet_rules": [],
            "conditions": [], "limits": {}, "avoid_ingredients": [], "notes": ""}


def _is_empty(m: dict) -> bool:
    return not (m["allergens"] or m["diet_rules"] or m["conditions"] or m["limits"] or m["avoid_ingredients"])


def _add(lst: list, v: str):
    if v and v not in lst:
        lst.append(v)


def _apply(m: dict, clause: str, diets_only: bool = False) -> None:
    for syn, diet in DIET_SYNONYMS.items():
        if contains_term(clause, syn) and not re.search(rf"\bnon[- ]?{re.escape(syn)}", clause):
            _add(m["diet_rules"], diet)
    if diets_only:
        return
    for syn, cond in sorted(CONDITION_SYNONYMS.items(), key=lambda kv: -len(kv[0])):
        if syn in AMBIGUOUS_CONDITION_KEYS:
            continue
        if contains_term(clause, syn):
            _add(m["conditions"], cond)
    if "prediabetes" in m["conditions"] and "diabetes" in m["conditions"]:
        m["conditions"].remove("diabetes")

    age = (re.search(r"\b(\d{1,2})\s*(?:-|\s)?(?:years?|yrs?|yo)\b", clause)
           or re.search(r"\baged?\s*(\d{1,2})\b", clause)
           or re.search(r"\bis\s+(\d{1,2})\b(?!\s*(?:g|mg|kg|%))", clause))
    if age:
        m["age"] = int(age.group(1))

    if re.search(r"allerg", clause):
        for entry in allergen_table()["by_key"].values():
            for syn in entry["synonyms"]:
                if contains_term(clause, syn):
                    _add(m["allergens"], resolve_allergen(syn) or syn)
                    break
        if "tree_nuts" in m["allergens"] and any(a in m["allergens"] for a in ("cashew", "almond", "walnut", "pistachio")):
            m["allergens"].remove("tree_nuts")  # "cashew nuts" should not mean all tree nuts

    if re.search(r"(cut|reduc|low|less|limit|watch)\w*\s+(on\s+)?(sodium|salt)", clause):
        m["limits"]["sodium_mg_per_day"] = 1500
    if re.search(r"(cut|reduc|low|less|limit|watch)\w*\s+(on\s+)?sugar", clause) or \
            any(c in m["conditions"] for c in ("diabetes", "prediabetes")):
        m["limits"]["sugar_g_per_day"] = 20

    for mt in re.finditer(r"\b(?:avoid|avoids|avoiding|no|don't eat|doesn't eat|hate)\s+([a-z][a-z\s\-]{2,25})", clause):
        item = mt.group(1).strip()
        item = re.split(r"\b(and|or|because|as)\b", item)[0].strip()
        if item and not resolve_allergen(item) and item not in DIET_SYNONYMS and item not in ("onion garlic",):
            _add(m["avoid_ingredients"], item)
