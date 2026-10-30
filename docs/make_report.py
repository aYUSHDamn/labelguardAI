"""
Builds docs/LabelGuard_Project_Report.pdf (A4, <= 15 pages).

    python docs/make_report.py

Edit the DETAILS block below (name, register number, course, guide) and re-run.
Needs: pip install reportlab pillow
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image as PILImage
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

# ----------------------------------------------------------------- DETAILS
DETAILS = {
    "title": "LabelGuard",
    "subtitle": "A Personalised Food-Label Scanner for Indian Households using LLM Vision and a Deterministic Rules Engine",
    "school": "School of Computer Science and Engineering",
    "course": "BCSE306L - Artificial Intelligence",
    "review": "Course Project Review - 3",
    "semester": "Fall Semester 2026-27",
    "slot": "C2+TC2",
    "guide": "Dr. D. Anuradha",
    "team": [
        ("Harsh Kulkarni", "24BCT0137"),
        ("B S Srivallabha", "24BCE0457"),
        ("Ayush Konar", "24BDS0107"),
        ("Pratham Paudel", "24BCE2940"),
    ],
    "date": "November 2026",
}

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
OUT = HERE / "LabelGuard_Project_Report.pdf"

# ----------------------------------------------------------------- fonts
FONT_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
try:
    pdfmetrics.registerFont(TTFont("TNR", str(FONT_DIR / "times.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-B", str(FONT_DIR / "timesbd.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-I", str(FONT_DIR / "timesi.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(FONT_DIR / "consola.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-B")
    BODY, BOLD, ITAL, MONO = "TNR", "TNR-B", "TNR-I", "Mono"
except Exception:  # fallback to built-in fonts
    BODY, BOLD, ITAL, MONO = "Times-Roman", "Times-Bold", "Times-Italic", "Courier"

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#4b5563")
BRAND = colors.HexColor("#4f46e5")
SOFT = colors.HexColor("#eef2ff")
LINE = colors.HexColor("#d1d5db")

ss = getSampleStyleSheet()
S = {
    "body": ParagraphStyle("body", parent=ss["Normal"], fontName=BODY, fontSize=11, leading=15, alignment=TA_JUSTIFY,
                           textColor=INK, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=15, leading=19, spaceBefore=6, spaceAfter=8, textColor=INK),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=12.5, leading=16, spaceBefore=8, spaceAfter=4, textColor=INK),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=11, leading=14, spaceBefore=5, spaceAfter=2, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName=BODY, fontSize=11, leading=14.5, leftIndent=14, bulletIndent=4,
                             spaceAfter=2, textColor=INK, alignment=TA_JUSTIFY),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=9.5, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=BOLD, fontSize=9.5, leading=12, textColor=INK),
    "caption": ParagraphStyle("caption", fontName=ITAL, fontSize=9.5, leading=12, alignment=TA_CENTER,
                              textColor=MUTED, spaceBefore=3, spaceAfter=10),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=7.8, leading=9.6, textColor=INK, backColor=colors.HexColor("#f6f7f9"),
                           borderColor=LINE, borderWidth=0.5, borderPadding=6, leftIndent=6, rightIndent=6,
                           spaceBefore=4, spaceAfter=10),
    "ref": ParagraphStyle("ref", fontName=BODY, fontSize=10, leading=13, leftIndent=18, firstLineIndent=-18, spaceAfter=4),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="\u2022") for t in items]


def table(rows, widths, header=True, font_size=None):
    data = [[c if not isinstance(c, str) else Paragraph(c, S["cellb"] if (header and i == 0) else S["cell"])
             for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(style))
    return t


def figure(name, caption, width_cm=15.5, crop_h=None):
    path = SHOTS / name
    img = PILImage.open(path)
    if crop_h and img.size[1] > crop_h:
        cropped = SHOTS / f"_{name}"
        img.crop((0, 0, img.size[0], crop_h)).save(cropped)
        path, img = cropped, PILImage.open(cropped)
    w, h = img.size
    width = width_cm * cm
    height = width * h / w
    max_h = 12.5 * cm
    if height > max_h:
        width, height = width * max_h / height, max_h
    return KeepTogether([Image(str(path), width=width, height=height), P(caption, "caption")])


def code(text):
    return Preformatted(text.strip("\n"), S["code"])


def code_block(title, text):
    return KeepTogether([P(title, "h3"), code(text)])


# ----------------------------------------------------------- architecture diagram
def architecture():
    W, H = 16.5 * cm, 10.6 * cm
    d = Drawing(W, H)

    def box(x, y, w, h, title, lines=(), fill=colors.white, stroke=BRAND):
        d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=stroke, strokeWidth=1))
        d.add(String(x + w / 2, y + h - 13, title, fontName=BOLD, fontSize=9, textAnchor="middle", fillColor=INK))
        for i, ln in enumerate(lines):
            d.add(String(x + w / 2, y + h - 25 - i * 10, ln, fontName=BODY, fontSize=7.6, textAnchor="middle", fillColor=MUTED))

    def arrow(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=MUTED, strokeWidth=0.9))
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        a, s = 0.45, 5
        d.add(Polygon([x2, y2, x2 - s * math.cos(ang - a), y2 - s * math.sin(ang - a),
                       x2 - s * math.cos(ang + a), y2 - s * math.sin(ang + a)], fillColor=MUTED, strokeColor=MUTED))

    cm_ = cm
    # Layer 1: client
    box(0.3 * cm_, 8.6 * cm_, 15.9 * cm_, 1.7 * cm_, "Client: React 18 + Vite + Tailwind single-page app",
        ["Scan (paste / camera / barcode / manual)  |  Results  |  Explorer  |  Tracker  |  Weekly report  |  Profile"],
        fill=SOFT)
    arrow(8.25 * cm_, 8.6 * cm_, 8.25 * cm_, 7.95 * cm_)
    d.add(String(8.45 * cm_, 8.15 * cm_, "REST / JSON  (/api/*)", fontName=ITAL, fontSize=7.5, fillColor=MUTED))
    # Layer 2: API
    box(0.3 * cm_, 6.5 * cm_, 15.9 * cm_, 1.45 * cm_, "FastAPI backend (Python 3.11+, Pydantic v2)",
        ["routers: profile, scan, alternatives, compare, tracker/report, extras  |  consistent {error, detail} JSON"])
    # Layer 3: engines
    xs = [0.3, 4.35, 8.4, 12.45]
    titles = [("LLM layer (Gemini)", ["profile parsing", "label vision (1-3 photos)", "summary / ask / report",
                                      "model fallback + cache"]),
              ("Rules engine (0 LLM)", ["allergens, diets, conditions", "hidden sugars, INS codes", "claims, front vs back",
                                        "health score 0-100"]),
              ("Alternatives (0 LLM)", ["same-category candidates", "same score formula", "family-safe filter",
                                        "feedback re-ranking"]),
              ("Tracker & report", ["intake logs", "weekly budgets", "insights", "weekly report facts"])]
    for x, (t, ls) in zip(xs, titles):
        box(x * cm_, 3.6 * cm_, 3.75 * cm_, 2.3 * cm_, t, ls,
            fill=colors.HexColor("#f0fdf4") if "0 LLM" in t or "Tracker" in t else colors.HexColor("#fff7ed"))
        arrow((x + 1.875) * cm_, 6.5 * cm_, (x + 1.875) * cm_, 5.9 * cm_)
    # Layer 4: data
    box(0.3 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "Google Gemini API",
        ["gemini-3.6-flash (primary)", "3.5-flash-lite, 3.8-flash (fallback)", "JSON output, temperature 0-0.3"])
    box(5.7 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "SQLite (labelguard.db)",
        ["household, scans, intake_logs", "extraction_cache, llm_cache", "feedback, shopping, llm_calls"])
    box(11.1 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "Reference data",
        ["CSV/JSON lookup tables", "Indian products table (73)", "Open Food Facts API"])
    arrow(2.175 * cm_, 3.6 * cm_, 2.85 * cm_, 2.9 * cm_)
    arrow(6.225 * cm_, 3.6 * cm_, 8.25 * cm_, 2.9 * cm_)
    arrow(10.275 * cm_, 3.6 * cm_, 13.65 * cm_, 2.9 * cm_)
    arrow(14.325 * cm_, 3.6 * cm_, 8.6 * cm_, 2.9 * cm_)
    return d


# ----------------------------------------------------------------- page decor
def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont(BODY, 9)
        canvas.setFillColor(MUTED)
        canvas.drawString(2 * cm, 1.2 * cm, "LabelGuard - BCSE306L Artificial Intelligence - Project Report")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(LINE)
        canvas.line(2 * cm, 1.55 * cm, A4[0] - 2 * cm, 1.55 * cm)
    canvas.restoreState()


# ----------------------------------------------------------------- content
def build():
    st = []
    D = DETAILS

    # ---------- title page
    center = lambda size, bold=False, color=INK, lead=None: ParagraphStyle(  # noqa: E731
        f"c{size}{bold}", fontName=BOLD if bold else BODY, fontSize=size, leading=lead or size * 1.3,
        alignment=TA_CENTER, textColor=color)
    st += [Spacer(1, 0.6 * cm),
           Paragraph(D["school"], center(15)),
           Spacer(1, 0.15 * cm),
           Paragraph(D["course"], center(14, True)),
           Spacer(1, 0.1 * cm),
           Paragraph(D["review"], center(13)),
           Spacer(1, 2.0 * cm),
           Paragraph(D["title"], center(34, True, BRAND, 40)),
           Spacer(1, 0.4 * cm),
           Paragraph(D["subtitle"], center(14.5, False, INK, 19)),
           Spacer(1, 0.9 * cm),
           Paragraph("PROJECT REPORT", center(13, True, MUTED)),
           Spacer(1, 1.2 * cm),
           Paragraph("Submitted by", center(12, True)),
           Spacer(1, 0.25 * cm)]
    team = Table([[Paragraph("<b>Name</b>", S["body"]), Paragraph("<b>Register No.</b>", S["body"])]] +
                 [[Paragraph(n, S["body"]), Paragraph(r, S["body"])] for n, r in D["team"]],
                 colWidths=[6.5 * cm, 4.5 * cm])
    team.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE), ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    st += [team, Spacer(1, 1.1 * cm)]
    info = [["Faculty", D["guide"]], ["Slot", D["slot"]], ["Semester", D["semester"]], ["Date", D["date"]]]
    t = Table([[Paragraph(f"<b>{a}</b>", S["body"]), Paragraph(b, S["body"])] for a, b in info],
              colWidths=[3.5 * cm, 7.5 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    st += [t, PageBreak()]

    # ---------- a. Abstract
    st += [P("Abstract", "h1"),
           P("Packaged-food labels in India are hard to act on: sugar is split across many names (jaggery, invert syrup, "
             "maltodextrin), additives appear only as INS codes, front-of-pack words such as <i>healthy</i>, <i>natural</i> "
             "or <i>made with real fruit</i> are rarely checked against the ingredient list, and one household often has "
             "very different needs (a Jain diet, a pre-diabetic adult, a lactose-intolerant child). General-purpose "
             "chatbots can read a label but give a different answer each time, forget the family between conversations "
             "and may invent products."),
           P("<b>LabelGuard</b> is a web application that photographs or looks up a packaged food and produces a "
             "personalised, repeatable verdict for every family member. Its design principle is: <i>the LLM handles "
             "perception and interpretation; deterministic Python rules and real databases handle anything that must be "
             "consistent, verifiable or cheap.</i> A Gemini vision model reads one to three photos of a pack (front and "
             "back) into structured JSON in a single call. A rules engine with curated Indian lookup tables (54 sugar "
             "aliases, 49 INS additives, 22 allergen groups, 34 Jain/vegetarian/vegan/halal rules) then flags allergens, "
             "diet conflicts and medical-condition risks with evidence, checks label claims against FSSAI thresholds, "
             "compares front-of-pack promises with the back of the pack, and computes a transparent 0-100 health score. "
             "Better alternatives come from Open Food Facts and a 73-product Indian table, scored with the same formula. "
             "A tracker, insights page and weekly family report close the loop."),
           P("All safety-relevant outputs are deterministic (identical input gives identical output, verified by 46 "
             "automated tests); the LLM is used for only three core tasks plus two optional ones, every output is "
             "cached, and an automatic multi-model fallback keeps scans working when a model is overloaded. A typical "
             "new scan uses about 2,100 input and 450 output tokens and completes in roughly 5 seconds, while repeat "
             "scans, barcode lookups and every analysis module cost zero tokens."),
           Spacer(1, 4),
           P("<b>Keywords:</b> food labelling, large language models, multimodal extraction, rules engine, "
             "personalised nutrition, FSSAI, front-of-pack claims, Open Food Facts.")]

    # ---------- b. Introduction
    st += [P("1. Introduction", "h1"),
           P("1.1 Background", "h2"),
           P("India's packaged-food market has grown rapidly, and with it the share of daily sugar, salt and fat that "
             "comes from labelled products. FSSAI regulations require an ingredient list, a nutrition table and "
             "allergen declarations, and they define thresholds for claims such as <i>low sugar</i> or <i>high fibre</i>. "
             "In practice, consumers face three gaps: the information is technical (INS codes, per-100 g values, "
             "hidden sugar names), it is not personal (a label cannot know that one family member is Jain and another "
             "is diabetic), and marketing on the front of the pack frequently contradicts the back."),
           P("1.2 Problem statement", "h2"),
           P("Design and build a system that, from a photo (or barcode, or typed label) of a packaged food, can:"),
           *bullets([
               "accurately extract ingredients, nutrition values, serving size, claims and front-of-pack imagery;",
               "evaluate the product separately for each household member's allergies, diet (Jain, vegetarian, vegan, "
               "halal, eggetarian), medical conditions and daily limits, giving a SAFE / CAUTION / AVOID verdict with evidence;",
               "produce the <b>same</b> score and verdict every time for the same label, with a documented formula;",
               "detect hidden sugars, explain additives, check claims and expose front-versus-back contradictions;",
               "suggest real, safer alternatives and track intake over a week; and",
               "keep LLM token usage low and remain usable when the LLM or the internet is unavailable.",
           ]),
           P("1.3 Why not a general chatbot?", "h2"),
           table([["Requirement", "Plain chatbot", "LabelGuard"],
                  ["Consistent score", "Varies between runs", "Deterministic formula; identical result for identical input"],
                  ["Family memory", "Re-explain every time", "Profile saved once, applied to every member on every scan"],
                  ["Alternatives", "May invent products", "Real products from a database, same scoring"],
                  ["Indian context", "Generic", "Jain/halal rules, Indian names (kaju, besan), INS codes, FSSAI limits"],
                  ["History", "None", "Intake tracker, insights, weekly family report"],
                  ["Cost", "Long prompt per question", "One vision call per new product; cache makes repeats free"]],
                 [3.6 * cm, 4.4 * cm, 8.5 * cm]),
           Spacer(1, 6),
           P("1.4 Objectives and scope", "h2"),
           P("The project targets a demonstrable, single-household web application for Indian users. Medical "
             "diagnosis, verified brand databases and multi-user accounts are out of scope; every screen carries the "
             "disclaimer that the output is informational and not medical advice.")]

    # ---------- c. Methodology
    st += [Spacer(1, 8), P("2. Methodology", "h1"),
           P("2.1 System architecture", "h2"),
           P("LabelGuard is a three-tier application (Figure 1). A React single-page app talks to a FastAPI backend "
             "over JSON. The backend contains four engines: an LLM layer that wraps Google Gemini, a deterministic rules "
             "engine, an alternatives engine and a tracker/report module. Persistent state lives in a single SQLite "
             "file; reference knowledge lives in versioned CSV/JSON tables; product data comes from Open Food Facts "
             "with a local Indian fallback table."),
           architecture(),
           P("Figure 1: LabelGuard architecture. Orange components call the LLM; green components are pure Python.", "caption"),
           P("2.2 Division of work between the LLM and the rules", "h2"),
           table([["LLM task (Gemini)", "When it runs", "Fallback if unavailable"],
                  ["1. Profile parsing: free text to structured household JSON", "Once per profile edit (cached)", "Keyword parser"],
                  ["2. Label extraction: 1-3 photos to JSON (incl. front-of-pack imagery)", "Once per new image set (cached by hash)", "Barcode / manual entry / demo labels"],
                  ["3. Personalised 2-3 line summary (EN / HI / TA, ELI12 option)", "Per scan + language (cached)", "Template sentences"],
                  ["4. Optional: answer a question about a product", "On demand (cached)", "Answer built from rule output"],
                  ["5. Optional: weekly family report write-up", "On demand (cached)", "Template report"]],
                 [7.8 * cm, 4.5 * cm, 4.2 * cm]),
           Spacer(1, 4),
           P("Everything else - flags, scores, claim checks, front/back checks, alternatives, tracking, comparison, "
             "insights and allergy cards - is deterministic Python with zero LLM calls. The LLM never decides a verdict: "
             "summaries and answers receive the rule results as facts and are instructed not to change them."),
           P("2.3 Modules", "h2"),
           table([["Module", "Description"],
                  ["Family profile", "Free text parsed into members (name, relation, age, allergies, diet, conditions, daily sugar/sodium/sat-fat limits, ingredients to avoid); editable form; saved in SQLite."],
                  ["Scan", "Three inputs: paste/camera photos (up to 3 of one pack), barcode lookup (Open Food Facts, 0 tokens) and manual entry. Images resized to 1024 px; results cached by image hash and barcode."],
                  ["Result analysis", "Score ring, per-member verdicts with evidence, hidden sugars, additive cards, claim check, front-vs-back check, traffic-light label, per-serving table, summary with text-to-speech, Ask box, share and shopping list."],
                  ["Alternatives", "Top 3 safer, higher-scoring products in the same category with a reason and weekly 'swap impact'; thumbs up/down feedback re-ranks future results."],
                  ["Compare", "2-4 products side by side; winner = safest verdict for the selected member, then highest score."],
                  ["Explorer & decoder", "Browse 73 Indian products with family verdicts; decode any INS code or ingredient against every member."],
                  ["Tracker, insights, report", "Log intake per member; weekly budgets and daily charts; aggregate patterns; LLM-written weekly family report over computed facts."],
                  ["Allergy cards", "Printable per-member card listing allergens with Indian names, diet rules and conditions."]],
                 [3.4 * cm, 13.1 * cm])]

    st += [P("2.4 Algorithms", "h2"),
           P("Algorithm 1 - Label extraction with caching and model fallback", "h3"),
           *bullets([
               "Compute SHA-256 over the uploaded image(s); if the hash (or a decoded barcode) is in <i>extraction_cache</i>, reuse it (0 tokens).",
               "Otherwise validate and resize each image to at most 1024 px and send all images with the extraction prompt in one Gemini call "
               "(JSON output, temperature 0, 'use null, never guess', salt-to-sodium rule sodium_mg = salt_g x 400).",
               "If the model returns 429/5xx or times out (20 s), retry on the next model in the fallback list; a failed model is skipped for 5 minutes.",
               "Validate with Pydantic: coerce numbers, derive per-100 g values from per-serving values when only those are printed, and cache the result.",
           ]),
           KeepTogether([P("Algorithm 2 - Rules engine", "h3"),
           P("Ingredients are normalised and matched with word-boundary regular expressions that tolerate plurals "
             "(so <i>maltodextrin</i> never matches <i>dextrin</i> and <i>buckwheat</i> never matches <i>wheat</i>). INS/E-numbers are "
             "extracted from forms such as <i>E471</i>, <i>INS 330</i> and <i>Emulsifiers (322, 471)</i>. Exclusion lists prevent false "
             "positives (coconut milk is not dairy, fox nuts are not tree nuts). For each member the engine emits flags "
             "from allergens (AVOID if listed, CAUTION if 'may contain' or an unspecified parent group such as 'nuts'), "
             "diets (AVOID for forbidden items such as onion for Jain; CAUTION 'source unclear' for ambiguous items such "
             "as E471 or natural flavours), conditions (e.g. sugar &gt; 22.5 g/100 g is AVOID for diabetes; sodium &gt; 600 mg "
             "is AVOID for hypertension), personal limits (one serving using &ge; 40% of a daily sugar limit) and child "
             "rules (Southampton colours, caffeine, sweeteners). The member's status is the worst flag.")]),
           KeepTogether([P("Algorithm 3 - Health score (0-100, deterministic)", "h3"),
           table([["Component", "Rule", "Max"],
                  ["Sugar", "Solids 0.875 pts per g/100 g; drinks 3.5 pts per g/100 ml", "-35"],
                  ["Sodium", "0.025 pts per mg/100 g", "-25"],
                  ["Saturated fat", "Solids 2 pts per g; drinks 4 pts per g", "-20"],
                  ["Energy density", "Solids (kcal - 250)/30; drinks (kcal - 40)/8", "-10"],
                  ["Additives", "High concern 5, medium 2, low 0.5 each", "-15"],
                  ["Processing level", "Minimal 0, processed (or unknown) 5, ultra-processed 10", "-10"],
                  ["Fibre / protein bonus", "+1.6 pts per g fibre; +0.7 pts per g protein", "+8 / +7"]],
                 [3.6 * cm, 10.6 * cm, 2.3 * cm]),
           Spacer(1, 3),
           P("Score = clamp(100 - penalties + bonuses, 0, 100); each component is rounded to one decimal before summing. "
             "Grades: 70-100 <i>Good choice</i> (green), 50-69 <i>Okay occasionally</i> (amber), 0-49 <i>Limit this</i> (red). "
             "Thresholds follow UK FSA traffic-light levels, WHO sugar and sodium guidance and a NOVA-style processing estimate.")]),
           P("Algorithm 4 - Claim checker and front-vs-back check", "h3"),
           P("Claims are compared with FSSAI thresholds: <i>sugar free</i> &le; 0.5 g/100 g, <i>low sugar</i> &le; 5 g (2.5 g for "
             "drinks), <i>low sodium</i> &le; 120 mg, <i>high fibre</i> &ge; 6 g, <i>high protein</i> &ge; 20% of energy; <i>no added sugar</i> "
             "fails if any sugar alias is present; <i>multigrain/whole wheat</i> fails if the first ingredient is refined flour; "
             "vague words (<i>healthy</i>, <i>natural</i>) fail when sugar, sodium or saturated fat is high or the score is below 50. "
             "For the front of the pack, each pictured food is located in the ingredient list: it is misleading if absent, "
             "below 5%, or below 15% when the product is named after it. Messages such as <i>for kids</i>, <i>natural</i> or "
             "<i>no preservatives</i> are checked against colours, flavourings, preservatives, sugar and the score."),
           P("Algorithm 5 - Alternatives ranking", "h3"),
           P("Candidates in the same category are scored with Algorithm 3 and evaluated with Algorithm 2 for the selected "
             "members; any candidate that is AVOID for a member or does not beat the scanned score is removed. The rank "
             "value is score + feedback adjustment - 3 x (members with CAUTION). Feedback adds +8 per thumbs-up and -8 per "
             "thumbs-down on the same product, -10 for a disliked brand, and a sugar-proportional penalty after 'too sweet' "
             "feedback. Swap impact = (base - candidate nutrient per 100 g) x grams logged this week (or one serving a day) / 100.")]

    # ---------- d. Implementation
    st += [Spacer(1, 8), KeepTogether([P("3. Implementation", "h1"),
           P("3.1 Hardware and software requirements", "h2"),
           table([["Category", "Requirement"],
                  ["Hardware (development / demo)", "Any laptop with 4 GB RAM or more, dual-core CPU, 1 GB free disk; internet for Gemini and Open Food Facts. Optional: smartphone on the same Wi-Fi for camera capture."],
                  ["Operating system", "Windows 10/11, macOS or Linux"],
                  ["Backend", "Python 3.11+, FastAPI 0.143, Uvicorn, Pydantic v2, google-genai 2.31 (Gemini SDK), Pillow, Requests, Pandas, SQLite 3 (built in), pytest"],
                  ["Frontend", "Node.js 18+, React 18.3, Vite 5.4, Tailwind CSS 3.4, React Router 6, Recharts 2.15"],
                  ["External services", "Google Gemini API (gemini-3.6-flash primary; gemini-3.5-flash-lite and gemini-3.8-flash fallback); Open Food Facts API v2 (product and search)"],
                  ["Browser", "Any modern browser; clipboard paste and text-to-speech use standard Web APIs"]],
                 [4.2 * cm, 12.3 * cm])]),
           Spacer(1, 4),
           P("3.2 Supporting resources", "h2"),
           table([["Resource", "Contents"],
                  ["sugar_aliases.csv", "54 sugar names incl. jaggery, gur, khandsari, invert syrup, maltodextrin, with group and note"],
                  ["additives.csv", "49 INS/E-number additives with class, plain-English purpose, concern level and note"],
                  ["allergens.json", "22 allergen groups with Indian keywords (kaju, til, besan), parent groups and exclusion phrases"],
                  ["diet_rules.csv", "34 rules marking items avoid/check for vegetarian, vegan, Jain and halal diets"],
                  ["indian_products_fallback.csv", "73 common Indian packaged products (approximate values) across 17 categories"],
                  ["demo_labels.json", "4 complete demo labels (incl. front-of-pack data) that work offline"],
                  ["Database (SQLite)", "household, scans, extraction_cache, intake_logs, alt_feedback, shopping_list, llm_cache, off_cache, llm_calls"]],
                 [4.6 * cm, 11.9 * cm]),
           Spacer(1, 4),
           P("The REST API exposes about 30 endpoints, documented automatically by FastAPI at <i>/docs</i>, including "
             "<i>/api/scan</i>, <i>/api/scan/barcode</i>, <i>/api/scan/explain</i>, <i>/api/alternatives/{id}</i>, <i>/api/compare</i>, "
             "<i>/api/log</i>, <i>/api/tracker</i>, <i>/api/report</i>, <i>/api/products</i> and <i>/api/lookup</i>. All errors return a "
             "consistent <i>{error, detail}</i> JSON body that the interface shows as a friendly message.")]

    st += [P("3.3 Sample code", "h2"),
           code_block("(a) Deterministic health score (backend/rules/scoring.py, excerpt):", '''
sugar = n.get("sugar_g")
if sugar is not None:
    add("sugar", "Sugar", sugar, -min(35.0, sugar * (3.5 if liquid else 0.875)), f"{sugar} g per 100g")
sodium = n.get("sodium_mg")
if sodium is not None:
    add("sodium", "Sodium", sodium, -min(25.0, sodium * 0.025), f"{sodium} mg per 100g")
...
weights = {"high": 5.0, "medium": 2.0, "low": 0.5}
add_pen = min(15.0, sum(weights.get(a.get("concern"), 0.0) for a in additives))
level = processing_level(ingredients, additives)          # 1, 3 or 4
add("processing", "Processing level", level, -{1: 0.0, 3: 5.0, 4: 10.0}[level], ...)
raw = round(100 + sum(c["points"] for c in comps), 1)      # avoid float drift
score = int(max(0, min(100, math.floor(raw + 0.5))))
'''),
           code_block("(b) Allergy rule for one family member (backend/rules/engine.py, excerpt):", '''
for raw in m.allergens:
    key = data.resolve_allergen(raw)                 # "kaju" / "cashews" -> "cashew"
    a = present.get(key)
    if a and a["source"] == "ingredients":
        flag(AVOID, "allergen", f"Contains {a['display']} (listed allergy)", evidence(a))
    elif a:
        flag(WARN, "allergen", f"May contain traces of {a['display']}", evidence(a))
    elif table[key].get("parent") in present:        # generic "nuts" for a cashew allergy
        flag(WARN, "allergen", "Contains tree nuts that may include cashew - check the pack", ...)
'''),
           code_block("(c) Gemini call with automatic model fallback (backend/llm/gemini_client.py, excerpt):", '''
models = [config.GEMINI_MODEL] + [m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL]
healthy = [m for m in models if self._down_until.get(m, 0) <= time.monotonic()] or models
for model in healthy:
    try:
        return self._call(client, model, purpose, contents, temperature, max_tokens, timeout_s)
    except _ModelUnavailable as exc:                 # 429 / 5xx / timeout
        self._down_until[model] = time.monotonic() + config.GEMINI_MODEL_COOLDOWN_S
        last = LLMError(str(exc), exc.kind)
raise last
'''),
           code_block("(d) Front-of-pack check for a pictured food (backend/rules/front_back.py, excerpt):", '''
pos, ing, pct = _find(ingredients, item)             # position, text and % in the ingredient list
named = contains_term(norm(ex.product_name), _singular(item))
if pct is not None and pct < 5:
    verdict, reason = "misleading", f"Pictured on the front, but only {pct:g}% of the product."
elif named and pct is not None and pct < 15:
    verdict, reason = "misleading", f"The product is named after {item}, but it is only {pct:g}% ..."
'''),
           ]

    st += [P("3.4 Snapshots", "h2"),
           P("The snapshots below were captured from the running application with a sample household of four members "
             "(a Jain, pre-diabetic adult allergic to cashew; a lactose-intolerant 9-year-old; a mother with hypertension; "
             "and an uncle with diabetes and heart disease)."),
           figure("fig_scan_input.png", "Figure 2: Scan page - paste or photograph up to three images, barcode lookup, manual entry and demo labels."),
           figure("fig_result_summary.png", "Figure 3: Result summary - score, verdict, problem counts, actions and the AI-written family summary with text-to-speech."),
           figure("fig_front_back.png", "Figure 4: Front vs back of pack - all seven front-of-pack promises of a sample mango drink contradicted by its ingredient list."),
           figure("fig_family.png", "Figure 5: Per-member verdicts - the same product is AVOID for two members and CAUTION for two others."),
           figure("fig_alternatives.png", "Figure 6: Alternatives with reasons, swap impact, shopping list and feedback, beside the intake logger."),
           figure("fig_profile.png", "Figure 7: Family profile - free-text parsing into editable member cards.", width_cm=13.5, crop_h=860),
           figure("fig_tracker.png", "Figure 8: Tracker - weekly sugar and sodium budget used by each member (daily limit x 7).", width_cm=14, crop_h=735),
           figure("fig_report.png", "Figure 9: Weekly family report - numbers computed by the app, write-up generated by the LLM.", width_cm=14, crop_h=1080),
           figure("fig_products.png", "Figure 10: Product explorer - Indian products scored with the same formula and checked for the family.", width_cm=14, crop_h=720),
           ]

    # ---------- e. Conclusion
    st += [Spacer(1, 8), KeepTogether([P("4. Conclusion", "h1"),
           P("4.1 Overall efficiency", "h2"),
           P("The figures below were measured on the running system (Gemini usage is logged per call in the "
             "<i>llm_calls</i> table)."),
           table([["Measure", "Result"],
                  ["Label extraction (new image set)", "About 2,100 input + 450 output tokens; average 4.8 s (range 1.7-12.5 s) for successful calls"],
                  ["Repeat scan of the same photo / barcode lookup", "0 tokens (cache / Open Food Facts); under 1 s"],
                  ["Family summary", "About 340 input + 175 output tokens per scan and language; cached afterwards"],
                  ["Weekly report write-up", "About 900 input + 360 output tokens; 3.3 s; cached repeat 0.7 s"],
                  ["Analysis modules (flags, score, claims, front/back, alternatives, tracker)", "0 tokens; computed in milliseconds"],
                  ["Determinism", "Same extraction always yields an identical analysis and score (automated test, 5 runs)"],
                  ["Automated tests", "46 of 46 passing (rules, scoring, claims, API, caching, error handling)"],
                  ["Profile parser baseline", "Keyword fallback reaches 87% field accuracy (52/60) on 10 sample profiles"],
                  ["Front-vs-back detection (sample packs)", "7 of 7 misleading promises on a mango drink and 5 of 5 on a cereal; 0 false alarms on an honest makhana snack"],
                  ["Availability", "During testing the newest Gemini model frequently timed out (504/503); the automatic fallback still completed scans, and barcode, manual and demo modes work without the LLM"]],
                 [6.2 * cm, 10.3 * cm])]),
           Spacer(1, 6),
           P("4.2 Discussion", "h2"),
           P("LabelGuard shows that splitting the problem between a multimodal LLM and a deterministic rules engine gives "
             "the best of both: the model reliably reads messy photographs (including front-of-pack imagery) in a single "
             "low-cost call, while every verdict, score and recommendation is reproducible, explainable with evidence and "
             "free to recompute when the family profile changes. Caching and the multi-model fallback keep the "
             "application responsive and inexpensive; the per-member verdicts, Indian-specific knowledge and "
             "front-versus-back analysis provide value that a general chatbot does not."),
           P("4.3 Limitations and future work", "h2"),
           *bullets([
               "Extraction quality depends on the photo; low light, curved packs or tiny fonts can lead to missed values (shown to the user as confidence and unreadable fields).",
               "Ingredient matching is keyword based; unusual spellings and regional-language labels need more synonyms or translation.",
               "The local product table uses approximate values; a verified brand database would be required for production.",
               "The score is a transparent heuristic, not a clinically validated index; a dietitian review of thresholds is planned.",
               "Future work: live barcode scanning with the camera, a fully translated Hindi/Tamil interface, user accounts, a larger labelled evaluation set and a study with real families.",
           ])]

    # ---------- f. References
    ref_heading = P("5. References", "h1")
    refs = [
        "Food Safety and Standards Authority of India (FSSAI). <i>Food Safety and Standards (Labelling and Display) Regulations</i>, 2020.",
        "Food Safety and Standards Authority of India (FSSAI). <i>Food Safety and Standards (Advertising and Claims) Regulations</i>, 2018.",
        "UK Department of Health and Food Standards Agency. <i>Guide to Creating a Front of Pack (FoP) Nutrition Label for Pre-packed Products Sold through Retail Outlets</i>, 2016.",
        "World Health Organization. <i>Guideline: Sugars Intake for Adults and Children</i>. Geneva: WHO, 2015.",
        "World Health Organization. <i>Guideline: Sodium Intake for Adults and Children</i>. Geneva: WHO, 2012.",
        "Indian Council of Medical Research - National Institute of Nutrition. <i>Dietary Guidelines for Indians</i>, 2024.",
        "Monteiro, C. A., et al. Ultra-processed foods: what they are and how to identify them. <i>Public Health Nutrition</i>, 22(5), 936-941, 2019.",
        "McCann, D., et al. Food additives and hyperactive behaviour in 3-year-old and 8/9-year-old children in the community. <i>The Lancet</i>, 370(9598), 1560-1567, 2007.",
        "Codex Alimentarius Commission. <i>Class Names and the International Numbering System for Food Additives (CXG 36-1989)</i>, updated.",
        "Open Food Facts. <i>Open Food Facts API documentation (v2)</i>. https://openfoodfacts.github.io/openfoodfacts-server/api/",
        "Google. <i>Gemini API documentation: models, structured output and thinking</i>. https://ai.google.dev/gemini-api/docs",
        "FastAPI documentation. https://fastapi.tiangolo.com/ ; React documentation. https://react.dev/ ; Recharts. https://recharts.org/",
    ]
    ref_paras = [Paragraph(f"[{i}] {r}", S["ref"]) for i, r in enumerate(refs, 1)]
    st += [KeepTogether([ref_heading] + ref_paras[:3])] + ref_paras[3:]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=2 * cm, title="LabelGuard - Project Report", author=", ".join(n for n, _ in DETAILS["team"]),
                            subject="Personalised food-label scanner")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
    return OUT


if __name__ == "__main__":
    out = build()
    print("Wrote", out)
