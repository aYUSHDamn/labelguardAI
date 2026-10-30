"""
Open Food Facts client (no LLM). Read-only, cached in SQLite, throttled below the
published limits (10 search req/min, 15 product req/min per IP). Any failure
returns None / [] so callers fall back to the local Indian products CSV.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

import config
import db
from rules.text import split_ingredients
from schemas import Extraction

log = logging.getLogger("labelguard.off")

FIELDS = ("code,product_name,product_name_en,brands,categories_tags,ingredients_text,ingredients_text_en,"
          "nutriments,additives_tags,allergens_tags,traces_tags,labels_tags,serving_size,serving_quantity,"
          "image_front_small_url,countries_tags")

_lock = threading.Lock()
_last_call = {"search": 0.0, "product": 0.0}
_failed_until: dict[str, float] = {}


def _throttle(kind: str) -> None:
    gap = config.OFF_SEARCH_MIN_INTERVAL_S if kind == "search" else config.OFF_PRODUCT_MIN_INTERVAL_S
    with _lock:
        wait = _last_call[kind] + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[kind] = time.monotonic()


def _get(kind: str, url: str, params: dict) -> Optional[dict]:
    if not config.OFF_ENABLED:
        return None
    _throttle(kind)
    try:
        r = requests.get(url, params=params, timeout=config.OFF_TIMEOUT_S,
                         headers={"User-Agent": config.OFF_USER_AGENT})
        if r.status_code != 200:
            log.warning("OFF %s returned HTTP %s", kind, r.status_code)
            return None
        return r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("OFF %s failed: %s", kind, exc)
        return None


def get_product(barcode: str) -> Optional[dict]:
    key = f"product:{barcode}"
    cached = db.kv_get("off_cache", key, max_age_hours=config.OFF_CACHE_TTL_HOURS)
    if cached is not None:
        return cached or None
    data = _get("product", config.OFF_BASE_URL + config.OFF_PRODUCT_PATH.format(barcode=barcode), {"fields": FIELDS})
    if data is None:
        return None  # network problem: do not cache
    product = data.get("product") if data.get("status") in (1, "success") else None
    db.kv_put("off_cache", key, product or {})
    return product


def search_category(category: str) -> list[dict]:
    tags = config.CATEGORIES.get(category) or []
    if not tags:
        return []
    key = f"search:{category}"
    cached = db.kv_get("off_cache", key, max_age_hours=config.OFF_CACHE_TTL_HOURS)
    if cached is not None:
        return cached
    if _failed_until.get(category, 0) > time.monotonic():
        return []  # OFF failed recently: don't make the demo wait again
    params = {config.OFF_CATEGORY_PARAM: tags[0], "fields": FIELDS, "page_size": config.OFF_PAGE_SIZE}
    if config.OFF_COUNTRY_PARAM:
        params[config.OFF_COUNTRY_PARAM] = config.OFF_COUNTRY_VALUE
    data = _get("search", config.OFF_BASE_URL + config.OFF_SEARCH_PATH, params)
    if data is None:
        _failed_until[category] = time.monotonic() + 1800  # retry in 30 min; fallback CSV meanwhile
        return []
    products = data.get("products") or []
    # Prefer products sold in India when the server ignored the country filter.
    products.sort(key=lambda p: "en:india" not in (p.get("countries_tags") or []))
    db.kv_put("off_cache", key, products)
    return products


def _num(v) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def product_to_extraction(p: dict, category: Optional[str] = None) -> Optional[Extraction]:
    """Map an OFF product to our Extraction schema. Returns None if there is too little data to score."""
    if not p:
        return None
    n = p.get("nutriments") or {}
    sodium_g = _num(n.get("sodium_100g"))
    salt_g = _num(n.get("salt_100g"))
    sodium_mg = sodium_g * 1000 if sodium_g is not None else (salt_g * 400 if salt_g is not None else None)
    nutrition = {
        "energy_kcal": _num(n.get("energy-kcal_100g")),
        "sugar_g": _num(n.get("sugars_100g")),
        "added_sugar_g": _num(n.get("added-sugars_100g")),
        "sodium_mg": round(sodium_mg, 1) if sodium_mg is not None else None,
        "fat_g": _num(n.get("fat_100g")),
        "sat_fat_g": _num(n.get("saturated-fat_100g")),
        "trans_fat_g": _num(n.get("trans-fat_100g")),
        "carbs_g": _num(n.get("carbohydrates_100g")),
        "protein_g": _num(n.get("proteins_100g")),
        "fiber_g": _num(n.get("fiber_100g")),
    }
    if nutrition["sugar_g"] is None and nutrition["sodium_mg"] is None:
        return None
    text = p.get("ingredients_text_en") or p.get("ingredients_text") or ""
    ingredients = split_ingredients(text)
    # OFF's parsed additive tags ("en:e330") catch codes the text may hide.
    for tag in p.get("additives_tags") or []:
        code = tag.split(":")[-1].lstrip("e").upper()
        if not any(code.lower() in i.lower() for i in ingredients):
            ingredients.append(f"INS {code}")
    if not text:
        ingredients += [t.split(":")[-1] for t in p.get("allergens_tags") or []]
    return Extraction(
        product_name=p.get("product_name_en") or p.get("product_name") or None,
        brand=(p.get("brands") or "").split(",")[0].strip() or None,
        category=category or "other",
        ingredients=ingredients,
        nutrition_per_100g=nutrition,
        serving_size=p.get("serving_size"),
        serving_size_g=_num(p.get("serving_quantity")),
        may_contain=[t.split(":")[-1].replace("-", " ") for t in p.get("traces_tags") or []],
        barcode=p.get("code"),
        confidence=0.9 if text else 0.6,
    )
