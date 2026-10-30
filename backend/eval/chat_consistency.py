"""
OPTIONAL: compare score consistency of LabelGuard vs a plain chatbot.

1. Ask ChatGPT/Gemini chat "Rate this food label's healthiness 0-100" with the same photo
   3+ times (new chat each time). Record the numbers in a CSV:
       label_id,run,chat_score
       bourbon,1,35
       bourbon,2,50
2. Run (from /backend):  python eval/chat_consistency.py eval/ground_truth/chat_scores.csv
   LabelGuard's rules score for a fixed extraction has std-dev 0 by construction
   (see run_eval.py consistency table).
"""
import csv
import statistics
import sys
from collections import defaultdict


def main(path: str):
    by_label = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_label[row["label_id"]].append(float(row["chat_score"]))
    print("| Label | Chat scores | Chat std-dev | Chat range | LabelGuard std-dev (fixed extraction) |")
    print("|---|---|---|---|---|")
    sds = []
    for label, scores in by_label.items():
        sd = statistics.pstdev(scores)
        sds.append(sd)
        print(f"| {label} | {', '.join(f'{s:g}' for s in scores)} | {sd:.1f} | {max(scores) - min(scores):g} | 0.0 |")
    if sds:
        print(f"\nMean chat std-dev: {statistics.mean(sds):.1f} points. LabelGuard: 0.0 (deterministic rules).")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval/ground_truth/chat_scores.csv")
