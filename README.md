# LabelGuard

A personalised food-label scanner for Indian households. Photograph a packaged-food label and LabelGuard reads it, checks it against your family's health profile, gives a repeatable score, suggests real better alternatives and tracks weekly sugar and sodium.

> **Design principle:** The LLM handles perception and interpretation. Deterministic Python rules and real databases handle anything that must be consistent, verifiable or cheap.

*Informational only, not medical advice.*

---

## 1. Architecture

```
 Phone / laptop browser (React + Vite + Tailwind + Recharts)
        |  /api/*  (Vite dev proxy; the Gemini key never reaches the browser)
        v
 FastAPI (backend/main.py)
  |- routers/profile ----> llm/tasks.parse_profile ---- Gemini call #1 (once per profile edit, cached)
  |                                 \__ fallback: rules/profile_keywords.py
  |- routers/scan -------> pipeline.py
  |                         1. SQLite cache by image hash / barcode  -> 0 tokens
  |                         2. barcode (optional pyzbar) -> Open Food Facts product -> 0 tokens
  |                         3. Gemini vision call #2 (resize <=1024px, temp 0, JSON only)
  |                         4. rules/engine.py  (pure Python, 0 tokens)
  |                              - hidden sugars, INS additives, allergens, Jain/veg/vegan/halal
  |                              - per-member SAFE/WARN/AVOID + evidence
  |                              - claims.py (FSSAI thresholds), scoring.py (0-100 formula)
  |- /scan/explain -------> Gemini call #3 (<=60 words, cached) | fallback: template (en/hi/ta)
  |- routers/alternatives -> alternatives/ranker.py (0 tokens)
  |                           Open Food Facts search + data/indian_products_fallback.csv
  |                           same scoring formula, allergy/diet filter, feedback re-ranking
  |- routers/compare, routers/tracker (0 tokens)
  v
 SQLite (backend/labelguard.db)
```

### SQLite schema (backend/db.py)

| Table | Purpose |
|---|---|
| `household` | single row: household profile JSON + original free text |
| `extraction_cache` | `img:<sha256>` / `bar:<barcode>` -> extraction JSON (repeat scans cost 0 tokens) |
| `scans` | every scan: extraction JSON, profile-independent score, source |
| `intake_logs` | "Log this": member, grams, sugar/sodium/sat-fat eaten |
| `alt_feedback` | thumbs up/down on alternatives + reason (re-ranks future suggestions) |
| `llm_cache` | cached profile parses and explanations |
| `off_cache` | Open Food Facts responses (7-day TTL) |
| `llm_calls` | every LLM call: purpose, tokens, latency (shown on the About page) |

Verdicts are **re-computed** from the stored extraction with the *current* profile every time a scan is opened, so editing the profile updates old scans for free.

---

## 2. Setup and run

Requirements: Python 3.11+, Node 18+. **On Windows, keep the project in a short path** (e.g. `C:\dev\labelguard`); very long paths break Pillow's DLL loading.

### Backend (terminal 1)

