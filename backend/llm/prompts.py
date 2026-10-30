"""
ALL Gemini prompts live in this file.

LabelGuard makes exactly three kinds of LLM call:
  1. PROFILE_PARSE  - once per profile edit (free text -> household JSON)
  2. EXTRACTION     - once per NEW label image (vision -> label JSON); cached by image hash
  3. EXPLANATION    - short 2-3 line personalised summary; cached per scan/member/language

Everything else (flags, score, claims, alternatives, tracking) is deterministic Python.
All calls use temperature 0-0.2 and response_mime_type="application/json".
"""
import json

from config import CATEGORIES
from schemas import CONDITIONS, DIET_RULES

# ---------------------------------------------------------------------------
# 1. PROFILE PARSING
# Turns "Pre-diabetic, allergic to cashews, Jain, my son is lactose intolerant"
# into structured members. We give the model closed vocabularies so its output
# maps cleanly onto the rules engine; Pydantic validation fills any gaps.
# ---------------------------------------------------------------------------
PROFILE_PARSE_PROMPT = """You convert a free-text description of a household's food needs into JSON.

Return ONLY a JSON object with this exact shape:
{{
  "members": [
    {{
      "name": "string (use the person's name if given, else 'Me' for the writer, or the relation e.g. 'Son')",
      "relation": "self | spouse | son | daughter | father | mother | grandfather | grandmother | sibling | other",
      "age": integer or null,
      "allergens": ["lowercase allergen words, e.g. cashew, peanut, milk, gluten, sesame, mustard"],
      "diet_rules": ["only from: {diets}"],
      "conditions": ["only from: {conditions}"],
      "limits": {{"sugar_g_per_day": number or null, "sodium_mg_per_day": number or null, "sat_fat_g_per_day": number or null}},
      "avoid_ingredients": ["other ingredients they want to avoid, e.g. palm oil, maida, msg"],
      "notes": "short string, anything that did not fit"
    }}
  ]
}}

Rules:
- The writer is the first member ("Me", relation "self") unless the text is clearly only about others.
- Create one member per person mentioned (e.g. "my son" -> a member named "Son", relation "son").
- An intolerance (e.g. lactose intolerant) is a CONDITION, not an allergen.
- "Cutting sodium/salt" -> sodium_mg_per_day 1500. "Cutting sugar" -> sugar_g_per_day 20.
  Pre-diabetic or diabetic -> sugar_g_per_day 20 unless a number is given. Otherwise use null.
- Jain implies vegetarian rules too; just put "jain". "No onion garlic" -> "jain".
- Never invent facts that are not in the text. Use [] or null when unknown.

Text:
\"\"\"{text}\"\"\"
"""


def profile_parse_prompt(text: str) -> str:
    return PROFILE_PARSE_PROMPT.format(text=text.strip()[:2000], diets=", ".join(DIET_RULES),
                                       conditions=", ".join(CONDITIONS))


# ---------------------------------------------------------------------------
# 2. LABEL EXTRACTION (vision)
# Pure perception: read what is printed. No judgement, no health advice.
# Key safety rules: null for anything unreadable, never guess, and a fixed
# salt -> sodium conversion so numbers are comparable.
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You read photos of packaged-food labels (often Indian products) and transcribe them into JSON.
You may receive SEVERAL photos of the SAME pack (front, back, side panels). Combine them into ONE record.

Return ONLY a JSON object with exactly these keys:
{{
  "product_name": string or null,
  "brand": string or null,
  "category": one of [{categories}],
  "ingredients": [list of ingredient strings in the PRINTED ORDER; keep sub-ingredients and INS/E codes inside brackets exactly as printed, e.g. "Emulsifiers (INS 322, 471)"],
  "nutrition_per_100g": {{"energy_kcal": n, "sugar_g": n, "added_sugar_g": n, "sodium_mg": n, "fat_g": n, "sat_fat_g": n, "trans_fat_g": n, "carbs_g": n, "protein_g": n, "fiber_g": n}},
  "serving_size": string or null (as printed, e.g. "3 biscuits (20 g)"),
  "serving_size_g": number or null,
  "nutrition_per_serving": same keys as nutrition_per_100g,
  "claims": [front-of-pack or marketing claims as printed, e.g. "no added sugar", "high protein", "healthy", "baked not fried"],
  "may_contain": [allergens from "may contain" / "manufactured in a facility that also processes" statements],
  "front_highlights": [foods/ingredients the FRONT of the pack features in pictures or big words, e.g. "mango", "almonds", "honey", "chocolate"],
  "front_messages": [impressions the front gives through words or imagery, e.g. "for kids", "natural", "real fruit", "homemade", "fitness", "energy"],
  "barcode": digits as string or null,
  "confidence": number 0-1 (how clearly you could read the label),
  "unreadable_fields": [names of fields you could not read, e.g. "ingredients", "sodium_mg"]
}}

