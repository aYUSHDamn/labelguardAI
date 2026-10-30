from fastapi import APIRouter

import db
from llm.tasks import parse_profile
from pipeline import current_household
from rules.data import resolve_allergen
from schemas import Household, ProfileParseRequest, ProfileParseResponse

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _normalise(h: Household) -> Household:
    """Map typed allergens to canonical keys where we know them ('cashews' -> 'cashew')."""
    for m in h.members:
        m.allergens = list(dict.fromkeys(resolve_allergen(a) or a for a in m.allergens))
    return h


@router.post("/parse", response_model=ProfileParseResponse,
             summary="Free text -> structured household (1 LLM call, cached; keyword fallback)")
def parse(req: ProfileParseRequest):
    household, source, warning = parse_profile(req.text)
    return ProfileParseResponse(household=_normalise(household), source=source, warning=warning)


@router.get("", summary="Load the saved household (default single member if none saved)")
def get_profile():
    saved = db.get_household()
    return {"household": current_household().model_dump(), "saved": bool(saved),
            "raw_text": saved["raw_text"] if saved else None}


@router.put("", summary="Save the (user-edited) household")
def put_profile(body: dict):
    household = _normalise(Household.model_validate(body.get("household", body)))
    db.save_household(household.model_dump(), body.get("raw_text"))
    return {"household": household.model_dump(), "saved": True}
