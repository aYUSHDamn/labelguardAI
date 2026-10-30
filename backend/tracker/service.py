"""Intake tracker: weekly sugar / sodium budgets per member (zero LLM)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import db
from schemas import Extraction, Household


def nutrients_for(ex: Extraction, grams: float) -> dict:
    n = ex.nutrition_per_100g
    f = grams / 100.0
    return {k: (round(getattr(n, k) * f, 2) if getattr(n, k) is not None else None)
            for k in ("sugar_g", "sodium_mg", "sat_fat_g")}


def default_grams(ex: Extraction, servings: float, grams=None) -> float:
    if grams:
        return float(grams)
    return round((ex.serving_size_g or 100.0) * servings, 1)


def weekly_summary(household: Household, days: int = 7) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    logs = db.logs_since(since)
    members = []
    for m in household.members:
        mine = [l for l in logs if l["member"] == m.name]
        sugar = round(sum(l["sugar_g"] or 0 for l in mine), 1)
        sodium = round(sum(l["sodium_mg"] or 0 for l in mine), 0)
        sugar_budget = m.limits.sugar_g_per_day * days
        sodium_budget = m.limits.sodium_mg_per_day * days
        sugar_pct = round(sugar / sugar_budget * 100) if sugar_budget else 0
        sodium_pct = round(sodium / sodium_budget * 100) if sodium_budget else 0
        msgs = []
        for label, pct in (("sugar", sugar_pct), ("sodium", sodium_pct)):
            if pct >= 100:
                msgs.append(f"{m.name} is over the {days}-day {label} budget from packaged foods alone ({pct}%).")
            elif pct >= 50:
                msgs.append(f"{m.name} has used {pct}% of the {days}-day {label} budget on packaged foods.")
        members.append({
            "member": m.name, "items_logged": len(mine),
            "sugar_g": sugar, "sugar_budget_g": sugar_budget, "sugar_pct": sugar_pct,
            "sodium_mg": sodium, "sodium_budget_mg": sodium_budget, "sodium_pct": sodium_pct,
            "messages": msgs,
        })
    # Daily totals per member (for the day-by-day chart), oldest day first.
    local_day = lambda iso: datetime.fromisoformat(iso).astimezone().date().isoformat()  # noqa: E731
    today = datetime.now().astimezone().date()
    daily = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        row = {"date": d.isoformat(), "label": d.strftime("%a %d")}
        for m in household.members:
            day_logs = [l for l in logs if l["member"] == m.name and local_day(l["logged_at"]) == d.isoformat()]
            row[f"{m.name}|sugar"] = round(sum(l["sugar_g"] or 0 for l in day_logs), 1)
            row[f"{m.name}|sodium"] = round(sum(l["sodium_mg"] or 0 for l in day_logs), 0)
        daily.append(row)
    trend = list(reversed(db.list_scans(limit=20)))
    if logs:  # worst things actually eaten this week
        worst = [{"scan_id": w["scan_id"], "product": w["product_name"], "score": w["score"], "member": w["member"],
                  "sugar_g": w["sugar_g"], "sodium_mg": w["sodium_mg"]}
                 for w in sorted({l["scan_id"]: l for l in logs}.values(), key=lambda l: l["score"])[:5]]
    else:  # nothing logged yet: worst things scanned
        worst = [{"scan_id": s["id"], "product": s["product_name"], "score": s["score"], "member": None,
                  "sugar_g": None, "sodium_mg": None} for s in sorted(trend, key=lambda s: s["score"])[:5]]
    return {
        "days": days,
        "members": members,
        "score_trend": [{"scan_id": s["id"], "product": s["product_name"] or f"Scan {s['id']}", "score": s["score"],
                         "created_at": s["created_at"]} for s in trend],
        "worst_offenders": worst,
        "recent_logs": logs[:30],
        "daily": daily,
        "limits": {m.name: {"sugar_g": m.limits.sugar_g_per_day, "sodium_mg": m.limits.sodium_mg_per_day}
                   for m in household.members},
    }
