"""
Profile-parser evaluation: 10 free-text profiles vs expected JSON, field-level accuracy.
Compares the Gemini parser (if GEMINI_API_KEY is set) with the deterministic keyword baseline.

Usage (from /backend):  python eval/profile_parser_eval.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import config  # noqa: E402
from llm import prompts  # noqa: E402
from llm.gemini_client import LLMError, gemini  # noqa: E402
from rules.data import resolve_allergen  # noqa: E402
from rules.profile_keywords import parse_profile_keywords  # noqa: E402
from schemas import Household  # noqa: E402

FIELDS = ["allergens", "diet_rules", "conditions"]


def llm_parse(text: str) -> Household:
    data = gemini.generate_json("profile_parse", prompts.profile_parse_prompt(text), temperature=0.0,
                                max_tokens=config.MAX_TOKENS_PROFILE)
    return Household.model_validate(data)


def score(h: Household, expected: list[dict]) -> tuple[int, int, list[str]]:
    correct, total, notes = 0, 0, []
    members = list(h.members)
    for exp in expected:
        total += 1  # member found with the right relation
        m = next((x for x in members if x.relation == exp["relation"]), None)
        if m is None:
            notes.append(f"missing member {exp['relation']}")
            total += len(FIELDS)
            continue
        correct += 1
        members.remove(m)
        for f in FIELDS:
            total += 1
            got = set(getattr(m, f))
            if f == "allergens":
                got = {resolve_allergen(a) or a for a in got}
            if got == set(exp[f]):
                correct += 1
            else:
                notes.append(f"{exp['relation']}.{f}: got {sorted(got)} expected {sorted(exp[f])}")
    if members:
        notes.append(f"extra members: {[m.relation for m in members]}")
    return correct, total, notes


def main():
    cases = json.loads((HERE / "profile_cases.json").read_text(encoding="utf-8"))
    parsers = {"keyword_baseline": parse_profile_keywords}
    if gemini.available:
        parsers["gemini"] = llm_parse
    out_rows, totals = [], {k: [0, 0] for k in parsers}
    for i, case in enumerate(cases, 1):
        for name, fn in parsers.items():
            try:
                c, t, notes = score(fn(case["text"]), case["expected"])
            except LLMError as exc:
                c, t, notes = 0, 1 + 4 * len(case["expected"]), [f"LLM error: {exc}"]
            totals[name][0] += c
            totals[name][1] += t
            out_rows.append({"case": i, "parser": name, "correct": c, "total": t, "notes": "; ".join(notes)})

    results = HERE / "results"
    results.mkdir(exist_ok=True)
    with open(results / "profile_parser_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case", "parser", "correct", "total", "notes"])
        w.writeheader()
        w.writerows(out_rows)
    md = ["# Profile parser field accuracy", "", "| Parser | Field accuracy |", "|---|---|"]
    md += [f"| {k} | {c}/{t} = {c / t:.0%} |" for k, (c, t) in totals.items()]
    if "gemini" not in parsers:
        md.append("\n(Gemini not evaluated: GEMINI_API_KEY not set.)")
    (results / "profile_parser_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    for r in out_rows:
        if r["notes"]:
            print(f"  case {r['case']} [{r['parser']}]: {r['notes']}")


if __name__ == "__main__":
    main()