Strict rules:
- Use null for any value you cannot read clearly. NEVER guess or estimate a number.
- Values are numbers only (no units). If the table is per 100 ml, put it in nutrition_per_100g.
- If only SALT is printed, convert: sodium_mg = salt_g * 400. If sodium is printed in g, multiply by 1000.
- Energy in kJ only: energy_kcal = kJ / 4.184.
- "Total sugars" -> sugar_g. "Added sugars" -> added_sugar_g. "Dietary fibre" -> fiber_g.
- Do not add ingredients that are not printed. Do not translate brand names.
- front_highlights / front_messages describe ONLY the front panel (pictures, cartoons, big words). If no front panel is visible, use [].
- If the image is not a food label, return all nulls/empty lists with confidence 0.
"""


def extraction_prompt() -> str:
    return EXTRACTION_PROMPT.format(categories=", ".join(CATEGORIES))


# ---------------------------------------------------------------------------
# 3. PERSONALISED EXPLANATION (short)
# The verdicts are already decided by the rules engine. The LLM only rewords
# them for this person/family in the chosen language and reading level.
# It must not change verdicts, invent numbers or give medical advice.
# ---------------------------------------------------------------------------
LANG_NAMES = {"en": "English", "hi": "Hindi (Devanagari script)", "ta": "Tamil (Tamil script)"}

EXPLAIN_PROMPT = """You explain a food-label analysis to an Indian family in {language}.
{style}

Facts decided by our rules engine (do NOT change verdicts or numbers, do NOT add new facts):
{facts}

Write 2-3 short sentences (max 60 words) saying what this product means for {audience}.
- Mention the most important reason first, using the evidence given.
- For anything marked "source unclear", say the source is unclear and to check with the brand. Do not guess.
- Do not give medical advice or diagnose. No greetings, no markdown.

Return ONLY JSON: {{"explanation": "..."}}
"""

# ---------------------------------------------------------------------------
# 4. (OPTIONAL EXTRA) ASK ABOUT THIS PRODUCT
# Only runs when the user types a question. Answers strictly from the rule
# results; it cannot invent nutrients or change verdicts. Cached per question.
# ---------------------------------------------------------------------------
ASK_PROMPT = """You answer a family's question about ONE packaged food, in {language}.
Use ONLY these facts from our label reader and rules engine (do not add facts, do not change verdicts):
{facts}

Question: \"\"\"{question}\"\"\"

Rules:
- Max 70 words, plain language, no markdown, no greetings.
- If the facts don't contain the answer, say it isn't on the label / not something we checked.
- For "source unclear" items, say to check with the brand.
- Never diagnose or give medical advice; for medical decisions suggest asking a doctor.

Return ONLY JSON: {{"answer": "..."}}
"""


def ask_prompt(facts: dict, question: str, language: str) -> str:
    return ASK_PROMPT.format(language=LANG_NAMES.get(language, "English"),
                             facts=json.dumps(facts, ensure_ascii=False, separators=(",", ":")),
                             question=question.strip()[:300])


ELI12_STYLE ="Use very simple words a 12-year-old understands. Short sentences. One relatable comparison is fine."
NORMAL_STYLE = "Be clear and direct, like a helpful dietitian friend."


def explain_prompt(facts: dict, language: str, eli12: bool, audience: str) -> str:
    return EXPLAIN_PROMPT.format(
        language=LANG_NAMES.get(language, "English"),
        style=ELI12_STYLE if eli12 else NORMAL_STYLE,
        facts=json.dumps(facts, ensure_ascii=False, separators=(",", ":")),
        audience=audience,
    )


# ---------------------------------------------------------------------------
# 5. (OPTIONAL EXTRA) WEEKLY FAMILY REPORT
# On demand. Every number is computed in Python (tracker, rules, alternatives);
# the LLM only turns those facts into a short, friendly write-up. Cached.
# ---------------------------------------------------------------------------
REPORT_PROMPT = """You write a short weekly food report for an Indian family, in {language}.
Use ONLY these facts (computed by our app; do not invent numbers, products or medical facts):
{facts}

Return ONLY JSON:
{{"headline": "one upbeat but honest line (max 12 words)",
  "summary": "3-4 sentences on the week: what went well, what to watch",
  "members": [{{"name": "...", "note": "1-2 sentences for this person, using their budget % and items"}}],
  "tips": ["3 practical tips for next week, each max 20 words, preferring the swaps listed in the facts"]}}

Rules: plain language, no markdown, no diagnosis or medical advice, mention a swap by product name if one is listed.
If almost nothing was logged, say so kindly and encourage logging snacks.
"""


def report_prompt(facts: dict, language: str) -> str:
    return REPORT_PROMPT.format(language=LANG_NAMES.get(language, "English"),
                                facts=json.dumps(facts, ensure_ascii=False, separators=(",", ":")))