```bash
cd backend
python -m venv .venv
```
Windows: `.venv\Scripts\activate` | macOS/Linux: `source .venv/bin/activate`
```bash
pip install -r requirements.txt
```
```bash
cp .env.example .env
```
Edit `backend/.env` and set `GEMINI_API_KEY` (free key at https://aistudio.google.com). Then:
```bash
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. To use your **phone camera**, connect the phone to the same Wi-Fi and open `http://<laptop-ip>:5173` (Vite prints the Network URL). The "Take photo" button opens the rear camera.

**Without an API key** the app still works: demo labels, the rules engine, alternatives, tracker, compare, the keyword profile parser and template explanations. Only real photo scans need the key.

**Flaky Wi-Fi on demo day?** Set `OFF_ENABLED=0` in `.env` and alternatives come instantly from the local Indian products table.

---

## 3. Test the API before the UI (curl or /docs)

```bash
curl http://localhost:8000/api/health
```
```bash
curl -X POST http://localhost:8000/api/profile/parse -H "Content-Type: application/json" -d "{\"text\": \"Pre-diabetic, allergic to cashews, Jain, cutting sodium. My son Rohan is 9 and lactose intolerant.\"}"
```
Copy the `household` object from that response into a PUT (or use /docs):
```bash
curl -X PUT http://localhost:8000/api/profile -H "Content-Type: application/json" -d "{\"household\": {\"members\": [{\"name\": \"Me\", \"allergens\": [\"cashew\"], \"diet_rules\": [\"jain\"], \"conditions\": [\"prediabetes\"]}, {\"name\": \"Rohan\", \"relation\": \"son\", \"age\": 9, \"conditions\": [\"lactose_intolerance\"]}]}}"
```
```bash
curl -X POST http://localhost:8000/api/scan/demo/choco_cream_biscuit
```
```bash
curl -X POST http://localhost:8000/api/scan -F "file=@path/to/label.jpg"
```
```bash
curl -X POST http://localhost:8000/api/scan/explain -H "Content-Type: application/json" -d "{\"scan_id\": 1, \"language\": \"hi\", \"eli12\": true}"
```
```bash
curl http://localhost:8000/api/alternatives/1
```
```bash
curl -X POST http://localhost:8000/api/alternatives/feedback -H "Content-Type: application/json" -d "{\"scan_id\": 1, \"product_code\": \"FB-007\", \"vote\": -1, \"reason\": \"too_expensive\"}"
```
```bash
curl -X POST http://localhost:8000/api/log -H "Content-Type: application/json" -d "{\"scan_id\": 1, \"member\": \"Me\", \"servings\": 2}"
```
```bash
curl http://localhost:8000/api/tracker
```
```bash
curl -X POST http://localhost:8000/api/compare -H "Content-Type: application/json" -d "{\"scan_id_a\": 1, \"scan_id_b\": 2, \"member\": \"Me\"}"
```

All errors return `{"error": "...", "detail": "friendly message"}`.

---

## 4. Features (priority order)

| # | Feature | Where | LLM? |
|---|---|---|---|
| 1 | Household profile from free text, editable form, multiple members | Profile page | 1 call per edit (cached) |
| 2 | Label photo -> structured JSON (phone camera, or paste an image with Ctrl+V / "Paste image") | Scan page | 1 call per *new* photo |
| 3 | Per-member SAFE/WARN/AVOID with reason + evidence; hidden sugars; INS additive cards; Jain/veg/vegan/halal with "source unclear" | Scan result | none |
| 4 | Claim checker (FSSAI thresholds), per-serving vs per-100g trap detector | Scan result | none |
| 5 | Transparent 0-100 score with breakdown | Scan result + About | none |
| 6 | 2-3 line explanation in English/Hindi/Tamil + ELI12 | Scan result | 1 small call (cached), template fallback |
| 7 | Top-3 real alternatives + thumbs up/down re-ranking | Scan result + Alternatives | none |
| 8 | Log intake, weekly budgets per member, score trend, worst offenders | History & Tracker | none |
| 9 | Compare two products for a member | Compare | none |
| 10 | Evaluation harness | backend/eval | eval only |

Optional extras: barcode decoding (`pip install pyzbar`), the chat-consistency comparison script.

### More modules (all zero tokens unless noted)

| Module | What it does |
|---|---|
| **Barcode lookup** (Scan → Barcode tab) | Type the number under the barcode → Open Food Facts → full analysis. 0 tokens. Try 3017620422003 (Nutella). |
| **Multi-photo scan** | Paste up to 3 photos of one pack (front + ingredients + nutrition); read together in ONE AI call. |
| **Type it in** | Manual label entry when there's no photo or API key. |
| **Traffic-light label** | UK-style front-of-pack tiles (energy, fat, saturates, sugars, salt) with % of reference intake per serving. |
| **Listen** | Reads the summary aloud in English / Hindi / Tamil with the browser's speech engine. |
| **Share / list / delete** | WhatsApp share, copy summary, add to shopping list, delete scan. |
| **Ask about this product** | Optional 4th AI call: answers typed questions using only the label + rule results; cached; rules fallback. |
| **Swap impact** | Each alternative shows "swapping saves X g sugar a week", from logged intake or one serving a day. |
| **Product explorer** | Browse all Indian products with scores + family verdicts; filter by category / safe-only; sort by sugar, sodium, protein, price. |
| **Ingredient decoder** | Type E471, maltodextrin, kaju... → what it is + Safe/Caution/Avoid for each member (runs the real rules engine). |
| **Insights** | Most common hidden sugars and additives, average score per category, verdicts per member, misleading claims. |
| **Shopping list** | Save healthier picks, tick them off, send the list on WhatsApp. |
| **Allergy cards** | Printable card per member with Indian names of allergens (cashew = kaju), Jain avoid list, conditions. |
| **Compare 2-4 products** | Ranked with a winner and side-by-side nutrient bars. |
| **Tracker** | Day-by-day chart per member, delete mistaken logs. |
| **Reset demo data** | About page: clears scans/logs/list, keeps the profile. |
| **Weekly family report** | Optional AI call: every number (budgets, items eaten, claims caught, best swaps) is computed in Python; the AI only writes the headline, summary, per-member notes and 3 tips (English/Hindi/Tamil). Cached; template fallback. Print/PDF, WhatsApp, Listen. |
| **Front vs back of pack** | No extra AI call: the photo-reading call also notes what the FRONT pictures/promises (e.g. almonds, "natural", "for kids"); the rules engine checks each one against the ingredient list, percentages, additives and score ("almonds pictured, only 1%"). |



---

## 5. Evaluation (backend/eval)

1. Put 20-30 label photos in `backend/eval/images/`.
2. Copy `eval/ground_truth/labels_template.csv` to `eval/ground_truth/labels.csv` and add one row per photo (ingredients, hidden sugars and allergen keys `;`-separated; claims as `claim=verdict`, verdicts `ok|misleading|marketing|unknown`).
3. Run from `backend/`:

```bash
python eval/run_eval.py --runs 3
```
```bash
python eval/profile_parser_eval.py
```
Optional, after recording plain-chat scores in a CSV (format in the script docstring):
```bash
python eval/chat_consistency.py eval/ground_truth/chat_scores.csv
```

Outputs land in `backend/eval/results/` (`eval_results.csv`, `summary.md`, `profile_parser_summary.md`). They report ingredient F1, hidden-sugar and allergen precision/recall, claim accuracy, accuracy under blur / 15° rotation / low light, and consistency over 3 runs (rules output identical; extraction variance shown as score std-dev, ingredient Jaccard and varying nutrition fields). The keyword profile parser scores 87% field accuracy on the 10 sample profiles, which is the baseline Gemini should beat.

Cost: images x (runs + 3 degraded) vision calls, e.g. 25 x 6 = 150 calls. Use `--limit 5` for a dry run.

---

## 6. Three-minute demo script

1. **(0:00) Profile.** Profile -> "Use example" -> "Fill the form from this". *"I describe my family once in plain words. One AI call turns it into this form, which I can correct. It's saved and used for every scan."* Show the 3 members, then Save.
2. **(0:40) Scan.** Scan -> photograph a biscuit pack, or copy a label image and press Ctrl+V (or tap the **Choco Cream Biscuits** demo). *"One vision call reads the label. Everything after this is plain Python."* Point at: the red score, "Not suitable for Me: contains cashew", the Jain flag on the emulsifier marked *source unclear*, "Sugar appears under 4 names", and the **Claim check** ("healthy" and "made with whole wheat" both misleading; first ingredient is maida).
3. **(1:30) Consistency.** Scan the *same* photo again: "cached, 0 tokens", same score. Open "Show how this score was calculated". *"A plain chatbot can give a slightly different number on a re-ask (we measured 1.1 points on average, and 4 of 8 products changed) and it cannot show how it got there. This is a formula you can open and check."*
4. **(1:50) Explanation.** Switch the header to Hindi + ELI12. *"The only free text from the AI is this short summary, and it can't change the verdicts."*
5. **(2:10) Alternatives.** Scroll to Better alternatives. *"Real products from Open Food Facts plus a local Indian table, scored with the same formula and filtered for my cashew allergy."* Tap "Not for me -> Too expensive", then reload and show the re-ranking.
6. **(2:30) Tracker.** Tap "Log this" for Rohan with 2 servings of the mango drink demo -> History & Tracker: Rohan's sugar bar and the "% of weekly budget" message.
7. **(2:50) Compare.** Biscuits vs makhana for "Me": the winner and why. Close on the About page's AI-usage table: *"3 kinds of AI call, everything else deterministic."*

---

## 7. Known limitations

- Extraction quality depends on photo quality. Curved packs, glare and tiny fonts cause misses; the confidence and "unreadable fields" warnings flag this.
- Ingredient matching is keyword-based: unusual spellings or regional names not in the tables are missed, and some ambiguous items (E471, "natural flavours") can only be marked *source unclear*.
- Fallback product nutrition values are **approximate**, compiled for the demo, and must be checked against real packs. Open Food Facts coverage of Indian products is patchy, and its search endpoint was intermittently unavailable when this was built.
- The score is a transparent heuristic inspired by FSA traffic lights / FSSAI claim thresholds / NOVA, not a validated clinical index. Thresholds are per 100 g/ml and ignore portion context except in the serving check.
- The intake tracker only counts what you log from scans (packaged foods), not your whole diet.
- One household per install: no accounts, no auth (it's a demo).
- Hindi/Tamil fallback templates keep the reason text in English; full translation needs the LLM call.

---

## 8. Likely viva questions

**Why not just use ChatGPT?**
Four things a chat can't do reliably. (1) *Consistency and traceability:* in our test a plain LLM was close to repeatable but not exact (mean SD 1.1 points at temperature 1.0; 4 of 8 products changed between runs, 2 of 8 even at temperature 0), it scored on a very different scale from our formula (cola 5 vs 50, bread 35 vs 80) and could not show how a number was obtained; ours is a documented formula with zero variance, and repeat photos hit the cache. (2) *Memory:* the household profile is set once and applied to every scan for every member. (3) *Grounded alternatives:* chat invents products; ours come from Open Food Facts or a curated table, scored with the same formula. (4) *Tracking:* weekly budgets and history across scans. It's also cheaper: at most one vision call per new product, versus a long chat each time.

**Where is the AI?**
Three narrow places: understanding free-text profiles, reading the label photo (vision OCR plus structure), and a 2-3 line plain-language summary in the user's language. Perception and language are where LLMs excel; judgement that must be repeatable is in rules.

**Isn't a rules engine "not AI"?**
It's a deliberate hybrid. The LLM handles unstructured input; rules make the safety-critical decisions auditable. Every flag carries its evidence, so a user or examiner can check it, which an LLM's free-form answer can't offer.

**How do you stop the LLM hallucinating values?**
The prompt says to use null for anything unreadable and never guess; output is JSON-only at temperature 0; Pydantic validates and coerces it; the explanation call can't change verdicts; and low confidence or missing fields are shown as warnings.

**How is the score computed and why those weights?**
It's shown on the About page: start at 100, subtract capped penalties for sugar, sodium, saturated fat, energy density, additive concern and processing level, then add fibre and protein bonuses. Thresholds follow UK FSA traffic lights and FSSAI claim limits; drinks use stricter sugar scaling. It's a transparent heuristic, not a clinical index.

**How do you keep token cost low?**
Three call types only; image-hash and barcode caches; images resized to 1024 px; explanations capped at 60 words and cached; the profile is parsed once. Alternatives, tracking and compare use zero tokens. Token usage is logged per call and shown in the app.

**What if Gemini or Open Food Facts is down?**
The profile falls back to a keyword parser, explanations fall back to templates, and alternatives fall back to the local CSV. Errors return friendly JSON, and demo labels work with no network at all.

**How did you evaluate it?**
Against hand-labelled ground truth: ingredient F1, hidden-sugar and allergen precision/recall, claim accuracy, robustness to blur, rotation and low light, and repeat-run consistency, plus profile-parser field accuracy against a keyword baseline (see `eval/results/summary.md`).

**Why is E471 a "WARN" for vegetarians?**
Mono- and diglycerides can come from plant or animal fat and labels rarely say which. We mark it "source unclear, check with the brand" rather than guessing either way.

---

## 9. External details you must verify before the demo

| Item | Current value (Oct 2026) | Where to check | Where to change |
|---|---|---|---|
| Gemini model name | `gemini-3.8-flash` (stable). `gemini-3.6-flash` is the fallback | https://ai.google.dev/gemini-api/docs/models | `GEMINI_MODEL` in `.env` |
| Thinking setting | `thinking_level=low` (3.8 Flash supports low/medium/high). Thinking tokens count towards `max_output_tokens`. The client retries without it if the model rejects it | https://ai.google.dev/gemini-api/docs/thinking | `GEMINI_THINKING_LEVEL` in `.env` |
| google-genai SDK | 2.31.0, using `client.models.generate_content` + `GenerateContentConfig(response_mime_type="application/json")` | PyPI `google-genai` | `requirements.txt` |
| OFF product endpoint | `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json` (**confirmed working**) | https://openfoodfacts.github.io/openfoodfacts-server/api/ | `config.py` |
| OFF search endpoint | `GET /api/v2/search?categories_tags_en=...&countries_tags_en=india`. **During testing, searches returned "Page temporarily unavailable"** (with the country filter, and intermittently without). Try it the day before; if it fails, set `OFF_COUNTRY_PARAM=` (empty) or `OFF_ENABLED=0` | same docs | `config.py` / `.env` |
| OFF rate limits | 10 searches/min and 15 product reads/min per IP; we throttle to 1 per 6.5 s / 4.5 s and cache 7 days. Send a descriptive `OFF_USER_AGENT` | same docs | `config.py` |
| OFF category tags | mapping in `config.CATEGORIES` (e.g. `biscuits`, `instant-noodles`) | browse world.openfoodfacts.org/categories | `config.py` |

---

## Experiments used in the paper (backend/eval)

```bash
python eval/make_synthetic_set.py     # 12 labelled test labels with known ground truth
python eval/run_eval.py --runs 3      # extraction accuracy: clean, blur, rotation, low light
python eval/chat_baseline.py --runs 5 # plain-LLM scoring vs LabelGuard
python eval/profile_parser_eval.py    # keyword fall-back vs Gemini profile parser
python ../docs/collect_results.py && python ../docs/make_paper.py   # builds docs/LabelGuard_Research_Paper.pdf
```
Measured (Oct 2026, gemini-3.6-flash): clean-image ingredient F1 1.00, hidden-sugar and allergen precision/recall 1.00, nutrition accuracy 100% (96% under 15 degree rotation); plain LLM score SD 1.1 points (T=1.0) and 0.6 (T=0) vs 0 for LabelGuard; profile parser 100% (Gemini) vs 87% (keyword fall-back).
