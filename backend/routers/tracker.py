from fastapi import APIRouter

import db
from errors import APIError
from pipeline import current_household
from schemas import Extraction, LogRequest
from tracker.service import default_grams, nutrients_for, weekly_summary

router = APIRouter(prefix="/api", tags=["tracker"])


@router.post("/log", summary="Log a scanned product as eaten by a member (zero LLM)")
def log_intake(req: LogRequest):
    row = db.get_scan(req.scan_id)
    if not row:
        raise APIError(404, "not_found", f"Scan {req.scan_id} not found.")
    household = current_household()
    if req.member not in {m.name for m in household.members}:
        raise APIError(400, "unknown_member", f"'{req.member}' is not in your household profile.")
    ex = Extraction.model_validate(row["extraction"])
    grams = default_grams(ex, req.servings, req.grams)
    n = nutrients_for(ex, grams)
    log_id = db.insert_log(req.scan_id, req.member, grams, n["sugar_g"], n["sodium_mg"], n["sat_fat_g"])
    summary = weekly_summary(household)
    me = next(m for m in summary["members"] if m["member"] == req.member)
    return {"log_id": log_id, "grams": grams, "nutrients": n, "member_week": me}


@router.get("/tracker", summary="Weekly sugar/sodium vs limits per member, score trend, worst offenders")
def tracker(days: int = 7):
    return weekly_summary(current_household(), days=min(max(days, 1), 31))


@router.delete("/log/{log_id}", summary="Delete an intake log entry")
def delete_log(log_id: int):
    if not db.delete_log(log_id):
        raise APIError(404, "not_found", f"Log {log_id} not found.")
    return {"deleted": True}


@router.get("/report", summary="Weekly family report: numbers from the rules engine, write-up by the LLM (cached)")
def report(language: str = "en", days: int = 7, refresh: bool = False):
    from tracker.report import build_facts, write_report
    facts = build_facts(current_household(), days=min(max(days, 1), 31))
    text, source = write_report(facts, language if language in ("en", "hi", "ta") else "en", refresh=refresh)
    return {"facts": facts, "report": text, "source": source, "language": language}
