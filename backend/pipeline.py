"""
Scan pipeline: image -> (cache | barcode+OFF | Gemini vision) -> rules engine -> stored scan.

Token budget per scan: 0 calls if the image or barcode was seen before,
0 calls if a barcode is decoded and Open Food Facts has the product,
otherwise exactly 1 vision call.
"""
from __future__ import annotations

import hashlib
import io
import logging
from typing import Optional

import db
from alternatives import off_client
from llm.gemini_client import prepare_image
from llm.tasks import extract_label
from rules.engine import analyze
from schemas import Extraction, Household, Member

log = logging.getLogger("labelguard.pipeline")


def current_household() -> Household:
    saved = db.get_household()
    return Household.model_validate(saved["profile"]) if saved else Household(members=[Member(name="Me")])


def decode_barcode(jpeg: bytes) -> Optional[str]:
    """Optional extra: needs `pip install pyzbar` (+ zbar library on macOS/Linux)."""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
    except Exception:  # noqa: BLE001 - pyzbar missing or zbar DLL missing
        return None
    try:
        for sym in decode(Image.open(io.BytesIO(jpeg))):
            digits = sym.data.decode("ascii", "ignore").strip()
            if digits.isdigit() and 8 <= len(digits) <= 14:
                return digits
    except Exception:  # noqa: BLE001
        return None
    return None


def _merge_missing(primary: Extraction, extra: Extraction) -> Extraction:
    """Fill nulls in a vision extraction from OFF data (never overwrite what was read)."""
    p = primary.model_dump()
    e = extra.model_dump()
    for k, v in e["nutrition_per_100g"].items():
        if p["nutrition_per_100g"].get(k) is None and v is not None:
            p["nutrition_per_100g"][k] = v
    for k in ("product_name", "brand"):
        p[k] = p[k] or e[k]
    if not p["ingredients"] and e["ingredients"]:
        p["ingredients"] = e["ingredients"]
    return Extraction.model_validate(p)


def extraction_from_barcode(barcode: str) -> tuple[Extraction, str, bool] | None:
    """Barcode typed by the user -> cache or Open Food Facts. Zero AI tokens. None if OFF doesn't know it."""
    hit = db.cache_get_extraction(f"bar:{barcode}")
    if hit:
        return Extraction.model_validate(hit["extraction"]), hit["source"], True
    product = off_client.get_product(barcode)
    ex = off_client.product_to_extraction(product, guess_category(product)) if product else None
    if not ex:
        return None
    ex.barcode = barcode
    db.cache_put_extraction(f"bar:{barcode}", ex.model_dump(), "open_food_facts")
    return ex, "open_food_facts", False


def guess_category(product: dict | None) -> str:
    """Map OFF category tags onto our fixed category list (first match wins)."""
    import config
    tags = " ".join((product or {}).get("categories_tags") or []).lower()
    for cat, off_tags in config.CATEGORIES.items():
        if any(f"en:{t}" in tags for t in off_tags):
            return cat
    return "other"


def extraction_from_image(raws: bytes | list[bytes], use_cache: bool = True) -> tuple[Extraction, str, str, bool]:
    """Returns (extraction, source, image_hash, cached). Accepts 1-3 photos of the same pack.
    Raises ValueError for bad images, LLMError for AI failure."""
    raws = raws if isinstance(raws, list) else [raws]
    image_hash = hashlib.sha256(b"".join(hashlib.sha256(r).digest() for r in raws)).hexdigest()
    if use_cache:
        hit = db.cache_get_extraction(f"img:{image_hash}")
        if hit:
            return Extraction.model_validate(hit["extraction"]), hit["source"], image_hash, True

    jpegs = [prepare_image(r) for r in raws]  # validates + resizes to <= 1024 px
    jpeg = jpegs if len(jpegs) > 1 else jpegs[0]

    barcode = next((b for b in (decode_barcode(j) for j in jpegs) if b), None)
    if barcode:
        hit = db.cache_get_extraction(f"bar:{barcode}") if use_cache else None
        if hit:
            db.cache_put_extraction(f"img:{image_hash}", hit["extraction"], hit["source"])
            return Extraction.model_validate(hit["extraction"]), hit["source"], image_hash, True
        product = off_client.get_product(barcode)
        ex = off_client.product_to_extraction(product) if product else None
        if ex and ex.ingredients:
            ex.barcode = barcode
            db.cache_put_extraction(f"img:{image_hash}", ex.model_dump(), "open_food_facts")
            db.cache_put_extraction(f"bar:{barcode}", ex.model_dump(), "open_food_facts")
            return ex, "open_food_facts", image_hash, False

    ex = extract_label(jpeg)  # the one vision LLM call
    source = "gemini_vision"
    if ex.barcode and not barcode:
        product = off_client.get_product(ex.barcode)
        off_ex = off_client.product_to_extraction(product) if product else None
        if off_ex:
            ex = _merge_missing(ex, off_ex)
            source = "gemini_vision+open_food_facts"
    if use_cache:
        db.cache_put_extraction(f"img:{image_hash}", ex.model_dump(), source)
        if ex.barcode:
            db.cache_put_extraction(f"bar:{ex.barcode}", ex.model_dump(), source)
    return ex, source, image_hash, False


def store_scan(ex: Extraction, source: str, image_hash: Optional[str], household: Household) -> tuple[int, dict]:
    analysis = analyze(ex, household)
    scan_id = db.insert_scan(ex.model_dump(), analysis["score"]["score"], source, image_hash)
    return scan_id, analysis


def scan_payload(scan_id: int, ex: Extraction, analysis: dict, source: str, cached: bool) -> dict:
    return {"scan_id": scan_id, "source": source, "cached": cached, "extraction": ex.model_dump(),
            "analysis": analysis}


def load_scan(scan_id: int, household: Optional[Household] = None) -> Optional[dict]:
    """Re-run the rules on a stored extraction with the CURRENT profile (cheap and deterministic)."""
    row = db.get_scan(scan_id)
    if not row:
        return None
    ex = Extraction.model_validate(row["extraction"])
    analysis = analyze(ex, household or current_household())
    return {**scan_payload(scan_id, ex, analysis, row["source"], True), "created_at": row["created_at"]}
