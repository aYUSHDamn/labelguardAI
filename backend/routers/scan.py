import json
import re
from typing import Optional

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

import config
import db
from errors import APIError
from llm.tasks import ask, explain
from pipeline import (current_household, extraction_from_barcode, extraction_from_image, load_scan, scan_payload,
                      store_scan)
from schemas import ExplainRequest, Extraction, ScanJsonRequest

router = APIRouter(prefix="/api", tags=["scan"])


class BarcodeRequest(BaseModel):
    barcode: str


class AskRequest(BaseModel):
    scan_id: int
    question: str = Field(min_length=2, max_length=300)
    language: str = "en"


def _demo_labels() -> dict:
    with open(config.DATA_DIR / "demo_labels.json", encoding="utf-8") as f:
        return json.load(f)


@router.post("/scan", summary="Upload 1-3 photos of one pack -> extraction + flags + score (0 or 1 LLM call)")
async def scan_image(file: Optional[UploadFile] = File(None), files: Optional[list[UploadFile]] = File(None)):
    uploads = ([file] if file else []) + (files or [])
    raws = [r for r in [await u.read() for u in uploads[:3]] if r]
    if not raws:
        raise APIError(400, "empty_file", "No image received. Please paste or take a photo.")
    if any(len(r) > config.MAX_UPLOAD_BYTES for r in raws):
        raise APIError(413, "file_too_large", "One image is over 12 MB. Please use a smaller photo.")
    try:
        ex, source, image_hash, cached = extraction_from_image(raws)
    except ValueError as exc:
        raise APIError(400, "bad_image", "That file isn't a readable image. Please use a JPG or PNG photo.") from exc
    no_nutrition = all(v is None for v in ex.nutrition_per_100g.model_dump().values()) and \
        all(v is None for v in ex.nutrition_per_serving.model_dump().values())
    if not ex.ingredients and no_nutrition:
        raise APIError(422, "unreadable_label",
                       "We couldn't find an ingredient list or nutrition table. Photograph the back of the pack "
                       "in good light, filling the frame.")
    scan_id, analysis = store_scan(ex, source, image_hash, current_household())
    return scan_payload(scan_id, ex, analysis, source, cached)


@router.post("/scan/barcode", summary="Look up a barcode on Open Food Facts and analyse it (zero LLM)")
def scan_barcode(req: BarcodeRequest):
    code = re.sub(r"\D", "", req.barcode)
    if not 8 <= len(code) <= 14:
        raise APIError(400, "bad_barcode", "Barcodes are 8 to 14 digits (EAN-8 / EAN-13 / UPC).")
    found = extraction_from_barcode(code)
    if not found:
        raise APIError(404, "barcode_not_found",
                       "Open Food Facts doesn't have this product yet (or is offline). Paste a photo of the label instead.")
    ex, source, cached = found
    scan_id, analysis = store_scan(ex, source, None, current_household())
    return scan_payload(scan_id, ex, analysis, source, cached)


@router.post("/scan/json", summary="Analyse an extraction you provide (manual entry; no LLM)")
def scan_json(req: ScanJsonRequest):
    scan_id, analysis = store_scan(req.extraction, "manual", None, current_household())
    return scan_payload(scan_id, req.extraction, analysis, "manual", False)


@router.get("/demo-labels", summary="Built-in demo labels (work without an API key)")
def demo_labels():
    return [{"key": k, "product_name": v["product_name"], "brand": v.get("brand"), "category": v["category"]}
            for k, v in _demo_labels().items()]


@router.post("/scan/demo/{key}", summary="Scan a built-in demo label (no LLM)")
def scan_demo(key: str):
    labels = _demo_labels()
    if key not in labels:
        raise APIError(404, "not_found", f"No demo label called '{key}'.")
    ex = Extraction.model_validate(labels[key])
    scan_id, analysis = store_scan(ex, "demo", None, current_household())
    return scan_payload(scan_id, ex, analysis, "demo", False)


@router.get("/scans", summary="Scan history (newest first)")
def scans(limit: int = 50):
    return db.list_scans(limit=min(max(limit, 1), 200))


@router.get("/scan/{scan_id}", summary="Re-analyse a stored scan with the current profile (no LLM)")
def get_scan(scan_id: int):
    result = load_scan(scan_id)
    if not result:
        raise APIError(404, "not_found", f"Scan {scan_id} not found.")
    return result


@router.delete("/scan/{scan_id}", summary="Delete a scan (and its intake logs)")
def delete_scan(scan_id: int):
    if not db.delete_scan(scan_id):
        raise APIError(404, "not_found", f"Scan {scan_id} not found.")
    return {"deleted": True}


@router.post("/scan/explain", summary="Short personalised explanation (1 small LLM call, cached; template fallback)")
def explain_scan(req: ExplainRequest):
    result = load_scan(req.scan_id)
    if not result:
        raise APIError(404, "not_found", f"Scan {req.scan_id} not found.")
    members = result["analysis"]["members"]
    if req.member and req.member != "all":
        members = [m for m in members if m["member"] == req.member] or members
    text, source = explain(result["extraction"], result["analysis"], members, req.language, req.eli12)
    return {"scan_id": req.scan_id, "explanation": text, "source": source, "language": req.language,
            "eli12": req.eli12, "disclaimer": config.DISCLAIMER}


@router.post("/scan/ask", summary="Ask a question about a scanned product (optional LLM call, grounded; rules fallback)")
def ask_scan(req: AskRequest):
    result = load_scan(req.scan_id)
    if not result:
        raise APIError(404, "not_found", f"Scan {req.scan_id} not found.")
    text, source = ask(result["extraction"], result["analysis"], req.question, req.language)
    return {"answer": text, "source": source}
