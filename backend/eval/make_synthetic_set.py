"""
Builds a reproducible evaluation set with KNOWN ground truth.

Takes 12 products from data/indian_products_fallback.csv, renders each as a label image
(ingredient list + nutrition table, varied font sizes and layouts) into eval/images/, and writes
eval/ground_truth/labels.csv.

Ground truth:
  * ingredients, nutrition values  -> exactly what is printed on the image
  * hidden_sugars, allergens       -> the rules engine applied to the TRUE ingredient list
    (so the evaluation isolates the perception stage: does the extracted text lead to the same flags?)
  * true_score                     -> the deterministic score computed from the true values

Run from /backend:  python eval/make_synthetic_set.py
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from rules.engine import analyze_product  # noqa: E402
from rules.text import split_ingredients  # noqa: E402
from schemas import Extraction  # noqa: E402

CODES = ["FB-001", "FB-004", "FB-011", "FB-020", "FB-031", "FB-035", "FB-040", "FB-050", "FB-061", "FB-090",
         "FB-110", "FB-120"]
FIELDS = [("energy_kcal", "Energy (kcal)"), ("protein_g", "Protein (g)"), ("sugar_g", "Total Sugars (g)"),
          ("fat_g", "Total Fat (g)"), ("sat_fat_g", "Saturated Fat (g)"), ("fiber_g", "Dietary Fibre (g)"),
          ("sodium_mg", "Sodium (mg)")]
LIQUID = {"soft_drinks", "juices", "dairy_drinks"}


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in text.split(" "):
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def num(v):
    return "" if v in (None, "") else (str(int(float(v))) if float(v) == int(float(v)) else str(float(v)))


def render(row: dict, rng: random.Random) -> Image.Image:
    size = rng.choice([22, 24, 26])
    bg = rng.choice([(255, 255, 255), (252, 250, 243), (246, 249, 252)])
    img = Image.new("RGB", (1000, 1400), bg)
    d = ImageDraw.Draw(img)
    y = 40
    d.text((40, y), f"{row['brand']} {row['product_name']}".upper(), font=font(36, True), fill=(20, 20, 20))
    y += 70
    ing = "INGREDIENTS: " + ", ".join(i.strip() for i in row["ingredients"].split(";")) + "."
    for line in wrap(d, ing, font(size), 920):
        d.text((40, y), line, font=font(size), fill=(20, 20, 20))
        y += int(size * 1.45)
    y += 25
    unit = "100 ml" if row["category"] in LIQUID else "100 g"
    d.text((40, y), f"NUTRITION INFORMATION (per {unit})", font=font(28, True), fill=(20, 20, 20))
    y += 52
    d.rectangle((40, y - 8, 960, y - 8 + 46 * len(FIELDS) + 12), outline=(20, 20, 20), width=2)
    for key, label in FIELDS:
        d.text((60, y), label, font=font(26), fill=(20, 20, 20))
        d.text((640, y), num(row[key]), font=font(26), fill=(20, 20, 20))
        y += 46
    img = img.crop((0, 0, 1000, y + 40))
    return img


def main():
    rows = {r["code"]: r for r in csv.DictReader(open(HERE.parent / "data" / "indian_products_fallback.csv", encoding="utf-8"))}
    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "ground_truth").mkdir(exist_ok=True)
    rng = random.Random(7)
    out = []
    for code in CODES:
        r = rows[code]
        img = render(r, rng)
        fname = f"{code}.jpg"
        img.save(HERE / "images" / fname, quality=92)
        # Ground truth = the top-level ingredients exactly as PRINTED on the image (groups such as
        # "raising agents (INS 503, INS 500)" stay one item, because the label prints them as one).
        printed = ", ".join(i.strip() for i in r["ingredients"].split(";"))
        true_items = split_ingredients(printed)
        ex = Extraction(
            product_name=r["product_name"], brand=r["brand"], category=r["category"],
            ingredients=true_items,
            nutrition_per_100g={k: (float(r[k]) if r[k] != "" else None) for k, _ in FIELDS})
        pa = analyze_product(ex)
        out.append({
            "image_file": fname, "product_name": f"{r['brand']} {r['product_name']}", "category": r["category"],
            "ingredients": ";".join(true_items),
            "hidden_sugars": ";".join(h["alias"] for h in pa["hidden_sugars"]),
            "allergens": ";".join(a["key"] for a in pa["allergens"] if a["source"] == "ingredients"),
            "claims": "",
            **{k: r[k] for k, _ in FIELDS}, "true_score": pa["score"]["score"],
        })
    with open(HERE / "ground_truth" / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"Wrote {len(out)} images to eval/images and eval/ground_truth/labels.csv")
    for o in out:
        print(f"  {o['image_file']}  {o['product_name'][:34]:34s} score={o['true_score']:>3}  sugars={o['hidden_sugars'].count(';') + 1 if o['hidden_sugars'] else 0}  allergens={o['allergens'] or '-'}")


if __name__ == "__main__":
    main()
