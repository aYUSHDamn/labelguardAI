"""
Weekly family report.

build_facts()  -> every number, computed deterministically (tracker + rules engine + alternatives)
write_report() -> the LLM turns the facts into a short write-up (cached); template fallback
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from statistics import mean

import db
from alternatives.ranker import find_alternatives
from llm.tasks import cached_llm_json
from rules.engine import analyze
from schemas import Extraction, Household
from tracker.service import weekly_summary

log = logging.getLogger("labelguard.report")


def build_facts(household: Household, days: int = 7) -> dict:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).isoformat(timespec="seconds")
    week = weekly_summary(household, days)
    logs = db.logs_since(since)

    # Scans made this week, re-checked with the current profile.
    scans = [s for s in db.all_scans_full(200) if s["created_at"] >= since]
    misleading, avoided_for = 0, {m.name: 0 for m in household.members}
    scores = []
    for s in scans:
        a = analyze(Extraction.model_validate(s["extraction"]), household)
        scores.append(a["score"]["score"])
        misleading += sum(1 for c in a["claims"] if c["verdict"] == "misleading")
        for m in a["members"]:
            if m["status"] == "AVOID":
                avoided_for[m["member"]] = avoided_for.get(m["member"], 0) + 1

    members = []
    for m in week["members"]:
        mine = [l for l in logs if l["member"] == m["member"]]
        top = sorted(mine, key=lambda l: -(l["sugar_g"] or 0))[:2]
        members.append({
            "name": m["member"], "items_logged": m["items_logged"],
            "sugar_g": m["sugar_g"], "sugar_budget_g": m["sugar_budget_g"], "sugar_pct": m["sugar_pct"],
            "sodium_mg": m["sodium_mg"], "sodium_budget_mg": m["sodium_budget_mg"], "sodium_pct": m["sodium_pct"],
            "top_items": [f"{l['product_name']} ({l['sugar_g'] or 0:g} g sugar, {l['sodium_mg'] or 0:g} mg sodium)" for l in top],
            "scanned_products_unsuitable": avoided_for.get(m["member"], 0),
        })

    # Best swap for the worst things actually eaten (zero LLM).
    swaps, seen = [], set()
    worst_logged = sorted({l["scan_id"]: l for l in logs}.values(), key=lambda l: l["score"])[:3]
    for l in worst_logged:
        row = db.get_scan(l["scan_id"])
        if not row or row["product_name"] in seen:
            continue
        seen.add(row["product_name"])
        ex = Extraction.model_validate(row["extraction"])
        grams = sum(x["grams"] for x in logs if x["scan_id"] == l["scan_id"])
        try:
            alts = find_alternatives(ex, household, None, limit=1, weekly_grams=grams)["alternatives"]
        except Exception as exc:  # noqa: BLE001 - a report should never fail on one product
            log.warning("swap lookup failed: %s", exc)
            alts = []
        if alts:
            a = alts[0]
            swaps.append({"from": row["product_name"], "from_score": row["score"],
                          "to": f"{a['brand']} {a['product_name']}".strip(), "to_score": a["score"],
                          "why": a["reason"], "impact": a["swap_impact"]})

    start = (now - timedelta(days=days)).astimezone()
    return {
        "period": f"{start.strftime('%d %b')} - {now.astimezone().strftime('%d %b %Y')}",
        "days": days,
        "products_scanned": len(scans),
        "average_score": round(mean(scores)) if scores else None,
        "misleading_claims_caught": misleading,
        "items_logged": len(logs),
        "members": members,
        "budget_alerts": [msg for m in week["members"] for msg in m["messages"]],
        "worst_eaten": [{"product": w["product"], "score": w["score"], "member": w["member"]}
                        for w in week["worst_offenders"] if w.get("member")][:3],
        "swaps": swaps,
    }


def write_report(facts: dict, language: str, refresh: bool = False) -> tuple[dict, str]:
    # Only the facts the writer needs (keeps input tokens low).
    slim = {k: facts[k] for k in ("period", "products_scanned", "average_score", "misleading_claims_caught",
                                  "items_logged", "members", "budget_alerts", "worst_eaten", "swaps")}
    from llm import prompts
    data, source = cached_llm_json("report", prompts.report_prompt(slim, language), key_parts=(slim, language),
                                   refresh=refresh, max_tokens=1500)
    if data and data.get("summary"):
        names = {m["name"] for m in facts["members"]}
        data["members"] = [m for m in data.get("members", []) if m.get("name") in names]
        data["tips"] = [str(t) for t in (data.get("tips") or [])][:4]
        return data, source
    return template_report(facts), "template_fallback"


def template_report(f: dict) -> dict:
    """Deterministic write-up used when the AI is unavailable."""
    if not f["items_logged"]:
        summary = (f"{f['products_scanned']} products were scanned this week but nothing was logged as eaten yet. "
                   "Use 'Log this' on a scan to track sugar and sodium for each person.")
    else:
        summary = (f"This week {f['items_logged']} packaged items were logged and {f['products_scanned']} products scanned"
                   f"{f' (average score ' + str(f['average_score']) + '/100)' if f['average_score'] is not None else ''}. "
                   f"{f['misleading_claims_caught']} misleading label claims were caught.")
    members = []
    for m in f["members"]:
        note = (f"Used {m['sugar_pct']}% of the weekly sugar budget and {m['sodium_pct']}% of sodium "
                f"from {m['items_logged']} logged item(s).") if m["items_logged"] else "Nothing logged this week."
        members.append({"name": m["name"], "note": note})
    tips = [f"Swap {s['from']} for {s['to']}: {s['why']}." for s in f["swaps"]][:3]
    tips += ["Log snacks right after eating so the budgets stay accurate.",
             "Check the claim checker before trusting words like 'healthy' or 'no added sugar'."][: max(0, 3 - len(tips))]
    worst = max(f["members"], key=lambda m: max(m["sugar_pct"], m["sodium_pct"]), default=None)
    headline = (f"{worst['name']} needs the most attention this week" if worst and worst["items_logged"]
                else "Start logging to see your family's week")
    return {"headline": headline, "summary": summary, "members": members, "tips": tips}
