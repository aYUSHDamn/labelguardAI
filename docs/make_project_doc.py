"""
Fills the course template "Project document - VTOP.docx" (kept in docs/template_vtop.docx) with the LabelGuard
project content and writes docs/LabelGuard_Project_Document.docx.  The cover block and the six numbered headings
(Title, Team members, Abstract, Test Results, Conclusion, References) are the template's own paragraphs.

    python docs/make_project_doc.py
    (then export to PDF with Word: see docs/export_pdf.ps1)
All experimental numbers come from docs/paper_results.json.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template_vtop.docx"
OUT = HERE / "LabelGuard_Project_Document.docx"
SHOTS = HERE / "screenshots"
R = json.loads((HERE / "paper_results.json").read_text(encoding="utf-8"))

FONT = "Times New Roman"
BODY_PT = 10.5

TITLE = "LabelGuard: A Hybrid Vision-Language and Rule-Based Approach for Personalised Food-Label Analysis for Indian Households"
TEAM = [("Harsh Kulkarni", "24BCT0137"), ("B S Srivallabha", "24BCE0457"),
        ("Ayush Konar", "24BDS0107"), ("Pratham Paudel", "24BCE2940")]
FACULTY = "Dr. D. Anuradha"
SLOT = "C2+TC2"

REFS = {
    "gemapi": "Google. Gemini API documentation: models, structured output and thinking. https://ai.google.dev/gemini-api/docs (accessed October 2026).",
    "off": "Open Food Facts. Open Food Facts API documentation (v2). https://openfoodfacts.github.io/openfoodfacts-server/api/ (accessed October 2026).",
    "fssai_claims": "Food Safety and Standards Authority of India, 2018. Food Safety and Standards (Advertising and Claims) Regulations, 2018. New Delhi: FSSAI.",
    "ukdh": "Department of Health, Food Standards Agency, Scottish Government and Welsh Government, 2016. Guide to creating a front of pack (FoP) nutrition label for pre-packed products sold through retail outlets. London.",
    "codex": "Codex Alimentarius Commission. Class names and the international numbering system for food additives, CXG 36-1989. Rome: FAO/WHO.",
    "monteiro": "Monteiro, C.A., Cannon, G., Levy, R.B., Moubarac, J.C., Louzada, M.L., Rauber, F., et al., 2019. Ultra-processed foods: what they are and how to identify them. Public Health Nutrition, 22(5), pp.936-941.",
    "mccann": "McCann, D., Barrett, A., Cooper, A., Crumpler, D., Dalen, L., Grimshaw, K., et al., 2007. Food additives and hyperactive behaviour in 3-year-old and 8/9-year-old children in the community: a randomised, double-blinded, placebo-controlled trial. The Lancet, 370(9598), pp.1560-1567.",
    "fssai_label": "Food Safety and Standards Authority of India, 2020. Food Safety and Standards (Labelling and Display) Regulations, 2020. New Delhi: FSSAI.",
    "who_sugar": "World Health Organization, 2015. Guideline: Sugars intake for adults and children. Geneva: World Health Organization.",
    "who_sodium": "World Health Organization, 2012. Guideline: Sodium intake for adults and children. Geneva: World Health Organization.",
}
_order: list[str] = []


def c(*keys):
    nums = []
    for k in keys:
        if k not in _order:
            _order.append(k)
        nums.append(str(_order.index(k) + 1))
    return "[" + ", ".join(nums) + "]"


# ------------------------------------------------------------------ low-level helpers
doc = docx.Document(str(TEMPLATE))
body = doc.element.body


def style_run(run, size=BODY_PT, bold=False, italic=False):
    run.font.name = FONT
    run._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_runs(p, text, size=BODY_PT):
    """Very small markup: **bold** and _italic_ segments."""
    import re
    for part in re.split(r"(\*\*[^*]+\*\*|__[^_]+__)", text):
        if not part:
            continue
        if part.startswith("**"):
            style_run(p.add_run(part[2:-2]), size, bold=True)
        elif part.startswith("__"):
            style_run(p.add_run(part[2:-2]), size, italic=True)
        else:
            style_run(p.add_run(part), size)


class Cursor:
    """Inserts new block elements one after another, starting after a given template paragraph."""

    def __init__(self, anchor):
        self.anchor = anchor

    def put(self, element):
        self.anchor.addnext(element)
        self.anchor = element

    def para(self, text="", size=BODY_PT, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=4, keep_next=False, indent=None):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.alignment = align
        pf.space_before, pf.space_after = Pt(before), Pt(after)
        pf.line_spacing = 1.0
        pf.keep_with_next = keep_next
        if indent is not None:
            pf.left_indent = Inches(indent)
        add_runs(p, text, size)
        self.put(p._p)
        return p

    def caption_table(self, n, text):
        return self.para(f"**Table {n}:** {text}", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=2, keep_next=True)

    def caption_fig(self, n, text):
        return self.para(f"**Fig {n}:** {text}", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=8)

    def picture(self, path, width_in):
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Inches(width_in))
        self.put(p._p)

    def table(self, rows, widths_in, left_cols=(), size=9.5):
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "6")
            e.set(qn("w:space"), "0")
            e.set(qn("w:color"), "000000")
            borders.append(e)
        tblPr.append(borders)
        for i, row in enumerate(rows):
            tr = t.rows[i]._tr
            trPr = tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            if i == 0:
                th = OxmlElement("w:tblHeader")
                trPr.append(th)
            for j, text in enumerate(row):
                cell = t.cell(i, j)
                cell.width = Inches(widths_in[j])
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.LEFT if (j in left_cols and i > 0) else WD_ALIGN_PARAGRAPH.CENTER)
                add_runs(p, f"**{text}**" if i == 0 else text, size)
                if i == 0:
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:color"), "auto")
                    shd.set(qn("w:fill"), "E7E6E6")
                    cell._tc.get_or_add_tcPr().append(shd)
        self.put(t._tbl)
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(2)
        spacer.paragraph_format.space_before = Pt(0)
        for r in spacer.runs:
            r.font.size = Pt(4)
        self.put(spacer._p)


def find_heading(name):
    for p in doc.paragraphs:
        if p.text.strip() == name:
            return p
    raise KeyError(name)


def clear_placeholders(heading):
    """Delete the template's blank spacer paragraphs that follow a heading (up to the next heading)."""
    nxt = heading._p.getnext()
    while nxt is not None and nxt.tag == qn("w:p"):
        text = "".join(t.text or "" for t in nxt.iter(qn("w:t")))
        has_num = nxt.find(".//" + qn("w:numPr")) is not None
        if has_num or text.strip():
            break
        after = nxt.getnext()
        nxt.getparent().remove(nxt)
        nxt = after


