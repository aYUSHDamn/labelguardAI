"""Loads the lookup tables in /backend/data once and exposes them as plain Python objects."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache

from config import DATA_DIR


@dataclass(frozen=True)
class Additive:
    ins: str
    name: str
    aliases: tuple[str, ...]
    cls: str
    purpose: str
    concern: str  # low | medium | high
    note: str


@dataclass(frozen=True)
class DietRule:
    terms: tuple[str, ...]   # plain words, or 'ins:471' for additive codes
    category: str
    status: dict             # diet -> 'avoid' | 'check'
    reason: str


def _read_csv(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


@lru_cache(maxsize=1)
def sugar_aliases() -> dict[str, dict]:
    return {r["alias"].lower(): r for r in _read_csv("sugar_aliases.csv")}


@lru_cache(maxsize=1)
def additives() -> dict[str, Additive]:
    out = {}
    for r in _read_csv("additives.csv"):
        a = Additive(ins=r["ins"].lower(), name=r["name"],
                     aliases=tuple(x.strip().lower() for x in r["aliases"].split("|") if x.strip()),
                     cls=r["class"], purpose=r["purpose"], concern=r["concern"], note=r["note"])
        out[a.ins] = a
    return out


@lru_cache(maxsize=1)
def allergen_table() -> dict:
    with open(DATA_DIR / "allergens.json", encoding="utf-8") as f:
        data = json.load(f)
    return {"by_key": {a["key"]: a for a in data["allergens"]},
            "lactose_keywords": data["lactose_keywords"]}


@lru_cache(maxsize=1)
def diet_rules() -> list[DietRule]:
    out = []
    for r in _read_csv("diet_rules.csv"):
        status = {d: r[d] for d in ("vegetarian", "vegan", "jain", "halal") if r[d] in ("avoid", "check")}
        out.append(DietRule(terms=tuple(t.strip().lower() for t in r["terms"].split("|") if t.strip()),
                            category=r["category"], status=status, reason=r["reason"]))
    return out


@lru_cache(maxsize=1)
def fallback_products() -> list[dict]:
    return _read_csv("indian_products_fallback.csv")


def resolve_allergen(text: str) -> str | None:
    """Map whatever the user typed ('cashews', 'kaju', 'dairy') to an allergen key."""
    t = (text or "").strip().lower()
    if not t:
        return None
    table = allergen_table()["by_key"]
    if t in table:
        return t
    for key, a in table.items():
        if t in a["synonyms"] or t.rstrip("s") in a["synonyms"]:
            return key
    for key, a in table.items():  # e.g. "allergic to cashew nuts"
        if any(s in t for s in a["synonyms"] if len(s) > 3):
            return key
    return None
