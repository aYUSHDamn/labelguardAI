"""
Plain-LLM consistency baseline (answers "why not just ask a chatbot?").

For 8 test products, ask the SAME model that LabelGuard uses to "rate the healthiness of this food
from 0 to 100" N times, at the default chat temperature (1.0) and at temperature 0. LabelGuard's own
score for the same inputs is a deterministic function, so its run-to-run standard deviation is 0.

Run from /backend (needs GEMINI_API_KEY):  python eval/chat_baseline.py [--runs 5]
Outputs: eval/results/chat_baseline.csv and eval/results/chat_baseline.md
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import config  # noqa: E402
from llm.gemini_client import LLMError, gemini  # noqa: E402

PROMPT = """You are a nutrition assistant. Rate how healthy this packaged food is on a scale from 0 (very unhealthy)
to 100 (very healthy) for a typical adult.

Product: {name}
Ingredients: {ingredients}
Nutrition per 100 {unit}: energy {energy_kcal} kcal, protein {protein_g} g, total sugars {sugar_g} g, total fat {fat_g} g,
saturated fat {sat_fat_g} g, fibre {fiber_g} g, sodium {sodium_mg} mg.

Return ONLY JSON: {{"score": <integer 0-100>}}"""

LIQUID = {"soft_drinks", "juices", "dairy_drinks"}
PICK = ["FB-001", "FB-004", "FB-011", "FB-031", "FB-035", "FB-040", "FB-050", "FB-090"]


def pearson(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    truth = {r["image_file"].split(".")[0]: r for r in csv.DictReader(open(HERE / "ground_truth" / "labels.csv", encoding="utf-8"))}
    rows, summary = [], {0.0: [], 1.0: []}
    for code in PICK:
        t = truth[code]
        prompt = PROMPT.format(name=t["product_name"], ingredients=", ".join(i.strip() for i in t["ingredients"].split(";")),
                               unit="ml" if t["category"] in LIQUID else "g", **{k: t[k] for k in (
                                   "energy_kcal", "protein_g", "sugar_g", "fat_g", "sat_fat_g", "fiber_g", "sodium_mg")})
        for temp in (1.0, 0.0):
            scores = []
            for run in range(args.runs):
                try:
                    data = gemini.generate_json("chat_baseline", prompt, temperature=temp, max_tokens=512, timeout_s=25)
                    score = max(0, min(100, int(round(float(data["score"])))))
                except (LLMError, KeyError, ValueError, TypeError) as exc:
                    print(f"  {code} T={temp} run {run + 1}: failed ({exc})", flush=True)
                    continue
                scores.append(score)
                rows.append({"product": t["product_name"], "temperature": temp, "run": run + 1, "score": score})
            if scores:
                summary[temp].append({"code": code, "product": t["product_name"], "scores": scores,
                                      "mean": statistics.mean(scores), "sd": statistics.pstdev(scores),
                                      "range": max(scores) - min(scores), "labelguard": float(t["true_score"])})
            print(f"{code} T={temp}: {scores}  LabelGuard={t['true_score']}", flush=True)

    (HERE / "results").mkdir(exist_ok=True)
    with open(HERE / "results" / "chat_baseline.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["product", "temperature", "run", "score"])
        w.writeheader()
        w.writerows(rows)

    md = ["# Plain-LLM scoring vs LabelGuard", "", f"Model: {config.GEMINI_MODEL} | runs per product: {args.runs}", "",
          "| Method | Mean SD across runs | Mean range (max-min) | Products with identical scores every run | Pearson r with LabelGuard (mean score) |",
          "|---|---|---|---|---|"]
    for temp, label in ((1.0, "Plain LLM, temperature 1.0 (chat default)"), (0.0, "Plain LLM, temperature 0")):
        s = summary[temp]
        if not s:
            continue
        md.append(f"| {label} | {statistics.mean(x['sd'] for x in s):.1f} | {statistics.mean(x['range'] for x in s):.1f} | "
                  f"{sum(1 for x in s if x['sd'] == 0)}/{len(s)} | {pearson([x['mean'] for x in s], [x['labelguard'] for x in s]):.2f} |")
    md.append(f"| LabelGuard (deterministic rules) | 0.0 | 0.0 | {len(summary[1.0])}/{len(summary[1.0])} | 1.00 |")
    md += ["", "## Per product", "", "| Product | LabelGuard | LLM T=1.0 scores | SD | LLM T=0 scores | SD |", "|---|---|---|---|---|---|"]
    by0 = {x["code"]: x for x in summary[0.0]}
    for x in summary[1.0]:
        z = by0.get(x["code"])
        md.append(f"| {x['product']} | {x['labelguard']:.0f} | {x['scores']} | {x['sd']:.1f} | {z['scores'] if z else '-'} | {z['sd'] if z else 0:.1f} |")
    (HERE / "results" / "chat_baseline.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