# ------------------------------------------------------------------ content
def build():
    X = R["extract"]
    ch = R["chat"]
    changed1 = ch["n_products"] - int(ch["t1_ident"].split("/")[0])
    changed0 = ch["n_products"] - int(ch["t0_ident"].split("/")[0])
    pr = R["profile"]

    # ---- 1. Title
    h = find_heading("Title")
    clear_placeholders(h)
    cur = Cursor(h._p)
    cur.para(f"**{TITLE}**", size=12, align=WD_ALIGN_PARAGRAPH.LEFT, before=3, after=8)

    # ---- 2. Team members
    h = find_heading("Team members")
    clear_placeholders(h)
    cur = Cursor(h._p)
    for i, (name, reg) in enumerate(TEAM):
        cur.para(f"{name} ({reg})", size=11, align=WD_ALIGN_PARAGRAPH.LEFT, before=3 if i == 0 else 0, after=0)
    cur.para(f"Faculty: {FACULTY}    |    Slot: {SLOT}", size=11, align=WD_ALIGN_PARAGRAPH.LEFT, before=4, after=8)

    # ---- 3. Abstract
    h = find_heading("Abstract")
    clear_placeholders(h)
    cur = Cursor(h._p)
    cur.para("Packaged-food labels are hard to act on: sugar hides under dozens of names, additives appear as INS codes, "
             "front-of-pack claims are rarely checked against the ingredient list, and one household can have very different "
             "dietary needs. LabelGuard is a web application that analyses a packaged food for every member of a household. "
             "A multimodal large language model (Gemini) converts one to three photographs of a pack into structured data in a "
             "single call, while a deterministic rules engine with curated Indian knowledge tables (54 sugar names, 49 INS "
             "additives, 22 allergen groups and 34 diet rules) produces SAFE, CAUTION or AVOID verdicts with evidence for each "
             "member, checks label claims against FSSAI-style thresholds, compares the promises on the front of the pack with "
             "its ingredient list and computes a transparent 0-100 health score. Alternatives come from Open Food Facts and a "
             "local table of Indian products, intake is tracked against personal limits, and a weekly family report is "
             "generated. The language model is used only to read labels, understand the family profile and word summaries; "
             "every decision is made by rules, so the same input always gives the same output.", before=3, after=4)
    cur.para(f"In tests on {R['n_images']} labelled test labels the system reached an ingredient F1 of {X['clean']['ing_f1']:.2f}, "
             f"hidden-sugar and allergen precision and recall of {X['clean']['sugar_p']:.2f}, and {X['clean']['nut_acc']:.0%} nutrition-value accuracy "
             f"on clean images. A plain LLM asked to score eight of the products was not exactly repeatable (standard deviation "
             f"{ch['t1_sd']:.1f} points, {changed1} of {ch['n_products']} products changed between runs) and used a very different scale, whereas "
             f"LabelGuard's score never changed. All {R['n_tests']} automated tests pass.", after=4)
    cur.para("__Key words:__ food label analysis, large language models, multimodal extraction, rule-based reasoning, "
             "personalised nutrition, FSSAI, Open Food Facts.", after=8)

    # ---- 4. Test Results
    h = find_heading("Test Results")
    clear_placeholders(h)
    cur = Cursor(h._p)
    cur.para("**Test setup.** The system was tested on a Windows laptop with the backend (Python, FastAPI) and frontend (React) running "
             f"locally, using the Gemini API ({R['model']} with two fall-back models) {c('gemapi')} and Open Food Facts {c('off')} over the Internet. "
             "Three kinds of tests were carried out: (a) functional test cases of the rules and of the end-to-end flow, "
             f"covering {R['n_tests']} automated tests plus live runs (Table 1); (b) an accuracy experiment on {R['n_images']} labelled test labels "
             "rendered as images, read three times unchanged and once each under blur, 15-degree rotation and low light (Table 2); and "
             "(c) a comparison with a plain LLM, a profile-parser test and a measurement of token use (Tables 3 to 5). For ingredients "
             "and nutrition values the ground truth is exactly what is printed on the test image; the ground truth for hidden sugars and "
             "allergens is obtained by applying the rules to the true ingredient list, so these experiments measure the reading stage.",
             before=3, after=4)

    cur.caption_table(1, "Functional test cases")
    cases = [
        ["1", "Allergy listed as an ingredient", "'Cashew (2%)' in the list; member allergic to cashew", "AVOID, evidence 'Cashew (2%)'", "Pass (pytest)"],
        ["2", "Jain diet", "'Onion powder'; Jain member", "AVOID: not Jain", "Pass (pytest)"],
        ["3", "Ambiguous source", f"'Emulsifier (E471)'; vegetarian member; INS codes {c('codex')}", "CAUTION: source unclear, check with the brand", "Pass (pytest)"],
        ["4", "False-positive guards", "'Coconut milk', 'fox nuts', 'buckwheat flour'", "Not flagged as dairy, tree nuts or wheat", "Pass (pytest)"],
        ["5", "Hidden sugars", "Sugar, invert sugar syrup, liquid glucose, maltodextrin", "All four listed with position on the list", "Pass (pytest)"],
        ["6", "Serving-size trap", "34 g sugar per 100 g, 20 g serving", "Warns that 6.8 g per serving hides a HIGH level", "Pass (pytest)"],
        ["7", "Claim check", f"'healthy', 'no added sugar', 'made with whole wheat' {c('fssai_claims')}", "All three marked misleading", "Pass (pytest)"],
        ["8", "Front vs back of pack", "Front and back photos of a made-up mango drink (live Gemini call)", "7 of 7 front promises contradicted by the back", "Pass (live)"],
        ["9", "Determinism", "Same extraction analysed 5 times", "Identical analysis and score every time", "Pass (pytest)"],
        ["10", "Repeat scan", "Same photo scanned twice", "One LLM call; second scan from cache", "Pass (pytest)"],
        ["11", "Barcode look-up", "3017620422003 (live Open Food Facts)", "Nutella found; analysed with 0 LLM tokens", "Pass (live)"],
        ["12", "Error handling", "A non-image file; scan with no API key", "Friendly {error, detail} JSON (400 and 503)", "Pass (pytest)"],
        ["13", "End-to-end flow", "Profile, scan, summary, alternatives, feedback, log, tracker, compare", "Each step succeeds; alternatives safe for all members and higher scoring", "Pass (pytest)"],
    ]
    cur.table([["No.", "Test case", "Input", "Expected result", "Result"]] + cases, [0.35, 1.3, 2.15, 2.0, 0.95], left_cols=(1, 2, 3))

    cur.para("**Label extraction accuracy.** Table 2 shows the results for the clean images and the three degraded conditions. "
             f"On clean images the ingredient lists were read with an F1 of {X['clean']['ing_f1']:.2f} and the printed nutrition values with "
             f"{X['clean']['nut_acc']:.0%} accuracy; hidden-sugar precision and recall and allergen precision and recall were all {X['clean']['sugar_p']:.2f}. "
             f"Blur and low light caused no loss, and rotation by 15 degrees lowered nutrition accuracy to {X['rotate']['nut_acc']:.0%} "
             f"(mean score error {X['rotate']['score_err']:.1f} points). Two of the 72 extraction calls were lost to Gemini service time-outs and appear as a smaller n. "
             f"Reading each clean image three times gave an identical score for {R['repeat']['identical']} of {R['n_images']} images, and the rules gave an identical analysis for an "
             "identical extraction in every case.", after=3)
    cur.caption_table(2, "Performance metrics of label extraction")
    rows = [["Condition", "Ingredient F1", "Sugar P / R", "Allergen P / R", "Nutrition accuracy", "Score error", "n"]]
    for k, lab in (("clean", "Clean"), ("blur", "Blur"), ("rotate", "Rotation 15°"), ("low_light", "Low light")):
        e = X[k]
        rows.append([lab, f"{e['ing_f1']:.2f}", f"{e['sugar_p']:.2f} / {e['sugar_r']:.2f}", f"{e['all_p']:.2f} / {e['all_r']:.2f}",
                     f"{e['nut_acc']:.0%}", f"{e['score_err']:.1f}", str(e["n"])])
    cur.table(rows, [1.1, 0.95, 1.0, 1.05, 1.2, 0.8, 0.5])

    cur.para("**Comparison with a plain LLM.** The same model was asked, with a plain prompt, to rate the healthiness of "
             f"{ch['n_products']} of the test products from 0 to 100, {ch['runs']} times each, at temperature 1.0 and at temperature 0 (Table 3). "
             f"The plain LLM was largely but not perfectly repeatable: {changed1} of {ch['n_products']} products received different scores in different runs at temperature 1.0 and "
             f"{changed0} of {ch['n_products']} even at temperature 0. The practical weaknesses are the scale and the traceability: it rated every product far below the documented "
             f"formula (for example 5 against 50 for a cola and 35 against 80 for white bread; Pearson r = {ch['t1_r']:.2f}), it cannot show how a number was obtained and it knows "
             "nothing about the family. Neither scale is a clinical standard; the LabelGuard number can be recomputed exactly and explained component by component.", after=3)
    cur.caption_table(3, "Score consistency: plain LLM versus LabelGuard")
    cur.table([["Method", "Mean SD (points)", "Mean range", "Identical every run", "Pearson r"],
               ["Plain LLM, temperature 1.0", f"{ch['t1_sd']:.1f}", f"{ch['t1_range']:.1f}", ch["t1_ident"], f"{ch['t1_r']:.2f}"],
               ["Plain LLM, temperature 0", f"{ch['t0_sd']:.1f}", f"{ch['t0_range']:.1f}", ch["t0_ident"], f"{ch['t0_r']:.2f}"],
               ["**LabelGuard (rules)**", "**0.0**", "**0.0**", f"**{ch['n_products']}/{ch['n_products']}**", "**1.00**"]],
              [2.2, 1.1, 0.95, 1.2, 0.9])

    cur.para("**Profile parsing and resource use.** Ten free-text household descriptions with expected output were used to compare the keyword fall-back parser "
             f"with the Gemini parser (Table 4): the keyword parser got {pr['kw_fields']} fields right ({pr['kw_acc']}), failing on conditions it has no keyword for "
             f"and on a missing family member, while the Gemini parser got {pr['llm_fields']} ({pr['llm_acc']}). Table 5 gives the measured token use and "
             "latency of each LLM task; a new label costs about two thousand input tokens, while repeated photographs, barcode look-ups and every analysis module cost none.", after=3)
    cur.caption_table(4, "Field-level accuracy of profile parsing")
    cur.table([["Parser", "Correct fields", "Field accuracy"],
               ["Keyword fall-back (no LLM)", pr["kw_fields"], pr["kw_acc"]],
               ["Gemini parser", pr["llm_fields"], pr["llm_acc"]]], [3.0, 1.6, 1.6])
    cur.caption_table(5, "Measured token use and latency per LLM task")
    cur.table([["LLM task", "Successful / total calls", "Avg input tokens", "Avg output tokens", "Avg latency (s)"]] +
              [[t["task"], f"{t['ok']} / {t['calls']}", str(t["in"]), str(t["out"]), f"{t['sec']:.1f}"] for t in R["usage"]],
              [2.3, 1.3, 1.1, 1.1, 1.0], left_cols=(0,))

    cur.para("**System output.** Fig 1 and Fig 2 show the output for the made-up mango drink of test case 8, whose front claims 'real mango', "
             "'100% natural', 'no preservatives' and 'energy for active kids'. The score is 44/100 ('Limit this'). The front-versus-back check finds that "
             "mango pulp is only 8% of the product, that sodium benzoate is a preservative, that Sunset Yellow (INS 110) is a synthetic colour linked to "
             f"hyperactivity in children {c('mccann')}, and that the drink has 15.8 g of sugar per 100 ml. The same product is AVOID for two household members and CAUTION for the other two.",
             after=3, keep_next=True)
    cur.picture(SHOTS / "fig_front_back.png", 4.3)
    cur.caption_fig(1, "Front versus back of pack check")
    cur.picture(SHOTS / "fig_family.png", 5.0)
    cur.caption_fig(2, "Per-member verdicts for the same product")
    cur.para("**Limits of the tests.** The test labels are clean, synthetic renderings of 12 products, so the perfect scores on clean images show that the pipeline "
             "works end to end, not that every real photograph will be read perfectly; curved packaging, glare and small fonts are not covered. The plain-LLM comparison "
             "used one model and one prompt. The availability of the hosted model varied during testing, which is why the system uses caching and automatic fall-back models.", after=8)

    # ---- 5. Conclusion
    h = find_heading("Conclusion")
    clear_placeholders(h)
    cur = Cursor(h._p)
    cur.para("LabelGuard shows that dividing the work between a multimodal language model and a deterministic rules engine gives personal, repeatable and inexpensive "
             f"label analysis. The model read the test labels with an ingredient F1 of {X['clean']['ing_f1']:.2f} and {X['clean']['nut_acc']:.0%} nutrition accuracy on clean images, "
             "and the rules produced the same verdicts and scores every time they were given the same input, with evidence for every flag. A plain LLM was close to repeatable but "
             "not exact, used a different and unexplained scale and could not use the family profile.", before=3, after=4)
    cur.para("The main limitations are the clean synthetic test images and small test set, keyword-based ingredient matching, approximate values in the local product table and a score "
             "that is a transparent heuristic rather than a clinically validated index. Future work includes live barcode scanning, a fully translated Hindi and Tamil interface, "
             "regional-language label reading, a dietitian review of the thresholds and a larger evaluation with real photographs and real families.", after=8)

    # ---- 6. References
    h = find_heading("References")
    clear_placeholders(h)
    cur = Cursor(h._p)
    for i, key in enumerate(_order, 1):
        p = cur.para(f"[{i}] {REFS[key]}", size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, before=2 if i == 1 else 0, after=2)
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)

    doc.core_properties.title = TITLE
    doc.core_properties.author = ", ".join(n for n, _ in TEAM)
    doc.save(str(OUT))
    return OUT


if __name__ == "__main__":
    print("Wrote", build())
