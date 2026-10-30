"""
Builds docs/LabelGuard_Research_Paper.pdf in the layout of the course sample paper:
single column, Times New Roman 12 pt, justified text with first-line indent, bold numbered headings,
"Table N:" captions above tables, "Fig N:" captions below figures, numbered references.

    python docs/make_paper.py

All experimental numbers are read from docs/paper_results.json (produced from backend/eval/results).
Needs: pip install reportlab pillow
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image as PILImage
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
OUT = HERE / "LabelGuard_Research_Paper.pdf"
R = json.loads((HERE / "paper_results.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ authors
CORRESPONDING = ("Corresponding author: Dr. D. Anuradha, Assistant Professor Sr.Grade-1, School of Computer Science and "
                 "Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India, <u>anuradha.d@vit.ac.in</u>")
STUDENTS = [  # (name, register no., e-mail or None)
    ("Harsh Kulkarni", "24BCT0137", None),
    ("B S Srivallabha", "24BCE0457", None),
    ("Ayush Konar", "24BDS0107", None),
    ("Pratham Paudel", "24BCE2940", None),
]
AFFIL = "Bachelor Of Technology, School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India."

# ------------------------------------------------------------------ fonts
FD = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
try:
    pdfmetrics.registerFont(TTFont("TNR", str(FD / "times.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-B", str(FD / "timesbd.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-I", str(FD / "timesi.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-BI", str(FD / "timesbi.ttf")))
    registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-BI")
    BODY, BOLD, ITAL = "TNR", "TNR-B", "TNR-I"
except Exception:
    BODY, BOLD, ITAL = "Times-Roman", "Times-Bold", "Times-Italic"

W_TEXT = 8.5 * inch - 2 * 1.3 * inch  # 5.9 in text width, as in the sample
S = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=14, leading=17, alignment=TA_CENTER, spaceAfter=10),
    "author": ParagraphStyle("author", fontName=BODY, fontSize=10.5, leading=12.6, alignment=TA_CENTER, spaceAfter=7),
    "h": ParagraphStyle("h", fontName=BOLD, fontSize=12, leading=14.6, spaceBefore=9, spaceAfter=1),
    "body": ParagraphStyle("body", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_JUSTIFY, firstLineIndent=33),
    "flat": ParagraphStyle("flat", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_JUSTIFY),
    "num": ParagraphStyle("num", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_JUSTIFY, leftIndent=38,
                          bulletIndent=18),
    "lead": ParagraphStyle("lead", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_JUSTIFY),
    "cap_t": ParagraphStyle("cap_t", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_CENTER, spaceBefore=7,
                            spaceAfter=2),
    "cap_f": ParagraphStyle("cap_f", fontName=BODY, fontSize=12, leading=14.6, alignment=TA_CENTER, spaceBefore=3,
                            spaceAfter=9),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=10.5, leading=12.4),
    "cellc": ParagraphStyle("cellc", fontName=BODY, fontSize=10.5, leading=12.4, alignment=TA_CENTER),
    "cellf": ParagraphStyle("cellf", fontName=BODY, fontSize=10.5, leading=14.2),
    "cellh": ParagraphStyle("cellh", fontName=BOLD, fontSize=10.5, leading=12.4, alignment=TA_CENTER),
    "ref": ParagraphStyle("ref", fontName=BODY, fontSize=11, leading=12.6, alignment=TA_JUSTIFY, leftIndent=17,
                          firstLineIndent=-17, spaceAfter=1),
}

# ------------------------------------------------------------------ references (numbered by first citation)
REFS = {
    "who_sugar": "World Health Organization, 2015. Guideline: Sugars intake for adults and children. Geneva: World Health Organization.",
    "who_sodium": "World Health Organization, 2012. Guideline: Sodium intake for adults and children. Geneva: World Health Organization.",
    "hall": "Hall, K.D., Ayuketah, A., Brychta, R., Cai, H., Cassimatis, T., Chen, K.Y., et al., 2019. Ultra-processed diets cause excess calorie intake and weight gain: an inpatient randomized controlled trial of ad libitum food intake. Cell Metabolism. doi:10.1016/j.cmet.2019.05.008.",
    "monteiro": "Monteiro, C.A., Cannon, G., Levy, R.B., Moubarac, J.C., Louzada, M.L., Rauber, F., et al., 2019. Ultra-processed foods: what they are and how to identify them. Public Health Nutrition, 22(5), pp.936-941.",
    "mccann": "McCann, D., Barrett, A., Cooper, A., Crumpler, D., Dalen, L., Grimshaw, K., et al., 2007. Food additives and hyperactive behaviour in 3-year-old and 8/9-year-old children in the community: a randomised, double-blinded, placebo-controlled trial. The Lancet, 370(9598), pp.1560-1567.",
    "fssai_label": "Food Safety and Standards Authority of India, 2020. Food Safety and Standards (Labelling and Display) Regulations, 2020. New Delhi: FSSAI.",
    "fssai_claims": "Food Safety and Standards Authority of India, 2018. Food Safety and Standards (Advertising and Claims) Regulations, 2018. New Delhi: FSSAI.",
    "grunert": "Grunert, K.G. and Wills, J.M., 2007. A review of European research on consumer response to nutrition information on food labels. Journal of Public Health, 15. doi:10.1007/s10389-007-0101-9.",
    "julia": "Julia, C. and Hercberg, S., 2017. Nutri-Score: evidence of the effectiveness of the French front-of-pack nutrition label. Ernährungs Umschau, 64(12), pp.181-187.",
    "ukdh": "Department of Health, Food Standards Agency, Scottish Government and Welsh Government, 2016. Guide to creating a front of pack (FoP) nutrition label for pre-packed products sold through retail outlets. London.",
    "icmr": "ICMR-National Institute of Nutrition, 2024. Dietary Guidelines for Indians. Hyderabad: Indian Council of Medical Research.",
    "codex": "Codex Alimentarius Commission. Class names and the international numbering system for food additives, CXG 36-1989. Rome: FAO/WHO.",
    "gemini": "Gemini Team, Google, 2023. Gemini: a family of highly capable multimodal models. arXiv preprint arXiv:2312.11805.",
    "brown": "Brown, T.B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., et al., 2020. Language models are few-shot learners. Advances in Neural Information Processing Systems, 33, pp.1877-1901.",
    "ji": "Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., et al., 2023. Survey of hallucination in natural language generation. ACM Computing Surveys. arXiv:2202.03629.",
    "hua": "Hua, A., Dhaliwal, M.P., Burke, R., Pullela, L. and Qin, Y., 2025. NutriBench: a dataset for evaluating large language models in nutrition estimation from meal descriptions. International Conference on Learning Representations (ICLR).",
    "min": "Min, W., Jiang, S., Liu, L., Rui, Y. and Jain, R., 2019. A survey on food computing. ACM Computing Surveys, 52(5), Article 92.",
    "meyers": "Meyers, A., Johnston, N., Rathod, V., Korattikara, A., Gorban, A., Silberman, N., et al., 2015. Im2Calories: towards an automated mobile vision food diary. Proceedings of the IEEE International Conference on Computer Vision (ICCV), pp.1233-1241.",
    "bossard": "Bossard, L., Guillaumin, M. and Van Gool, L., 2014. Food-101 - mining discriminative components with random forests. European Conference on Computer Vision (ECCV), LNCS 8694, pp.446-461.",
    "marin": "Marín, J., Biswas, A., Ofli, F., Hynes, N., Salvador, A., Aytar, Y., Weber, I. and Torralba, A., 2021. Recipe1M+: a dataset for learning cross-modal embeddings for cooking recipes and food images. IEEE Transactions on Pattern Analysis and Machine Intelligence, 43(1), pp.187-203.",
    "smith": "Smith, R., 2007. An overview of the Tesseract OCR engine. Proceedings of the 9th International Conference on Document Analysis and Recognition (ICDAR), vol. 2, pp.629-633.",
    "singhal": "Singhal, K., Azizi, S., Tu, T., Mahdavi, S.S., Wei, J., Chung, H.W., et al., 2023. Large language models encode clinical knowledge. Nature, 620, pp.172-180.",
    "lewis": "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., et al., 2020. Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33, pp.9459-9474.",
    "off": "Open Food Facts. Open Food Facts API documentation (v2). https://openfoodfacts.github.io/openfoodfacts-server/api/ (accessed October 2026).",
    "gemapi": "Google. Gemini API documentation: models, structured output and thinking. https://ai.google.dev/gemini-api/docs (accessed October 2026).",
}
_order: list[str] = []


def c(*keys: str) -> str:
    nums = []
    for k in keys:
        if k not in _order:
            _order.append(k)
        nums.append(str(_order.index(k) + 1))
    return "[" + ", ".join(nums) + "]"


# ------------------------------------------------------------------ helpers
def P(text, style="body"):
    return Paragraph(text, S[style])


def H(text):
    return Paragraph(text, S["h"])


def numbered(items):
    return [Paragraph(t, S["num"], bulletText=f"{i}.") for i, t in enumerate(items, 1)]


def bullets(items):
    return [Paragraph(t, S["num"], bulletText="\u2022") for t in items]


def table(rows, widths, left_cols=(), header=True, cell_style="cell"):
    data = []
    for i, row in enumerate(rows):
        out = []
        for j, cell in enumerate(row):
            st = "cellh" if (header and i == 0) else (cell_style if j in left_cols else "cellc")
            out.append(Paragraph(cell, S[st]) if isinstance(cell, str) else cell)
        data.append(out)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def cap_t(n, text):
    return Paragraph(f"<b>Table {n}:</b> {text}", S["cap_t"])


def figure(name, n, caption, width_in=5.0, max_h_in=4.6):
    img = PILImage.open(SHOTS / name)
    w, h = img.size
    width = width_in * inch
    height = width * h / w
    if height > max_h_in * inch:
        width, height = width * max_h_in * inch / height, max_h_in * inch
    return KeepTogether([Image(str(SHOTS / name), width=width, height=height),
                         Paragraph(f"<b>Fig {n}:</b> {caption}", S["cap_f"])])


# ------------------------------------------------------------------ Fig 1: architecture
def architecture():
    W, H_ = 16.5 * 28.3465, 10.6 * 28.3465
    d = Drawing(W, H_)
    cm_ = 28.3465
    INK, MUTED, BRAND = colors.black, colors.HexColor("#444444"), colors.HexColor("#1f3a8a")

    def box(x, y, w, h, title, lines=(), fill=colors.white):
        d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=BRAND, strokeWidth=1))
        d.add(String(x + w / 2, y + h - 13, title, fontName=BOLD, fontSize=9, textAnchor="middle", fillColor=INK))
        for i, ln in enumerate(lines):
            d.add(String(x + w / 2, y + h - 25 - i * 10, ln, fontName=BODY, fontSize=7.8, textAnchor="middle", fillColor=MUTED))

    def arrow(x1, y1, x2, y2):
        import math
        d.add(Line(x1, y1, x2, y2, strokeColor=MUTED, strokeWidth=0.9))
        ang = math.atan2(y2 - y1, x2 - x1)
        a, s = 0.45, 5
        d.add(Polygon([x2, y2, x2 - s * math.cos(ang - a), y2 - s * math.sin(ang - a),
                       x2 - s * math.cos(ang + a), y2 - s * math.sin(ang + a)], fillColor=MUTED, strokeColor=MUTED))

    box(0.3 * cm_, 8.6 * cm_, 15.9 * cm_, 1.7 * cm_, "Client: React 18 + Vite + Tailwind single-page application",
        ["Scan (paste / camera / barcode / manual)  |  Results  |  Explorer  |  Tracker  |  Weekly report  |  Profile"],
        fill=colors.HexColor("#eef2ff"))
    arrow(8.25 * cm_, 8.6 * cm_, 8.25 * cm_, 7.95 * cm_)
    d.add(String(8.45 * cm_, 8.15 * cm_, "REST / JSON (/api/*)", fontName=ITAL, fontSize=7.8, fillColor=MUTED))
    box(0.3 * cm_, 6.5 * cm_, 15.9 * cm_, 1.45 * cm_, "FastAPI backend (Python, Pydantic v2)",
        ["routers: profile, scan, alternatives, compare, tracker / report, extras  |  uniform {error, detail} errors"])
    xs = [0.3, 4.35, 8.4, 12.45]
    boxes = [("LLM layer (Gemini)", ["profile parsing", "label vision (1-3 photos)", "summary / ask / report", "model fallback + cache"]),
             ("Rules engine (no LLM)", ["allergens, diets, conditions", "hidden sugars, INS codes", "claims, front vs back", "health score 0-100"]),
             ("Alternatives (no LLM)", ["same-category candidates", "same score formula", "family-safe filter", "feedback re-ranking"]),
             ("Tracker and report", ["intake logs", "weekly budgets", "insights", "report facts"])]
    for x, (t, ls) in zip(xs, boxes):
        box(x * cm_, 3.6 * cm_, 3.75 * cm_, 2.3 * cm_, t, ls,
            fill=colors.HexColor("#fff4e5") if "LLM layer" in t else colors.HexColor("#eaf7ee"))
        arrow((x + 1.875) * cm_, 6.5 * cm_, (x + 1.875) * cm_, 5.9 * cm_)
    box(0.3 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "Google Gemini API",
        ["primary + two fallback models", "JSON output, low temperature", "timeouts and 5-minute cool-down"])
    box(5.7 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "SQLite (labelguard.db)",
        ["household, scans, intake_logs", "extraction_cache, llm_cache", "off_cache, feedback, shopping, llm_calls"])
    box(11.1 * cm_, 0.35 * cm_, 5.1 * cm_, 2.55 * cm_, "Reference data",
        ["CSV / JSON knowledge tables", "Indian products table (73)", "Open Food Facts API"])
    arrow(2.175 * cm_, 3.6 * cm_, 2.85 * cm_, 2.9 * cm_)
    arrow(6.225 * cm_, 3.6 * cm_, 8.25 * cm_, 2.9 * cm_)
    arrow(10.275 * cm_, 3.6 * cm_, 13.65 * cm_, 2.9 * cm_)
    arrow(14.325 * cm_, 3.6 * cm_, 8.6 * cm_, 2.9 * cm_)
    scale = W_TEXT / W
    d.scale(scale, scale)
    d.width, d.height = W * scale, H_ * scale
    return d


# ------------------------------------------------------------------ Fig 2: bar chart
def consistency_chart():
    d = Drawing(W_TEXT, 175)
    ch = VerticalBarChart()
    ch.x, ch.y, ch.width, ch.height = 55, 30, W_TEXT - 80, 120
    ch.data = [[R["chat"]["t1_sd"], R["chat"]["t0_sd"], 0.0]]
    ch.categoryAxis.categoryNames = ["Plain LLM (temperature 1.0)", "Plain LLM (temperature 0)", "LabelGuard (rules)"]
    ch.categoryAxis.labels.fontName = BODY
    ch.categoryAxis.labels.fontSize = 9
    ch.valueAxis.valueMin = 0
    top = max(R["chat"]["t1_sd"], R["chat"]["t0_sd"], 1.0)
    ch.valueAxis.valueMax = round(top * 1.25 + 0.5)
    ch.valueAxis.labels.fontName = BODY
    ch.valueAxis.labels.fontSize = 9
    ch.valueAxis.visibleGrid = False
    ch.bars[0].fillColor = colors.HexColor("#0000ff")
    ch.barWidth = 30
    ch.groupSpacing = 40
    ch.barLabelFormat = "%.1f"
    ch.barLabels.nudge = 7
    ch.barLabels.fontName = BODY
    ch.barLabels.fontSize = 9
    d.add(ch)
    d.add(String(ch.x - 5, ch.y + ch.height + 12, "Score standard deviation across runs (points)", fontName=BODY, fontSize=9,
                 textAnchor="start"))
    return d


# ------------------------------------------------------------------ build
def build():
    st = []
    ch = R["chat"]
    changed1 = ch["n_products"] - int(ch["t1_ident"].split("/")[0])
    changed0 = ch["n_products"] - int(ch["t0_ident"].split("/")[0])
    # ---- title and authors
    st.append(Paragraph("LabelGuard: A Hybrid Vision-Language and Rule-Based Approach for Personalised "
                        "Food-Label Analysis for Indian Households", S["title"]))
    st.append(Paragraph(CORRESPONDING, S["author"]))
    for name, reg, mail in STUDENTS:
        tail = f" <u>{mail}</u>" if mail else ""
        st.append(Paragraph(f"{name} ({reg}), {AFFIL}{tail}", S["author"]))

    # ---- abstract
    X = R["extract"]["clean"]
    st += [H("Abstract"),
           P("Packaged-food labels are the main source of information at the point of purchase, yet they are hard to "
             "act on: sugar is split across dozens of names, additives are printed as numeric codes, front-of-pack "
             "claims are seldom checked against the ingredient list, and a single household can combine very different "
             "dietary needs. General-purpose chatbots can read a label, but their answers are not guaranteed to repeat, "
             "they forget the family between conversations and they may invent products. This paper presents LabelGuard, a "
             "web application that analyses a packaged food for every member of a household. A multimodal large "
             "language model converts one to three photographs of a pack into structured data in a single call, while "
             "a deterministic rules engine, backed by curated Indian knowledge tables (54 sugar names, 49 INS "
             "additives, 22 allergen groups and 34 diet rules), produces SAFE, CAUTION or AVOID verdicts with "
             "evidence, checks claims against FSSAI-style thresholds, compares the promises on the front of the pack "
             "with its ingredient list and computes a transparent 0-100 health score. Alternatives come from real "
             "products, intake is tracked against personal limits and a weekly report is generated. On "
             f"{R['n_images']} labelled test labels the system reached an ingredient F1 of {X['ing_f1']:.2f}, hidden-sugar "
             f"precision and recall of {X['sugar_p']:.2f} and {X['sugar_r']:.2f}, and {X['nut_acc']:.0%} nutrition-value accuracy on clean images, "
             f"while a plain LLM asked to score eight of these products was not exactly repeatable (standard deviation {ch['t1_sd']:.1f} points, "
             f"{changed1} of {ch['n_products']} products changed between runs) and rated them on a different scale (Pearson r = {ch['t1_r']:.2f} with the documented score), "
             "against zero variation for LabelGuard. The findings point out that using the language model "
             "only for perception and wording, and rules for every decision, gives repeatable, explainable and "
             "inexpensive label analysis."),
           Spacer(1, 6),
           P("Key word: Food label analysis, Large language models, Multimodal extraction, Rule-based reasoning, "
             "Personalised nutrition, FSSAI, Hallucination mitigation, Open Food Facts", "flat"),
           Spacer(1, 4)]

    # ---- 1. Introduction
    st += [H("1. Introduction"),
           P("Diet is one of the most important modifiable influences on health, and packaged foods now supply a "
             "large share of what people eat. The World Health Organization recommends keeping free sugars below 10% "
             f"of total energy intake {c('who_sugar')} and consuming less than 2 g of sodium (about 5 g of salt) per day "
             f"{c('who_sodium')}. In a controlled inpatient trial, diets rich in ultra-processed food led to higher energy "
             f"intake and weight gain than minimally processed diets {c('hall', 'monteiro')}, and a randomised trial in "
             "children linked mixtures of certain artificial colours and sodium benzoate to increased hyperactivity "
             f"{c('mccann')}."),
           P("The label is the consumer's main tool for acting on such advice. In India the FSSAI Labelling and "
             f"Display Regulations {c('fssai_label')} require an ingredient list, nutrition information and allergen "
             f"declarations, and the Advertising and Claims Regulations {c('fssai_claims')} define when statements such as "
             "'low sugar' or 'high protein' may be used. Labels nevertheless remain difficult to use: a review of "
             "European research examined how consumers perceive, understand and use nutrition information on labels "
             f"{c('grunert')}, and front-of-pack schemes such as Nutri-Score {c('julia')} or the UK traffic-light label "
             f"{c('ukdh')} simplify the picture by giving one verdict per product for an average consumer."),
           P("Indian households add further complications. Sugar is written as jaggery, invert syrup, liquid glucose or "
             "maltodextrin; additives appear as INS numbers; vegetarian, Jain, vegan and halal requirements depend on "
             "ingredients such as gelatin, E471 or onion derivatives; and one family may include a pre-diabetic adult, a "
             "child with lactose intolerance and a grandparent with hypertension. A single score cannot serve all of "
             "them, and the words on the front of the pack (for example 'healthy', 'natural' or 'made with real fruit') "
             "are rarely compared with the ingredient list on the back."),
           P("Multimodal large language models (LLMs) can read a photograph of a label and answer questions about it "
             f"{c('gemini', 'brown')}, so asking a chatbot is the obvious shortcut. However, generative models are known to "
             f"produce unfaithful or fabricated content {c('ji')}, their answers are not guaranteed to repeat, they keep no "
             "memory of the family, and benchmarking studies of LLM nutrition estimation report that errors depend on "
             f"how portions are described {c('hua')}. For decisions about allergies and chronic conditions, a number that "
             "cannot be reproduced exactly or traced back to its inputs is hard to trust."),
           P("We therefore propose LabelGuard, built on one rule: the LLM handles perception and language, while "
             "deterministic Python rules and real databases handle anything that must be consistent, verifiable or "
             "cheap. The LLM transcribes the label into structured data and writes short summaries; every flag, score, "
             "claim check and recommendation is computed by rules from curated Indian knowledge tables. The remainder of "
             "this paper reviews related work (Section 2), states the contributions (Section 3), describes the proposed "
             "methodology (Section 4), reports experimental results (Section 5) and concludes (Section 6).")]

    # ---- 2. Related Works
    st += [H("2. Related Works"),
           P(f"Food computing has been surveyed by Min et al. (2019) {c('min')}, covering recognition, recommendation and "
             "health-oriented analysis of food data. Image-based dietary assessment is represented by Meyers et al. "
             f"(2015) {c('meyers')}, who estimate the calories of a meal from a single photograph by combining food "
             f"recognition with depth-based volume estimation, by the Food-101 benchmark of Bossard et al. (2014) {c('bossard')} "
             f"with 101 food categories and 101,000 images, and by Recipe1M+ (Marín et al., 2021) {c('marin')}, which links over "
             "one million recipes with 13 million images for cross-modal retrieval. These works recognise prepared "
             "dishes; they do not read the printed ingredient list, allergen statement or claims of a packaged product."),
           P(f"Optical character recognition engines such as Tesseract (Smith, 2007) {c('smith')} extract text from images but "
             "return text and layout rather than structured fields; curved packaging, mixed fonts and nutrition tables "
             f"need further parsing. Multimodal LLMs {c('gemini')} read and structure the label in a single step, and can also "
             "describe the imagery on the front of a pack, which OCR cannot interpret."),
           P("Research on labels shows why interpretation matters. Grunert and Wills (2007) reviewed European studies "
             f"of how consumers perceive, understand and use nutrition labels {c('grunert')}. Julia and Hercberg (2017) "
             f"describe the evidence behind the five-colour Nutri-Score {c('julia')}, and the UK guidance defines traffic-light "
             f"levels per 100 g {c('ukdh')}; both give one grade for an average consumer. The NOVA classification {c('monteiro')} "
             "and the trial by Hall et al. (2019) "
             f"{c('hall')} motivate counting processing level in a score, and the national reference for Indian diets is the ICMR-NIN "
             f"Dietary Guidelines {c('icmr')}. Additives follow the Codex international numbering system {c('codex')}."),
           P("Recent work examines LLMs in nutrition and health. Singhal et al. (2023) "
             f"{c('singhal')} evaluate the clinical knowledge of LLMs on medical question-answering benchmarks, and NutriBench "
             f"(Hua et al., 2025) {c('hua')} benchmarks nutrition estimation from textual meal descriptions. Retrieval-augmented "
             f"generation (Lewis et al., 2020) {c('lewis')} grounds model output in retrieved text, and the survey by Ji et al. "
             f"(2023) {c('ji')} reviews hallucination and its mitigation. LabelGuard is related in spirit to retrieval "
             "augmentation, but instead of retrieving passages for the model to paraphrase it computes the facts with "
             f"rules and lets the model verbalise them. Finally, Open Food Facts {c('off')} is a crowd-sourced open product "
             "database that we use for barcode look-ups and alternatives; its coverage of Indian products is "
             "incomplete, so we complement it with a local table. Table 1 summarises the related works and their "
             "limitations with respect to our problem."),
           cap_t(1, "Various related works and their limitations")]
    rows = [["Author(s)", "Year", "Scope", "Limitations"],
            [f"Min et al. {c('min')}", "2019", "Survey of food computing: recognition, recommendation, health", "Broad overview; no personalised label analysis"],
            [f"Meyers et al. {c('meyers')}", "2015", "Calorie estimation from meal photographs", "Targets prepared dishes; does not read labels or allergens"],
            [f"Bossard et al. {c('bossard')}", "2014", "Food-101 image benchmark (101 categories)", "Classification only; no ingredient or nutrition reading"],
            [f"Marín et al. {c('marin')}", "2021", "Recipe1M+ recipe-image embeddings", "Recipes, not packaged-food labels; no health rules"],
            [f"Smith {c('smith')}", "2007", "Tesseract OCR engine", "Returns raw text; no structuring or interpretation"],
            [f"Grunert and Wills {c('grunert')}", "2007", "Review of consumer response to nutrition labels", "Studies consumers; no automated tool"],
            [f"Julia and Hercberg {c('julia')}", "2017", "Nutri-Score front-of-pack label", "One grade for an average consumer; not personalised"],
            [f"Hall et al. {c('hall')}", "2019", "Controlled trial of ultra-processed diets", "Evidence base, not a label tool"],
            [f"Singhal et al. {c('singhal')}", "2023", "LLM clinical knowledge on medical question answering", "General medical QA; not label-specific or repeatable"],
            [f"Hua et al. {c('hua')}", "2025", "NutriBench: LLM nutrition estimation from meal text", "Text descriptions only; no label images or personalisation"],
            [f"Lewis et al. {c('lewis')}", "2020", "Retrieval-augmented generation", "Model still paraphrases retrieved text; no deterministic guarantee"],
            [f"Ji et al. {c('ji')}", "2023", "Survey of hallucination in language generation", "Survey; mitigation left to the application"]]
    st.append(table(rows, [100, 30, 140, 154], left_cols=(0, 2, 3)))
    st.append(Spacer(1, 6))

    # ---- 3. Contribution and Novelty
    st += [H("3. Contribution and Novelty"),
           P("The proposed methodology comes with a hybrid approach and an experimental evaluation that try to overcome the "
             "limitations of the previous methods discussed above (see Table 1), with the following contributions:"),
           *numbered([
               "Hybrid Architecture with a Strict Division of Labour: the LLM only reads labels and words summaries; "
               "verdicts, scores, claim checks and recommendations are deterministic, so the same input always gives the "
               "same output and the model can never change a verdict.",
               "Household-Level Personalisation in the Indian Context: every product is evaluated separately for each family "
               "member against allergies, Jain, vegetarian, vegan and halal rules, medical conditions and personal daily "
               "limits, using Indian allergen names, INS additives and hidden sugar aliases, and ambiguous ingredients are "
               "reported as 'source unclear' instead of being guessed.",
               "Detection of Marketing Contradictions: a claim checker based on FSSAI-style thresholds and a front-versus-back "
               "check, obtained from the same single vision call, compare pictured foods and front-of-pack messages with "
               "the ingredient list, percentages, additives and score.",
               "Grounded Recommendation, Tracking and Cost Control: alternatives are real products scored with the same "
               "formula, intake is tracked against weekly budgets, a weekly report separates computed facts from "
               "LLM wording, and caching with automatic model fall-back keeps token use low and the service available."]),
           ]

    # ---- 4. Proposed Methodology
    st += [H("4. Proposed Methodology"),
           H("4.1 Dataset Information"),
           P("LabelGuard works with a household profile, label data and a set of curated knowledge tables. The profile "
             "stores, for each member, the name, relation, age, allergens, diet rules (vegetarian, eggetarian, vegan, Jain, "
             "halal), medical conditions, daily limits for sugar, sodium and saturated fat (defaults of 25 g, 2,000 mg and "
             "20 g) and ingredients to avoid. Label data arrive by three routes: photographs read by the vision model, "
             f"barcode look-ups on the Open Food Facts API {c('off')} and manual entry. The knowledge tables, kept in CSV and "
             "JSON files, are: 54 sugar aliases (for example jaggery, khandsari, invert syrup and maltodextrin) grouped "
             f"by family; 49 additives identified by INS number {c('codex')} with class, purpose and concern level (11 high, 23 "
             "medium, 15 low); 22 allergen groups with Indian names (kaju, til, besan) and exclusion phrases; 34 diet "
             "rules marking ingredients as avoid or needs-check for each diet; and a table of 73 common Indian packaged "
             "products in 16 categories, with approximate nutrition values, used as a fallback source of alternatives. "
             f"For evaluation, {R['n_images']} additional test labels with known ground truth were created (Section 5.1)."),
           H("4.2 Data Preprocessing"),
           P("The preprocessing steps carried out before any rule is applied include image preparation, validation of the "
             "extracted data, normalisation of ingredient text and handling of missing values."),
           P("1. Image Preprocessing: Uploaded images are validated, rotated according to their EXIF orientation, "
             "converted to RGB and resized to at most 1,024 pixels on the longer side before being sent to the model. "
             "A SHA-256 hash of the image set is used as a cache key, so a photograph that has been read once is never sent twice.", "lead"),
           P("2. Structured Extraction and Validation: The JSON returned by the model is validated with Pydantic. Numbers "
             "are coerced and negative values removed; salt is converted to sodium (Na in mg = 400 × salt in g); energy "
             "printed only in kJ is converted to kcal in the prompt; and when only per-serving values are printed, "
             "per-100 g values are derived as (per-serving value) × 100 / G, where G is the serving size in grams. Barcodes are reduced to 8-14 digits.", "lead"),
           P("3. Ingredient Normalisation: The ingredient list is split on commas that are not inside brackets, "
             "lower-cased and matched with word-boundary expressions that tolerate plurals, so that 'maltodextrin' "
             "never matches 'dextrin' and 'buckwheat' never matches 'wheat'. Exclusion phrases prevent false positives "
             "such as 'coconut milk' (not dairy) or 'fox nuts' (not tree nuts).", "lead"),
           P("4. Additive Code Extraction: Codes are extracted from forms such as 'E471', 'INS 330', 'Emulsifiers (322, 471)' "
             "and 'INS 503(ii)', and additives are also recognised by name (for example 'aspartame'), then looked up "
             "in the additive table.", "lead"),
           P("5. Handling Missing Values: Values the model cannot read are returned as null and never guessed. A missing "
             "nutrient contributes nothing to the score and is listed to the user, and low confidence or unreadable "
             "fields produce visible warnings.", "lead"),
           H("4.3 Algorithmic Selection"),
           H("4.3.1 Vision-Language Extraction"),
           P(f"A multimodal LLM of the Gemini family {c('gemini', 'gemapi')} was chosen to read labels because it combines text "
             "recognition, table understanding and structuring in one call, accepts several photographs of the same "
             f"pack and can describe front-of-pack imagery that OCR engines {c('smith')} cannot interpret. The prompt asks for "
             "JSON only and instructs the model to use null for anything unreadable, to return the category from a "
             "fixed list, the ingredients in printed order, nutrition per 100 g and per serving, claims, 'may contain' "
             "statements, the barcode, a confidence value and, from the front of the pack, the foods pictured and the "
             "messages implied. Temperature is set to 0. If a model returns a rate-limit or server error, or exceeds a "
             "20-second time-out, the request is retried on the next model in a fall-back list and the failed model is "
             "skipped for five minutes."),
           H("4.3.2 Rules Engine"),
           P("The rules engine evaluates each member independently and emits flags with a status (SAFE, CAUTION or AVOID), "
             "a reason and the evidence that triggered it. An allergen listed as an ingredient gives AVOID; a 'may "
             "contain' trace, or a generic parent group such as 'nuts' for a cashew allergy, gives CAUTION. Diet rules give "
             "AVOID for forbidden items (onion for a Jain diet) and CAUTION with the note 'source unclear, check with the "
             "brand' for ambiguous ones such as E471 or natural flavours. Condition rules use per-100 g traffic-light "
             f"levels {c('ukdh')}: for diabetes or pre-diabetes, sugar above 22.5 g is AVOID and above 5 g is CAUTION, and fast-acting "
             "sugars such as maltodextrin are flagged; for hypertension, sodium above 600 mg is AVOID and above 300 mg is "
             "CAUTION; lactose intolerance flags milk solids, whey and cream but not ghee. Personal limits flag a serving "
             "that uses at least 40% of a daily sugar limit or 30% of a daily sodium limit, and children receive extra "
             f"checks for colours linked to hyperactivity {c('mccann')}, caffeine and sweeteners. The status of a member is the "
             "most severe of the flags."),
           H("4.3.3 Health Score"),
           P("A transparent score from 0 to 100 starts at 100, subtracts capped penalties for sugar, sodium, saturated "
             "fat, energy density, additive concern and processing level, and adds capped bonuses for fibre and protein "
             f"(Table 2). The thresholds follow the UK traffic-light levels {c('ukdh')}, the WHO guidance {c('who_sugar', 'who_sodium')} and "
             f"a NOVA-style estimate of processing {c('monteiro')}; drinks use stricter sugar and saturated-fat scales. Scores of "
             "70-100 are labelled 'Good choice', 50-69 'Okay occasionally' and below 50 'Limit this'. Because the formula "
             "is plain arithmetic, the same input always gives the same score."),
           H("4.3.4 Claim Checker and Front-versus-Back Check"),
           P(f"Claims are compared with FSSAI-style thresholds {c('fssai_claims')}: 'sugar free' needs at most 0.5 g sugar per 100 g, "
             "'low sugar' at most 5 g (2.5 g for drinks), 'low sodium' at most 120 mg, 'high fibre' at least 6 g and "
             "'high protein' at least 20% of energy; 'no added sugar' fails if any sugar alias is listed, and "
             "'multigrain' or 'whole wheat' fails if the first ingredient is refined flour. For the front of the pack, "
             "the vision call lists the foods pictured and the messages implied. Each pictured food is looked up in the "
             "ingredient list and is judged misleading if it is absent, below 5% of the product, or below 15% when the "
             "product is named after it. Messages such as 'for kids', 'natural', 'no preservatives' or 'energy' are "
             "checked against colours, flavourings, preservatives, sugar and the score."),
           H("4.3.5 Alternatives, Tracking and Weekly Report"),
           P(f"Candidates of the same category from Open Food Facts {c('off')} and the local table are scored with the same formula "
             "and evaluated with the same rules; candidates that are AVOID for any selected member, or that do not beat the "
             "scanned score, are removed. Ranking uses the score, an adjustment from stored thumbs-up and thumbs-down "
             "reasons, and a penalty for members with CAUTION, and a swap impact estimates the sugar or sodium saved per "
             "week. Logged intake is summed per member against weekly budgets (daily limit × 7). The weekly report is composed "
             "in two steps: all numbers are computed in Python, and the LLM only turns them into a headline, a summary and "
             "tips, with a template used if the model is unavailable.")]

    # Table 2
    st.append(cap_t(2, "Algorithmic Formulas"))
    f_rows = [["Algorithms", "Formulae", "Definitions"],
              ["Health score", "S = clamp(100 − ΣP + ΣB, 0, 100)<br/>P(sugar) = min(35, 0.875·gs)<br/>P(sodium) = min(25, 0.025·m)<br/>P(sat) = min(20, 2·gf)<br/>P(energy) = min(10, max(0, (E − 250)/30))<br/>P(add) = min(15, Σw)<br/>B(fibre) = min(8, 1.6·gb)<br/>B(prot) = min(7, 0.7·gp)",
               "S: score; P: penalties; B: bonuses; gs: sugar (g/100 g); m: sodium (mg/100 g); gf: saturated fat; gb: fibre; gp: protein; E: energy (kcal); w: additive weight (high 5, medium 2, low 0.5); a processing penalty of 0, 5 or 10 is also subtracted; drinks use 3.5·gs, 4·gf and (E − 40)/8"],
              ["Derived values", "N100 = Nserv · 100 / G ;  Na = 400 · salt",
               "Nserv: value per serving; N100: value per 100 g; G: serving size (g); Na: sodium (mg); salt in g"],
              ["Personal limit", "U = (N100 · G / 100) / L × 100",
               "U: % of daily limit used by one serving; L: daily limit; CAUTION if U ≥ 40 (sugar) or ≥ 30 (sodium)"],
              ["Pictured food", "misleading if p = 0, p < 5, or (named and p < 15)",
               "p: % of the pictured food in the ingredient list; named: product name contains the food"],
              ["Alternative rank", "R = Sc + Afb − 3·nw<br/>Afb = clamp(8v − 10d − min(15, 0.3·n·gs), −30, 20)",
               "Sc: candidate score; nw: members with CAUTION; v: net votes on the product; d: 1 if brand disliked; n: 'too sweet' votes"],
              ["Swap impact", "ΔN = (Nb − Nc) · W / 100",
               "Nb, Nc: nutrient per 100 g of base and candidate; W: grams eaten per week"]]
    st.append(table(f_rows, [58, 168, 198], left_cols=(0, 1, 2), cell_style="cellf"))
    st.append(Spacer(1, 6))

    # 4.4 architecture
    st += [H("4.4 System Architecture"),
           P("LabelGuard is a three-tier web application (Fig 1). A React single-page application with twelve pages (scan, "
             "alternatives, compare, explorer, decoder, tracker, weekly report, insights, shopping list, allergy cards, "
             "profile and about) talks over JSON to a FastAPI backend exposing "
             f"{R['n_endpoints']} documented endpoints. The backend has four engines: an LLM layer that wraps the Gemini API, the "
             "deterministic rules engine, the alternatives engine and the tracker and report module. Persistent state is "
             "kept in a single SQLite file with nine tables (household, scans, intake logs, feedback, shopping list, "
             "extraction cache, LLM cache, Open Food Facts cache and an LLM call log), and the knowledge tables are "
             "versioned CSV and JSON files. The LLM is used for three core tasks (profile parsing, label extraction and a "
             "short family summary in English, Hindi or Tamil) and two optional ones (answering a typed question about a "
             "product and writing the weekly report); every output is cached and each task has a deterministic fall-back, "
             "namely a keyword parser, manual or barcode entry, template text and rule-based answers."),
           architecture(),
           Paragraph("<b>Fig 1:</b> Architectural flow of the proposed system", S["cap_f"]),
           P("The backend is written in Python 3.11 or later with FastAPI, Pydantic v2, Pillow, the google-genai SDK and "
             f"SQLite; the frontend uses React 18, Vite, Tailwind CSS and Recharts. The code base has about {R['loc_py']:,} lines of "
             f"Python and {R['loc_js']:,} lines of JavaScript, with {R['n_tests']} automated tests. The system was developed and run on an ordinary "
             "Windows laptop and needs only an Internet connection for the Gemini and Open Food Facts services.")]

    # ---- 5. Results
    E = R["extract"]
    st += [H("5. Results"),
           H("5.1 Experimental Setup"),
           P(f"The system was evaluated on {R['n_images']} test labels generated from the Indian product table (biscuits, snacks, noodles, "
             "cereals, chocolate, soft drink, juice, bread, jam and a malted drink) and rendered as images with different fonts, "
             "layouts and backgrounds. For ingredients and nutrition values the ground truth is exactly what is printed. The "
             "ground truth for hidden sugars and allergens is obtained by applying the rules engine to the true ingredient "
             "list, so the evaluation isolates the perception stage: does the extracted text lead to the same flags? Each "
             "image was read three times unchanged (to measure run-to-run variation) and once under each of three "
             "degradations created with Pillow: Gaussian blur (radius 2.5), rotation by 15 degrees and brightness reduced to "
             f"35% (low light). Extraction used {R['model']} with automatic fall-back. The results of each experiment were "
             "analysed according to the following metrics (see Table 3):"),
           *bullets([
               "Ingredient F1: fuzzy match (ratio ≥ 0.85, percentages and brackets ignored) between extracted and true ingredients.",
               "Precision and Recall: of the hidden-sugar names and allergen groups found, how many are correct, and how many true ones are found.",
               "Nutrition accuracy: the share of printed nutrition values read within 2% (or 0.1 absolute) of the truth.",
               "Score error and score consistency: the absolute difference between the score computed from the extraction and from the truth, and the standard deviation of scores over repeated runs."]),
           cap_t(3, "Performance Metrics"),
           table([["S.no", "Metrics", "Formula"],
                  ["1", "Precision (P)", "P = TP / (TP + FP)"],
                  ["2", "Recall (R)", "R = TP / (TP + FN)"],
                  ["3", "F1-Score", "F1 = 2 × P × R / (P + R)"],
                  ["4", "Nutrition accuracy", "A = correct values / printed values"],
                  ["5", "Score standard deviation", "σ = sqrt( Σ(s(i) − mean)² / n )"]],
                 [34, 150, 240]),
           P("TP – True Positives, FP – False Positives, FN – False Negatives, s(i) – score of run i, n – number of runs.", "flat"),
           H("5.2 Extraction Accuracy"),
           P("Table 4 reports the extraction results for the clean images and the three degraded conditions. "
             f"On clean images the model read the ingredient lists with an F1 of {E['clean']['ing_f1']:.2f} and the printed nutrition values with "
             f"{E['clean']['nut_acc']:.0%} accuracy; hidden-sugar precision and recall were {E['clean']['sugar_p']:.2f} and {E['clean']['sugar_r']:.2f}, and allergen precision and "
             f"recall were {E['clean']['all_p']:.2f} and {E['clean']['all_r']:.2f}. {R['degrade_text']}"),
           cap_t(4, "Performance Metrics Evaluation of Label Extraction"),
           table([["Condition", "Ingredient F1", "Sugar P / R", "Allergen P / R", "Nutrition acc.", "Score error", "n"]] +
                 [[lab, f"{E[k]['ing_f1']:.2f}", f"{E[k]['sugar_p']:.2f} / {E[k]['sugar_r']:.2f}",
                   f"{E[k]['all_p']:.2f} / {E[k]['all_r']:.2f}", f"{E[k]['nut_acc']:.0%}", f"{E[k]['score_err']:.1f}", str(E[k]['n'])]
                  for k, lab in (("clean", "Clean"), ("blur", "Blur"), ("rotate", "Rotation 15°"), ("low_light", "Low light"))],
                 [70, 62, 68, 74, 64, 54, 32]),
           P(f"Repeating the same clean image three times gave {R['repeat']['identical']} of {R['n_images']} images with an identical score in all runs "
             f"(mean score standard deviation {R['repeat']['sd']:.2f} points, mean ingredient-set Jaccard {R['repeat']['jaccard']:.2f}). Because the rules "
             "engine is deterministic, any remaining variation comes only from the reading of the image, and the image-hash cache removes "
             "it completely for a photograph that has been read before; in all runs the rules gave an identical analysis for an identical extraction "
             f"({R['repeat']['rules_identical']}).", "body"),
           H("5.3 Consistency Compared with a Plain LLM"),
           P(f"To test whether a plain chatbot can replace the rules, the same model ({R['model']}) was asked, with a plain prompt, to rate the "
             f"healthiness of {ch['n_products']} of the test products from 0 to 100 given their ingredients and nutrition, {ch['runs']} times each, "
             "at the default chat temperature of 1.0 and at temperature 0. LabelGuard's score for the same inputs is a fixed function. "
             f"Table 5 and Fig 2 show that the plain LLM was largely but not perfectly repeatable: the mean standard deviation was {ch['t1_sd']:.1f} points at temperature 1.0 "
             f"and {ch['t0_sd']:.1f} points at temperature 0, with {changed1} of {ch['n_products']} products receiving different scores in different runs at temperature 1.0 "
             f"and {changed0} of {ch['n_products']} even at temperature 0 (average range {ch['t1_range']:.1f} and {ch['t0_range']:.1f} points). The variation is small because the model "
             "answers on a coarse scale, mostly in steps of five, so the practical weakness is less the variance than the calibration and the lack of "
             f"traceability. The average plain-LLM score correlated with the LabelGuard score (Pearson r = {ch['t1_r']:.2f}), so the model broadly agrees about "
             "which foods are healthier, but it rated every product far lower than the documented formula (for example 5 against 50 for a cola and "
             "35 against 80 for white bread), it cannot show how a number was obtained, and it knows nothing about the family. Neither scale is a clinical "
             "standard; the difference is that the LabelGuard number can be recomputed exactly and explained component by component (Section 4.3.3)."),
           cap_t(5, "Comparative Analysis of Score Consistency"),
           table([["Method", "Mean SD (points)", "Mean range", "Identical every run", "Pearson r"],
                  ["Plain LLM, temperature 1.0", f"{R['chat']['t1_sd']:.1f}", f"{R['chat']['t1_range']:.1f}", R['chat']['t1_ident'], f"{R['chat']['t1_r']:.2f}"],
                  ["Plain LLM, temperature 0", f"{R['chat']['t0_sd']:.1f}", f"{R['chat']['t0_range']:.1f}", R['chat']['t0_ident'], f"{R['chat']['t0_r']:.2f}"],
                  ["<b>LabelGuard (rules)</b>", "<b>0.0</b>", "<b>0.0</b>", f"<b>{R['chat']['n_products']}/{R['chat']['n_products']}</b>", "<b>1.00</b>"]],
                 [140, 70, 62, 84, 68]),
           Spacer(1, 4),
           consistency_chart(),
           Paragraph("<b>Fig 2:</b> Score variation across repeated runs: plain LLM versus LabelGuard", S["cap_f"]),
           H("5.4 Profile Parsing"),
           P(f"Ten free-text household descriptions with expected structured output were used to compare the keyword fall-back parser and the Gemini parser "
             f"(Table 6). Accuracy is counted per field (member found, allergens, diet rules and conditions). {R['profile']['text']}"),
           cap_t(6, "Field-Level Accuracy of Profile Parsing"),
           table([["Parser", "Correct fields", "Field accuracy"],
                  ["Keyword fall-back (no LLM)", R['profile']['kw_fields'], R['profile']['kw_acc']],
                  ["Gemini parser", R['profile']['llm_fields'], R['profile']['llm_acc']]],
                 [190, 120, 114]),
           H("5.5 Resource Use and Software Testing"),
           P("Table 7 lists the measured token use and latency of each LLM task during development use of the application (successful calls only). "
             "A new label costs about two thousand input tokens, while repeated photographs, barcode look-ups and all analysis modules cost none. "
             f"All {R['n_tests']} automated tests, covering the rules, scoring, claim checks, API behaviour, caching and error handling, pass."),
           cap_t(7, "Measured Token Use and Latency per LLM Task"),
           table([["LLM task", "Successful / total calls", "Avg input tokens", "Avg output tokens", "Avg latency (s)"]] +
                 [[t["task"], f"{t['ok']} / {t['calls']}", str(t["in"]), str(t["out"]), f"{t['sec']:.1f}"] for t in R["usage"]],
                 [140, 80, 70, 70, 64]),
           H("5.6 System Output"),
           P("Fig 3 and Fig 4 show the output for a made-up mango drink whose front claims 'real mango', '100% natural', "
             "'no preservatives' and 'energy for active kids'. The verdict is 'Limit this' (44/100), and the front-versus-back check "
             "finds all seven front promises contradicted: mango pulp is only 8% (after water and sugar), sodium benzoate is a "
             "preservative, Sunset Yellow (INS 110) is a synthetic colour linked to hyperactivity in children, and the drink has "
             "15.8 g of sugar per 100 ml. The same product is AVOID for two members and CAUTION for the other two."),
           figure("fig_front_back.png", 3, "Front versus back of pack check", width_in=4.0, max_h_in=3.5),
           figure("fig_family.png", 4, "Per-member verdicts for the same product", width_in=4.5),
           P(R["discussion"])]

    # ---- 6. Conclusion
    st += [H("6. Conclusion"),
           P("This study set out to build a label analysis system for Indian households that is personal, repeatable and inexpensive, "
             "and to test whether dividing the work between a multimodal LLM and a deterministic rules engine achieves this. "
             f"The language model read the test labels with an ingredient F1 of {E['clean']['ing_f1']:.2f} and {E['clean']['nut_acc']:.0%} nutrition accuracy on clean images, "
             f"and the rules engine, which gives the same output for the same input, produced hidden-sugar and allergen flags with precision "
             f"{E['clean']['sugar_p']:.2f} and {E['clean']['all_p']:.2f} and recall {E['clean']['sugar_r']:.2f} and {E['clean']['all_r']:.2f}. A plain LLM asked to score the same products was close to repeatable but not exact "
             f"({ch['t1_sd']:.1f} points standard deviation, {changed1} of {ch['n_products']} products changed), used a very different and unexplained scale and could not use the family "
             "profile, whereas LabelGuard's score never changed and can be explained component by component."),
           P("It follows that the language model is best used for what it does well, reading messy photographs and wording explanations, while "
             "every verdict, score and recommendation should come from transparent rules and real databases. Caching, an automatic model fall-back "
             "and template fall-backs kept the service available even when the newest model was overloaded, and barcode, manual and demo modes work "
             "with no LLM at all. Limitations are the clean synthetic test images, the small test set, keyword-based ingredient matching, approximate "
             "values in the local product table and a score that is a transparent heuristic rather than a clinically validated index. Future work "
             "includes live barcode scanning, a fully translated Hindi and Tamil interface, regional-language label reading, a dietitian review of the "
             "thresholds, a larger evaluation with real photographs and a study with real families."),
           H("Acknowledgement"),
           P("The authors thank the School of Computer Science and Engineering, Vellore Institute of Technology, for the facilities and "
             "guidance for this course project, and the Open Food Facts contributors for the open data used.")]

    # ---- References (numbered in order of first citation)
    refs = [Paragraph(f"{i}. {REFS[k]}", S["ref"]) for i, k in enumerate(_order, 1)]
    st += [KeepTogether([H("References")] + refs[:3])] + refs[3:]

    story = []
    is_h = lambda f: isinstance(f, Paragraph) and f.style.name == "h"  # noqa: E731
    for idx, f in enumerate(st):
        if is_h(f):
            nxt = st[idx + 1] if idx + 1 < len(st) else None
            # a heading directly followed by another heading needs room for both plus some text
            story.append(CondPageBreak((1.5 if (nxt is not None and is_h(nxt)) else 0.95) * inch))
        elif isinstance(f, Paragraph) and f.style.name == "cap_t":
            story.append(CondPageBreak(1.3 * inch))
        story.append(f)
    st = story

    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=1.3 * inch, rightMargin=1.3 * inch,
                            topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                            title="LabelGuard: A Hybrid Vision-Language and Rule-Based Approach for Personalised Food-Label Analysis",
                            author=", ".join(n for n, _, _ in STUDENTS))
    doc.build(st)
    return OUT


if __name__ == "__main__":
    print("Wrote", build())
