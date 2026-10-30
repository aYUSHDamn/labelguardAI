"""
Collects the experiment outputs in backend/eval/results (+ the app's LLM usage log) into docs/paper_results.json
for make_paper.py.  Run after run_eval.py, chat_baseline.py and profile_parser_eval.py.

    python docs/collect_results.py
The two free-text fields ("degrade_text", "discussion", profile "text") live in docs/paper_text.json.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE.parent / "backend" / "eval"
RES = EV / "results"
TEXT = json.loads((HERE / "paper_text.json").read_text(encoding="utf-8")) if (HERE / "paper_text.json").exists() else {}


def pct(s):
    return float(s.strip().rstrip("%")) / 100


def parse_extraction():
    md = (RES / "summary.md").read_text(encoding="utf-8")
    out, rep = {}, {}
    for line in md.splitlines():
        m = re.match(r"\|\s*(clean|blur|rotate|low_light)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+) / ([\d.]+)\s*\|\s*([\d.]+) / ([\d.]+)\s*\|\s*([\d.]+%)\s*\|\s*([\d.nan]+)\s*\|\s*(\d+)\s*\|", line)
        if m:
            k = m.group(1)
            out[k] = {"ing_f1": float(m.group(2)), "sugar_p": float(m.group(3)), "sugar_r": float(m.group(4)),
                      "all_p": float(m.group(5)), "all_r": float(m.group(6)), "nut_acc": pct(m.group(7)),
                      "score_err": float(m.group(8)), "n": int(m.group(9))}
        if "Rules output identical" in line:
            rep["rules_identical"] = re.search(r"(\d+/\d+)", line).group(1)
        if "Mean score std-dev" in line:
            rep["sd"] = float(re.findall(r"([\d.]+)\s*\|\s*$", line)[0])
        if "identical score every run" in line:
            rep["identical"] = int(re.search(r"\|\s*(\d+)/\d+", line).group(1))
        if "Jaccard" in line:
            rep["jaccard"] = float(re.findall(r"([\d.]+)\s*\|\s*$", line)[0])
    return out, rep


def parse_chat():
    truth = {r["product_name"]: float(r["true_score"]) for r in csv.DictReader(open(EV / "ground_truth" / "labels.csv", encoding="utf-8"))}
    runs = {}
    for r in csv.DictReader(open(RES / "chat_baseline.csv", encoding="utf-8")):
        runs.setdefault((float(r["temperature"]), r["product"]), []).append(float(r["score"]))

    def pearson(x, y):
        mx, my = statistics.mean(x), statistics.mean(y)
        num = sum((a - mx) * (b - my) for a, b in zip(x, y))
        den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
        return num / den if den else float("nan")

    out = {}
    for temp, key in ((1.0, "t1"), (0.0, "t0")):
        items = {p: v for (t, p), v in runs.items() if t == temp}
        sds = [statistics.pstdev(v) for v in items.values()]
        rng = [max(v) - min(v) for v in items.values()]
        out[f"{key}_sd"] = statistics.mean(sds)
        out[f"{key}_range"] = statistics.mean(rng)
        out[f"{key}_ident"] = f"{sum(1 for s in sds if s == 0)}/{len(items)}"
        out[f"{key}_r"] = pearson([statistics.mean(v) for v in items.values()], [truth[p] for p in items])
        out["n_products"] = len(items)
        out["runs"] = max(len(v) for v in items.values())
    return out


def parse_profile():
    md = (RES / "profile_parser_summary.md").read_text(encoding="utf-8")
    kw = re.search(r"keyword_baseline \| (\d+)/(\d+) = (\d+%)", md)
    llm = re.search(r"gemini \| (\d+)/(\d+) = (\d+%)", md)
    return {"kw_fields": f"{kw.group(1)} / {kw.group(2)}", "kw_acc": kw.group(3),
            "llm_fields": f"{llm.group(1)} / {llm.group(2)}" if llm else "n/a", "llm_acc": llm.group(3) if llm else "n/a",
            "text": TEXT.get("profile_text", "")}


def usage():
    c = sqlite3.connect(HERE.parent / "backend" / "labelguard.db")
    names = {"profile_parse": "Profile parsing", "extraction": "Label extraction (vision)", "explanation": "Family summary",
             "ask": "Ask about a product (optional)", "report": "Weekly report (optional)"}
    rows = []
    for purpose in names:
        r = c.execute("select sum(ok), count(*), avg(case when ok then input_tokens end), avg(case when ok then output_tokens end), "
                      "avg(case when ok then latency_ms end) from llm_calls where purpose = ?", (purpose,)).fetchone()
        if r[1]:
            rows.append({"task": names[purpose], "ok": int(r[0] or 0), "calls": r[1], "in": int(r[2] or 0), "out": int(r[3] or 0),
                         "sec": (r[4] or 0) / 1000})
    return rows


def main():
    ext, rep = parse_extraction()
    n_images = sum(1 for _ in csv.DictReader(open(EV / "ground_truth" / "labels.csv", encoding="utf-8")))
    data = {
        "n_images": n_images, "model": "gemini-3.6-flash", "n_tests": 46, "n_endpoints": 32,
        "loc_py": 4443, "loc_js": 3293,
        "extract": ext, "repeat": rep, "chat": parse_chat(), "profile": parse_profile(), "usage": usage(),
        "degrade_text": TEXT.get("degrade_text", ""), "discussion": TEXT.get("discussion", ""),
    }
    (HERE / "paper_results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data, indent=2)[:2500])


if __name__ == "__main__":
    main()
