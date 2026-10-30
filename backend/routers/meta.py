from fastapi import APIRouter

import config
import db
from rules import data
from rules.scoring import FORMULA

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", summary="Status check")
def health():
    try:
        db.list_scans(limit=1)
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok, "llm_configured": bool(config.GEMINI_API_KEY),
            "model": config.GEMINI_MODEL, "off_enabled": config.OFF_ENABLED, "disclaimer": config.DISCLAIMER}


@router.get("/score/formula", summary="The documented health-score formula")
def formula():
    return FORMULA


@router.get("/stats", summary="LLM usage + data table sizes (for the About/Evaluation page)")
def stats():
    return {
        "llm_usage": db.llm_usage_summary(),
        "tables": {"sugar_aliases": len(data.sugar_aliases()), "additives": len(data.additives()),
                   "allergens": len(data.allergen_table()["by_key"]), "diet_rules": len(data.diet_rules()),
                   "fallback_products": len(data.fallback_products())},
        "model": config.GEMINI_MODEL,
        "categories": list(config.CATEGORIES),
    }
