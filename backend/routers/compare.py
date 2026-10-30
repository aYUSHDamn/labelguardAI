from fastapi import APIRouter

from errors import APIError
from pipeline import current_household, load_scan
from schemas import CompareRequest

router = APIRouter(prefix="/api", tags=["compare"])
RANK = {"SAFE": 0, "WARN": 1, "AVOID": 2}


def _side(scan: dict, member: str | None) -> dict:
    a = scan["analysis"]
    members = a["members"]
    chosen = next((m for m in members if m["member"] == member), None) if member and member != "all" else None
    status = chosen["status"] if chosen else max((m["status"] for m in members), key=RANK.get)
    flags = chosen["flags"] if chosen else [dict(f, member=m["member"]) for m in members for f in m["flags"]]
    return {"scan_id": scan["scan_id"], "product_name": scan["extraction"]["product_name"] or f"Scan {scan['scan_id']}",
            "brand": scan["extraction"]["brand"], "score": a["score"]["score"], "color": a["score"]["color"],
            "label": a["score"]["label"], "status": status, "flags": flags[:8],
            "hidden_sugars": [h["alias"] for h in a["hidden_sugars"]],
            "additives_flagged": [f"{x['name']} ({x['concern']})" for x in a["additives"] if x["concern"] in ("medium", "high")],
            "misleading_claims": [c["claim"] for c in a["claims"] if c["verdict"] == "misleading"],
            "nutrition_per_100g": scan["extraction"]["nutrition_per_100g"],
            "basis": a["score"]["basis"]}


@router.post("/compare", summary="Compare 2-4 products for the selected member and name a winner (zero LLM)")
def compare(req: CompareRequest):
    ids = list(dict.fromkeys(req.scan_ids or [i for i in (req.scan_id_a, req.scan_id_b) if i]))[:4]
    if len(ids) < 2:
        raise APIError(400, "need_two", "Pick at least two different products to compare.")
    household = current_household()
    scans = [load_scan(i, household) for i in ids]
    if not all(scans):
        raise APIError(404, "not_found", "One of the scans was not found.")
    items = [_side(s, req.member) for s in scans]
    # Ranking: safer verdict first, then higher score. Same inputs -> same order.
    ranked = sorted(items, key=lambda s: (RANK[s["status"]], -s["score"]))
    best, second = ranked[0], ranked[1]
    who = req.member if req.member and req.member != "all" else "your family"
    if (RANK[best["status"]], best["score"]) == (RANK[second["status"]], second["score"]):
        winner, why = None, "It's a tie on both safety and score."
    elif RANK[best["status"]] < RANK[second["status"]]:
        winner, why = best["scan_id"], f"{best['product_name']} is the safest pick for {who} ({best['status']} vs {second['status']})."
    else:
        winner, why = best["scan_id"], (f"{best['product_name']} scores highest ({best['score']} vs {second['score']}) "
                                        f"with the same safety status for {who}.")
    for rank, s in enumerate(ranked, 1):
        s["rank"] = rank
    out = {"items": items, "winner_scan_id": winner, "reason": why, "member": req.member or "all"}
    if len(items) == 2:  # backward-compatible keys
        out["a"], out["b"] = items
    return out
