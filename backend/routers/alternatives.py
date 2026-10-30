from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter

import db
from alternatives.ranker import find_alternatives
from errors import APIError
from pipeline import current_household
from schemas import Extraction, FeedbackRequest

router = APIRouter(prefix="/api/alternatives", tags=["alternatives"])


@router.post("/feedback", summary="Thumbs up/down on an alternative (re-ranks future suggestions)")
def feedback(req: FeedbackRequest):
    fid = db.insert_feedback(req.scan_id, req.product_code, req.product_name, req.brand, req.vote, req.reason)
    return {"id": fid, "saved": True}


@router.get("/{scan_id}", summary="Top 3 better alternatives in the same category (zero LLM)")
def alternatives(scan_id: int, member: Optional[str] = None):
    row = db.get_scan(scan_id)
    if not row:
        raise APIError(404, "not_found", f"Scan {scan_id} not found.")
    ex = Extraction.model_validate(row["extraction"])
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    weekly_grams = sum(l["grams"] for l in db.logs_since(since) if l["scan_id"] == scan_id) or None
    result = find_alternatives(ex, current_household(), member, weekly_grams=weekly_grams)
    result["scan_id"] = scan_id
    if ex.category == "other":
        result["note"] = "This product's category is 'other', so we can't search for like-for-like alternatives."
    return result
