"""
Label evaluation harness (for the viva).

Usage (from /backend, with GEMINI_API_KEY set):
    python eval/run_eval.py                       # all images, 3 runs, + degraded variants
    python eval/run_eval.py --limit 5 --runs 2    # quicker / cheaper
    python eval/run_eval.py --no-degrade

Inputs
  eval/images/                  your label photos
  eval/ground_truth/labels.csv  one row per image (see labels_template.csv):
      image_file, product_name, ingredients (; separated), hidden_sugars (; separated),
      allergens (; separated allergen keys e.g. milk;gluten;cashew), claims (claim=verdict; ...)

Outputs
  eval/results/eval_results.csv   one row per image x condition x run
  eval/results/summary.md         markdown tables to paste into slides

Token cost: images x (runs + 3 degraded) vision calls. 25 images x 6 = 150 calls.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics
import sys
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from PIL import Image, ImageEnhance, ImageFilter  # noqa: E402

from llm.gemini_client import LLMError, prepare_image  # noqa: E402
from llm.tasks import extract_label  # noqa: E402
from rules.engine import analyze_product  # noqa: E402
from rules.text import norm  # noqa: E402

RESULTS = HERE / "results"


def split(s: str) -> list[str]:
    return [x.strip().lower() for x in (s or "").split(";") if x.strip()]


def clean(s: str) -> str:
    """Ingredient name without percentages / brackets for fuzzy matching."""
    s = norm(s)
    s = s.split("(")[0].split("[")[0]
    return "".join(ch for ch in s if ch.isalnum() or ch == " ").strip()


def fuzzy_prf(pred: list[str], truth: list[str], thresh: float = 0.85) -> tuple[float, float, float]:
    pred_c, truth_c = [clean(p) for p in pred], [clean(t) for t in truth]
    used, tp = set(), 0
    for p in pred_c:
        for j, t in enumerate(truth_c):
            if j not in used and (p == t or SequenceMatcher(None, p, t).ratio() >= thresh):
                used.add(j)
                tp += 1
                break
    precision = tp / len(pred_c) if pred_c else (1.0 if not truth_c else 0.0)
    recall = tp / len(truth_c) if truth_c else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def set_prf(pred: set, truth: set) -> tuple[int, int, int]:
    return len(pred & truth), len(pred - truth), len(truth - pred)  # tp, fp, fn


def degrade(raw: bytes, kind: str) -> bytes:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if kind == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=2.5))
    elif kind == "rotate":
        img = img.rotate(15, expand=True, fillcolor=(255, 255, 255))
    elif kind == "low_light":
        img = ImageEnhance.Brightness(img).enhance(0.35)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def evaluate_once(raw: bytes, truth: dict) -> dict:
    ex = extract_label(prepare_image(raw))  # direct call: bypasses the cache on purpose
    pa = analyze_product(ex)
    pa_again = analyze_product(ex)  # rules determinism check on identical input
    ip, ir, if1 = fuzzy_prf(ex.ingredients, split(truth["ingredients"]))
    sugars_pred = {h["alias"] for h in pa["hidden_sugars"]}
    allergens_pred = {a["key"] for a in pa["allergens"] if a["source"] == "ingredients"}
    claims_truth = dict(c.split("=", 1) for c in split(truth.get("claims", "")) if "=" in c)
    claims_pred = {c["claim"].lower(): c["verdict"] for c in pa["claims"]}
    claim_hits = sum(1 for k, v in claims_truth.items() if claims_pred.get(k) == v.strip())
    # Nutrition accuracy: a printed value counts as correct if within 2% (or 0.1 absolute) of the truth.
    nut_total = nut_ok = 0
    for field in ("energy_kcal", "sugar_g", "sodium_mg", "fat_g", "sat_fat_g", "protein_g", "fiber_g"):
        raw_truth = (truth.get(field) or "").strip()
        if raw_truth == "":
            continue
        nut_total += 1
        got = getattr(ex.nutrition_per_100g, field)
        t = float(raw_truth)
        if got is not None and abs(got - t) <= max(0.1, 0.02 * abs(t)):
            nut_ok += 1
    truth_score = float(truth["true_score"]) if (truth.get("true_score") or "").strip() else None
    return {
        "ing_precision": ip, "ing_recall": ir, "ing_f1": if1,
        "sugar": set_prf(sugars_pred, set(split(truth["hidden_sugars"]))),
        "allergen": set_prf(allergens_pred, set(split(truth["allergens"]))),
        "claims_correct": claim_hits, "claims_total": len(claims_truth),
        "nut_ok": nut_ok, "nut_total": nut_total,
        "score_error": abs(pa["score"]["score"] - truth_score) if truth_score is not None else None,
        "score": pa["score"]["score"], "rules_deterministic": pa == pa_again,
        "ingredients": ex.ingredients, "nutrition": ex.nutrition_per_100g.model_dump(),
        "confidence": ex.confidence,
    }


def prf_from_counts(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return p, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=str(HERE / "images"))
    ap.add_argument("--truth", default=str(HERE / "ground_truth" / "labels.csv"))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-degrade", action="store_true")
    args = ap.parse_args()

    with open(args.truth, newline="", encoding="utf-8") as f:
        truths = list(csv.DictReader(f))
    if args.limit:
        truths = truths[: args.limit]
    RESULTS.mkdir(exist_ok=True)
    conditions = ["clean"] + ([] if args.no_degrade else ["blur", "rotate", "low_light"])

    rows, per_cond, consistency = [], {c: [] for c in conditions}, []
    for t in truths:
        path = Path(args.images) / t["image_file"]
        if not path.exists():
            print(f"skip {t['image_file']}: image not found")
            continue
        raw = path.read_bytes()
        print(f"{t['image_file']} ...", flush=True)
        clean_runs = []
        for cond in conditions:
            n_runs = args.runs if cond == "clean" else 1
            for run in range(n_runs):
                try:
                    r = evaluate_once(raw if cond == "clean" else degrade(raw, cond), t)
                except LLMError as exc:
                    print(f"  {cond} run {run}: LLM error {exc}")
                    continue
                per_cond[cond].append(r)
                if cond == "clean":
                    clean_runs.append(r)
                rows.append({"image": t["image_file"], "condition": cond, "run": run + 1,
                             "ing_f1": round(r["ing_f1"], 3), "ing_precision": round(r["ing_precision"], 3),
                             "ing_recall": round(r["ing_recall"], 3), "sugar_tp_fp_fn": r["sugar"],
                             "allergen_tp_fp_fn": r["allergen"],
                             "claims": f"{r['claims_correct']}/{r['claims_total']}", "score": r["score"],
                             "rules_deterministic": r["rules_deterministic"], "confidence": r["confidence"]})
        if len(clean_runs) >= 2:
            scores = [r["score"] for r in clean_runs]
            sets = [set(map(clean, r["ingredients"])) for r in clean_runs]
            jacc = [len(a & b) / len(a | b) if a | b else 1.0 for a in sets for b in sets if a is not b]
            fields_diff = sum(1 for k in clean_runs[0]["nutrition"]
                              if len({r["nutrition"][k] for r in clean_runs}) > 1)
            consistency.append({"image": t["image_file"], "scores": scores,
                                "score_stdev": round(statistics.pstdev(scores), 2),
                                "ingredient_jaccard": round(statistics.mean(jacc), 3) if jacc else 1.0,
                                "nutrition_fields_varying": fields_diff,
                                "rules_identical": all(r["rules_deterministic"] for r in clean_runs)})

    with open(RESULTS / "eval_results.csv", "w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    md = ["# LabelGuard evaluation summary", "", f"Images: {len(truths)} | clean runs per image: {args.runs}", "",
          "| Condition | Ingredient F1 | Hidden-sugar P / R | Allergen P / R | Nutrition accuracy | Mean score error | n |",
          "|---|---|---|---|---|---|---|"]
    for cond, rs in per_cond.items():
        if not rs:
            continue
        s = [sum(x) for x in zip(*[r["sugar"] for r in rs])]
        a = [sum(x) for x in zip(*[r["allergen"] for r in rs])]
        sp, sr = prf_from_counts(*s)
        apr, ar = prf_from_counts(*a)
        ct = sum(r["claims_total"] for r in rs)
        cc = sum(r["claims_correct"] for r in rs)
        nt = sum(r["nut_total"] for r in rs)
        nk = sum(r["nut_ok"] for r in rs)
        errs = [r["score_error"] for r in rs if r["score_error"] is not None]
        md.append(f"| {cond} | {statistics.mean(r['ing_f1'] for r in rs):.2f} | {sp:.2f} / {sr:.2f} | "
                  f"{apr:.2f} / {ar:.2f} | {(nk / nt if nt else 0):.0%} | "
                  f"{(statistics.mean(errs) if errs else float('nan')):.1f} | {len(rs)} |")
    if consistency:
        md += ["", "## Consistency over repeated runs (same photo)", "",
               "| Metric | Value |", "|---|---|",
               f"| Rules output identical for identical extraction | {sum(c['rules_identical'] for c in consistency)}/{len(consistency)} images |",
               f"| Mean score std-dev across runs (from extraction variance) | {statistics.mean(c['score_stdev'] for c in consistency):.2f} |",
               f"| Images with identical score every run | {sum(1 for c in consistency if c['score_stdev'] == 0)}/{len(consistency)} |",
               f"| Mean ingredient-set Jaccard between runs | {statistics.mean(c['ingredient_jaccard'] for c in consistency):.3f} |",
               f"| Mean nutrition fields that varied | {statistics.mean(c['nutrition_fields_varying'] for c in consistency):.2f} |",
               "", "With the image-hash cache on (normal app use), a repeat scan returns the stored extraction, so the score is identical by construction."]
    (RESULTS / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nWrote {RESULTS / 'eval_results.csv'} and {RESULTS / 'summary.md'}")


if __name__ == "__main__":
    main()
