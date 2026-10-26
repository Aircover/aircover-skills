#!/usr/bin/env python3
"""
build_template.py - Regenerate assets/Close_Plan_TEMPLATE.xlsx (V5, four tabs).

Tabs: Summary, Health Score, Action Plan, Stakeholder Map.

The template ships BLANK: labels, styling, widths, dropdowns and formulas only.
No customer content, no vendor name, no example prose. fill_close_plan.py writes
the values in.

The Summary tab is a one-page read of the deal: header facts, the overall score, a
bar per bucket, top risks, the next five actions, key people and the four deal story
questions. Its scores, bars, actions and people are FORMULAS pointing at the other
tabs, so an AE who changes a marker, a status or a name sees the Summary follow.

The stakeholder axes (seniority, functions, persona roles), the marker and engagement
dropdown options and the Summary row layout are READ FROM config.json rather than
hardcoded here, so the template and the engine cannot drift. `summary_layout` is the
single definition of where each Summary block sits; fill_close_plan.py imports it.

Run:  python build_template.py --out Close_Plan_TEMPLATE.xlsx [--config config.json]
"""
import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# Aircover palette (aircover-presentation-design).
NAVY = "FF1B2A4A"
TEAL = "FF2CB5AD"
BODY = "FF3D4F6F"
MUTED = "FF7A8CA0"
OFFWHITE = "FFF7F9FB"
TRACK = "FFE8ECF0"
RULE = "FFE2E8F0"
WHITE = "FFFFFFFF"
FONT = "Calibri"

BUCKETS = [
    ("STAKEHOLDER ALIGNMENT", 7, [
        "Champion identified and confirmed (has influence + is actively selling internally)",
        "Economic buyer identified and engaged directly (not just through champion)",
        "All stakeholders/influencers mapped (security, legal, procurement, end users, IT)",
        "Decision criteria documented and agreed by buyer",
        "Decision process and approval chain confirmed (who signs, in what order)",
        "Compelling event / reason to act by target date is explicit",
    ]),
    ("TECHNICAL VALIDATION", 15, [
        "Technical win confirmed (POC/trial success criteria met and documented)",
        "Security review status known (in progress / passed / not started)",
        "Integration requirements scoped and no blockers open",
        "Any outstanding product gaps or feature requests flagged to product team",
    ]),
    ("COMMERCIAL", 21, [
        "Budget confirmed to exist and be allocated for this fiscal period",
        "Pricing/packaging aligned with buyer's expectations",
        "Quote/order form sent and reviewed by buyer",
        "Procurement process started (vendor onboarding, security questionnaires, etc.)",
        "Legal/MSA redlines identified early, not first surfaced at the finish line",
        "Have we established enough value w/ key stakeholders to mitigate potential for discounting?",
    ]),
    ("COMPETITION", 29, [
        "Competitive landscape known (incumbent, alternatives being evaluated)",
        "Differentiation validated with champion, they can repeat it internally",
        "No unaddressed objections tied to a competitor's pitch",
    ]),
    ("TIMELINE & RISK", 34, [
        "Mutual close plan shared with buyer, with dates both sides agreed to",
        'Next step scheduled with a specific date (not "follow up next week")',
        "Key risk(s) to close named explicitly, e.g. budget freeze, exec turnover, competing priority",
        "Backup plan if primary champion goes dark or leaves",
        "Do we have a clear migration or onboarding plan?",
        "Do we have an onboarding owner identified?",
        "Forecast category matches actual deal signals (don't call it Commit if 3+ boxes above are unchecked)",
    ]),
]

STORY_QUESTIONS = [
    ("business_units", "Who are the primary business units using the product?"),
    ("how_using", "How are they using the product today?"),
    ("use_cases", "What is the primary use case vs. what is the secondary use case? "
                  "(use case = what problem are we solving)"),
    ("vendor_impact", "What is the product's impact to the customer's business? "
                      "(cite specific metrics)"),
]

# Header facts: (label, header key) in reading order, two rows of four.
FACTS = [
    [("Amount", "arr"), ("Close date", "close_date"), ("Stage", "forecast"), ("AE", "ae")],
    [("SE", "se"), ("Partner", "partner"), ("CRM", "opp_link")],
]

GAP_QUESTION = ("Open question: Do we have a text relationship with any of "
                "these contacts?")

COVERAGE_BAND = "COVERAGE AND EVIDENCE LIMITS"


def load_config(explicit):
    """Read config.json so the axes below have exactly one definition."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in [explicit,
                 os.path.join(here, "config.json"),
                 os.path.join(os.path.dirname(here), "config.json")]:
        if cand and os.path.exists(cand):
            with open(cand) as f:
                return json.load(f)
    raise SystemExit("No config.json found. Pass --config explicitly.")


def axes(cfg):
    """The lists the template and the engine must agree on, from one place."""
    sm = cfg["stakeholder_map"]
    return {
        "seniority": sm["grid"]["seniority"],
        "functions": sm["grid"]["functions"],
        "personas": sm["personas"]["roles"],
        "status_options": ",".join(cfg["health"]["dropdown"]["options"]),
        "action_status_options": ",".join(cfg["actions"]["status_dropdown"]["options"]),
        "engagement_options": ",".join(
            cfg["stakeholder_map"]["engagement"][k]["text"]
            for k in ("engaged", "emerging", "gap")),
    }


def summary_layout(cfg):
    """Row numbers for every Summary block, derived from config counts.

    One definition, used by this builder and imported by fill_close_plan.py, so a
    change to the number of risks, actions or personas moves every block below it
    in both places at once.
    """
    s = cfg["summary"]
    lay = {"overall": "H3", "facts_rows": [6, 7]}
    r = 9
    lay["readiness_title"] = r
    lay["bucket_rows"] = {k: r + 1 + i for i, k in enumerate(cfg["health"]["buckets"])}
    r += len(cfg["health"]["buckets"]) + 2
    lay["risks_title"] = r
    lay["risk_rows"] = list(range(r + 1, r + 1 + s["risk_count"]))
    r += s["risk_count"] + 2
    lay["actions_title"] = r
    lay["actions_header"] = r + 1
    lay["action_rows"] = list(range(r + 2, r + 2 + s["action_count"]))
    r += s["action_count"] + 3
    lay["people_title"] = r
    lay["people_header"] = r + 1
    n = len(cfg["stakeholder_map"]["personas"]["roles"])
    lay["people_rows"] = list(range(r + 2, r + 2 + n))
    r += n + 3
    lay["story_title"] = r
    lay["story"] = {}
    for i, (key, _) in enumerate(STORY_QUESTIONS):
        lay["story"][key] = (r + 1 + 2 * i, r + 2 + 2 * i)  # (question row, answer row)
    r += 2 * len(STORY_QUESTIONS) + 2
    lay["coverage_row"] = r
    return lay


def expected_cells(cfg):
    """The header and synopsis coordinates config.json must declare for this layout."""
    lay = summary_layout(cfg)
    header = {"customer": "B3"}
    cols = ["C", "E", "G", "I"]
    for row, facts in zip(lay["facts_rows"], FACTS):
        for (label, key), col in zip(facts, cols):
            header[key] = f"{col}{row}"
    synopsis = {k: f"B{a}" for k, (_, a) in lay["story"].items()}
    labels = {f"B{q}" for _, (q, _) in lay["story"].items()}
    return header, synopsis, labels


def font(size=10, bold=False, color=BODY, italic=False):
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic)


def fill(color):
    return PatternFill("solid", fgColor=color)


def underline(ws, row, c0, c1, color=TEAL):
    side = Side(style="thin", color=color)
    for c in range(c0, c1 + 1):
        ws.cell(row=row, column=c).border = Border(bottom=side)


def section(ws, row, text, c0=2, c1=9):
    """Small teal caps heading with a hairline under it."""
    c = ws.cell(row=row, column=c0, value=text)
    c.font = font(10, True, TEAL)
    c.alignment = Alignment(vertical="bottom")
    underline(ws, row, c0, c1, RULE)
    ws.row_dimensions[row].height = 22


def header_band(ws, coord, text, size=10):
    """Navy header cell for a table."""
    c = ws[coord]
    c.value = text
    c.fill = fill(NAVY)
    c.font = font(size, True, WHITE)
    c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)


def page_setup(ws, landscape=False):
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5


def build_summary(wb, cfg):
    ws = wb.active
    ws.title = cfg["template"]["overview_sheet"]
    page_setup(ws)
    for col, w in zip("ABCDEFGHIJ", (2, 13, 15, 13, 15, 13, 15, 12, 18, 2)):
        ws.column_dimensions[col].width = w
    lay = summary_layout(cfg)
    hs = cfg["template"]["health_sheet"]
    aps = cfg["template"]["actions_sheet"]
    sms = cfg["template"]["stakeholder_sheet"]

    # Teal rule across the top, then the title block.
    for c in range(2, 10):
        ws.cell(row=1, column=c).fill = fill(TEAL)
    ws.row_dimensions[1].height = 4

    ws["B2"] = "CLOSE PLAN"
    ws["B2"].font = font(10, True, TEAL)
    ws.merge_cells("H2:I2")
    ws["H2"] = "CLOSE READINESS"
    ws["H2"].font = font(9, True, MUTED)
    ws["H2"].alignment = Alignment(horizontal="right")

    ws.merge_cells("B3:G3")
    ws["B3"].font = font(22, True, NAVY)
    ws["B3"].alignment = Alignment(vertical="center")
    ws.row_dimensions[3].height = 36
    ws.merge_cells("H3:I3")
    ws["H3"] = f"='{hs}'!{cfg['health']['overall_cell']}"
    ws["H3"].number_format = "0%"
    ws["H3"].font = font(28, True, TEAL)
    ws["H3"].alignment = Alignment(horizontal="right", vertical="center")

    ws.merge_cells("H4:I4")
    n_items = sum(len(b["rows"]) for b in cfg["health"]["buckets"].values())
    ws["H4"] = f"share of the {n_items} checklist items"
    ws["H4"].font = font(8, False, MUTED, italic=True)
    ws["H4"].alignment = Alignment(horizontal="right")
    underline(ws, 4, 2, 9, TEAL)

    # Header facts: label cell (muted caps on off-white), value cell (navy).
    cols = [("B", "C"), ("D", "E"), ("F", "G"), ("H", "I")]
    for row, facts in zip(lay["facts_rows"], FACTS):
        for (label, key), (lc, vc) in zip(facts, cols):
            lab = ws[f"{lc}{row}"]
            lab.value = label.upper()
            lab.font = font(8, True, MUTED)
            lab.fill = fill(OFFWHITE)
            lab.alignment = Alignment(vertical="center", indent=1)
            val = ws[f"{vc}{row}"]
            val.font = font(10, True, NAVY)
            val.fill = fill(OFFWHITE)
            val.alignment = Alignment(vertical="center", wrap_text=True, horizontal="left")
        ws.row_dimensions[row].height = 30
    # CRM reference is long, so it takes the rest of its row.
    last_row = lay["facts_rows"][-1]
    ws.merge_cells(f"G{last_row}:I{last_row}")
    for c in ("H", "I"):
        ws[f"{c}{last_row}"].fill = fill(OFFWHITE)

    # Readiness: bucket name, a bar drawn by formula over a grey track, the %, a flag.
    section(ws, lay["readiness_title"], "READINESS BY BUCKET")
    bar_len = cfg["summary"].get("bar_length", 24)
    score_cells = []
    for bkey, row in lay["bucket_rows"].items():
        bspec = cfg["health"]["buckets"][bkey]
        src = f"'{hs}'!{cfg['health']['score_col']}{bspec['header_row']}"
        ws.merge_cells(f"B{row}:C{row}")
        ws[f"B{row}"] = cfg["actions"]["bucket_titles"][bkey]
        ws[f"B{row}"].font = font(10, True, NAVY)
        ws[f"B{row}"].alignment = Alignment(vertical="center")
        ws.merge_cells(f"D{row}:G{row}")
        ws[f"D{row}"] = f'=REPT("█",ROUND({src}*{bar_len},0))'
        ws[f"D{row}"].font = Font(name=FONT, size=10, color=TEAL)
        ws[f"D{row}"].fill = fill(TRACK)
        ws[f"D{row}"].alignment = Alignment(vertical="center")
        ws[f"H{row}"] = f"={src}"
        ws[f"H{row}"].number_format = "0%"
        ws[f"H{row}"].font = font(11, True, NAVY)
        ws[f"H{row}"].alignment = Alignment(horizontal="center", vertical="center")
        score_cells.append(f"H{row}")
        ws.row_dimensions[row].height = 20
    first, last = score_cells[0], score_cells[-1]
    for cell in score_cells:
        row = cell[1:]
        ws[f"I{row}"] = f'=IF({cell}=MIN(${first[0]}${first[1:]}:${last[0]}${last[1:]}),"Weakest","")'
        ws[f"I{row}"].font = font(9, True, "FFD94F4F")
        ws[f"I{row}"].alignment = Alignment(vertical="center")

    # Top risks: written by the engine.
    section(ws, lay["risks_title"], "TOP RISKS")
    for row in lay["risk_rows"]:
        ws.merge_cells(f"B{row}:I{row}")
        ws[f"B{row}"].font = font(10, False, BODY)
        ws[f"B{row}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[row].height = 18

    # Next actions: the engine points each row at an Action Plan row by formula.
    section(ws, lay["actions_title"], "NEXT ACTIONS")
    hr = lay["actions_header"]
    for coord, text in (("B", "#"), ("C", "ACTION"), ("G", "OWNER"), ("I", "STATUS")):
        ws[f"{coord}{hr}"] = text
        ws[f"{coord}{hr}"].font = font(8, True, MUTED)
    ws.merge_cells(f"C{hr}:F{hr}")
    ws.merge_cells(f"G{hr}:H{hr}")
    for i, row in enumerate(lay["action_rows"], start=1):
        ws[f"B{row}"] = i
        ws[f"B{row}"].font = font(11, True, TEAL)
        ws[f"B{row}"].alignment = Alignment(horizontal="center", vertical="top")
        ws.merge_cells(f"C{row}:F{row}")
        ws.merge_cells(f"G{row}:H{row}")
        for c in ("C", "G", "I"):
            ws[f"{c}{row}"].font = font(10, False, BODY)
            ws[f"{c}{row}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"I{row}"].alignment = Alignment(horizontal="center", vertical="top")
        underline(ws, row, 2, 9, RULE)
        ws.row_dimensions[row].height = 30

    # Key people: formulas into the Stakeholder Map persona table.
    section(ws, lay["people_title"], "KEY PEOPLE")
    hr = lay["people_header"]
    for coord, text in (("B", "ROLE"), ("E", "NAME"), ("H", "ENGAGEMENT")):
        ws[f"{coord}{hr}"] = text
        ws[f"{coord}{hr}"].font = font(8, True, MUTED)
    p = cfg["stakeholder_map"]["personas"]
    pc = p["columns"]
    for i, row in enumerate(lay["people_rows"]):
        src = p["first_row"] + i
        ws.merge_cells(f"B{row}:D{row}")
        ws.merge_cells(f"E{row}:G{row}")
        ws.merge_cells(f"H{row}:I{row}")
        ws[f"B{row}"] = f"='{sms}'!{pc['role']}{src}"
        ws[f"B{row}"].font = font(10, True, NAVY)
        ws[f"E{row}"] = f"='{sms}'!{pc['name']}{src}"
        ws[f"E{row}"].font = font(10, False, BODY)
        ws[f"H{row}"] = f"='{sms}'!{pc['engagement']}{src}"
        ws[f"H{row}"].font = font(9, True, BODY)
        ws[f"H{row}"].alignment = Alignment(horizontal="center", vertical="center")
        for c in ("B", "E"):
            ws[f"{c}{row}"].alignment = Alignment(vertical="center")
        underline(ws, row, 2, 9, RULE)
        ws.row_dimensions[row].height = 20

    # Deal story: the four synopsis questions.
    section(ws, lay["story_title"], "DEAL STORY")
    questions = dict(STORY_QUESTIONS)
    for key, (q, a) in lay["story"].items():
        ws.merge_cells(f"B{q}:I{q}")
        ws[f"B{q}"] = questions[key]
        ws[f"B{q}"].font = font(10, True, NAVY)
        ws[f"B{q}"].alignment = Alignment(vertical="bottom", wrap_text=True)
        ws.row_dimensions[q].height = 22
        ws.merge_cells(f"B{a}:I{a}")
        ws[f"B{a}"].font = font(10, False, BODY)
        ws[f"B{a}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[a].height = 18

    # Coverage note mirrors the Health Score block so the limit travels with the score.
    cr = lay["coverage_row"]
    ws.merge_cells(f"B{cr}:I{cr + 1}")
    note = cfg["health"]["coverage_note_cell"]
    ws[f"B{cr}"] = f"=IF('{hs}'!{note}=\"\",\"\",'{hs}'!{note})"
    ws[f"B{cr}"].font = font(8, False, MUTED, italic=True)
    ws[f"B{cr}"].alignment = Alignment(vertical="top", wrap_text=True)
    ws[f"B{cr}"].fill = fill(OFFWHITE)
    ws.row_dimensions[cr].height = 18
    ws.row_dimensions[cr + 1].height = 18
    return ws


def build_health(wb, cfg, ax):
    ws = wb.create_sheet(cfg["template"]["health_sheet"])
    page_setup(ws)
    for col, w in (("A", 16), ("B", 72), ("C", 12)):
        ws.column_dimensions[col].width = w

    ws["A1"] = "Health Score"
    ws["A1"].font = font(18, True, NAVY)
    ws.row_dimensions[1].height = 28

    ws["A3"] = "Overall"
    ws["A3"].font = font(12, True, NAVY)
    hdr_rows = [r for _, r, _ in BUCKETS]
    ws["B3"] = "=AVERAGE(%s)" % ",".join(f"C{r}" for r in hdr_rows)
    ws["B3"].font = font(16, True, TEAL)
    ws["B3"].number_format = "0%"
    ws.row_dimensions[3].height = 24

    ws.merge_cells("A5:C5")
    ws["A5"] = ('Every item scored "No", "In Progress" or "Needs Input" generates a '
                'recommended action on the Action Plan tab. Each item is worth an equal '
                'share of its bucket: Yes = 100%, In Progress = 50%, No and Needs Input = 0%. '
                'Overall = the five bucket scores weighted equally. Change a status from the '
                'dropdown and every score, including the Summary, recalculates.')
    ws["A5"].font = font(9, False, MUTED, italic=True)
    ws["A5"].alignment = Alignment(vertical="top", wrap_text=True)
    ws.row_dimensions[5].height = 40

    marker_cells = []
    for title, hdr, labels in BUCKETS:
        first, last = hdr + 1, hdr + len(labels)
        ws.merge_cells(f"A{hdr}:B{hdr}")
        header_band(ws, f"A{hdr}", title)
        ws.row_dimensions[hdr].height = 20
        c = ws[f"C{hdr}"]
        # Each item is worth 1/(items in bucket). Yes takes the full weight, In Progress
        # takes half, No and Needs Input take none. Needs Input scores zero deliberately:
        # if an unexamined item scored half, a deal nobody had qualified would outscore a
        # deal that was qualified and found wanting.
        # Marker text comes from config.markers, never a literal, or renaming a marker
        # there silently zeroes every score that depends on it.
        # Denominator counts LABELS, not answers. Using COUNTA on the answer column
        # would drop unanswered items from the denominator and inflate the score.
        yes_txt = cfg["markers"]["yes"]["text"]
        part_txt = cfg["markers"]["partial"]["text"]
        c.value = (f'=(COUNTIF(A{first}:A{last},"{yes_txt}")'
                   f'+0.5*COUNTIF(A{first}:A{last},"{part_txt}"))'
                   f'/COUNTA($B${first}:$B${last})')
        c.fill = fill(NAVY)
        c.font = font(11, True, TEAL)
        c.number_format = "0%"
        c.alignment = Alignment(horizontal="center", vertical="center")

        for i, label in enumerate(labels):
            r = first + i
            a = ws[f"A{r}"]
            a.alignment = Alignment(horizontal="center", vertical="center")
            marker_cells.append(f"A{r}")
            b = ws[f"B{r}"]
            b.value = label
            b.font = font(10, False, BODY)
            b.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
            underline(ws, r, 1, 3, RULE)
            ws.row_dimensions[r].height = 18

    dv = DataValidation(type="list", formula1='"%s"' % ax["status_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = " ".join(marker_cells)

    # Coverage note block. Two rows clear of the last item so a bucket range can
    # never swallow it, and merged so the engine's autofit has somewhere to grow.
    last_item = max(hdr + len(labels) for _, hdr, labels in BUCKETS)
    band_row = last_item + 2
    ws.merge_cells(f"A{band_row}:C{band_row}")
    header_band(ws, f"A{band_row}", COVERAGE_BAND, size=9)
    ws.row_dimensions[band_row].height = 18

    note_first = band_row + 1
    ws.merge_cells(f"A{note_first}:C{note_first + 3}")
    c = ws[f"A{note_first}"]
    c.fill = fill(OFFWHITE)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    for r in range(note_first, note_first + 4):
        ws.row_dimensions[r].height = 14.5
    return ws


def build_actions(wb, cfg, ax):
    ws = wb.create_sheet(cfg["template"]["actions_sheet"])
    page_setup(ws, landscape=True)
    for col, w in (("A", 20), ("B", 40), ("C", 58), ("D", 18), ("E", 14), ("F", 42)):
        ws.column_dimensions[col].width = w

    ws["A1"] = "Action Plan"
    ws["A1"].font = font(18, True, NAVY)
    ws.row_dimensions[1].height = 28
    ws["A2"] = "One row per Health Score item that is not a Yes. Filter by owner or status."
    ws["A2"].font = font(9, False, MUTED, italic=True)

    headers = ["Bucket", "Gap (from Health Score)", "Recommended Action",
               "Owner", "Status", "Comments"]
    for i, h in enumerate(headers, start=1):
        header_band(ws, f"{get_column_letter(i)}3", h)
    ws.row_dimensions[3].height = 22
    ws.freeze_panes = "A4"

    dv = DataValidation(type="list", formula1='"%s"' % ax["action_status_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = "E4:E200"
    return ws


def build_stakeholders(wb, cfg, ax):
    ws = wb.create_sheet(cfg["template"]["stakeholder_sheet"])
    page_setup(ws, landscape=True)
    for col, w in (("A", 24), ("B", 20), ("C", 16), ("D", 16),
                   ("E", 16), ("F", 16), ("G", 16)):
        ws.column_dimensions[col].width = w

    ws.merge_cells("A1:G1")
    ws["A1"] = "Stakeholder Map"
    ws["A1"].font = font(18, True, NAVY)
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A3:G3")
    ws["A3"] = "BUYING COMMITTEE: seniority x function"
    ws["A3"].font = font(10, True, TEAL)
    underline(ws, 3, 1, 7, RULE)
    ws.row_dimensions[3].height = 20

    # C-Suite sits above the grid as one full-width band.
    ws["A5"] = "C-Suite"
    ws["A5"].font = font(10, True, NAVY)
    ws["A5"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B5:G5")
    ws["B5"].alignment = Alignment(vertical="top", wrap_text=True)
    ws["B5"].fill = fill(OFFWHITE)
    ws["B5"].font = font(10, False, BODY)
    ws.row_dimensions[5].height = 31.5

    ws["A7"] = "Seniority"
    ws["A7"].font = font(8, True, MUTED)
    for i, fn in enumerate(ax["functions"]):
        c = ws[f"{get_column_letter(2 + i)}7"]
        c.value = fn
        c.font = font(9, True, NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    underline(ws, 7, 2, 1 + len(ax["functions"]), TEAL)
    ws.row_dimensions[7].height = 30

    thin = Side(style="thin", color=WHITE)
    for i, sen in enumerate(ax["seniority"]):
        r = 8 + i
        a = ws[f"A{r}"]
        a.value = sen
        a.font = font(9, True, NAVY)
        a.alignment = Alignment(horizontal="right", vertical="center", indent=1)
        for j in range(len(ax["functions"])):
            c = ws[f"{get_column_letter(2 + j)}{r}"]
            c.fill = fill(OFFWHITE)
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = 30

    # Rows below the grid are DERIVED from the seniority axis, never hardcoded.
    # Add a row to the axis and the legend, unplaced line, and persona table all
    # slide down together instead of the grid overwriting the legend.
    grid_last = 7 + len(ax["seniority"])
    key_row = grid_last + 2
    unplaced_row = key_row + 1
    title_row = unplaced_row + 1
    hdr_row = title_row + 1

    eng = cfg["stakeholder_map"]["engagement"]
    ws[f"A{key_row}"] = "Key"
    ws[f"A{key_row}"].font = font(8, True, MUTED)
    ws[f"A{key_row}"].alignment = Alignment(horizontal="right", vertical="center", indent=1)
    legend = [("B", "Engaged", eng["engaged"]), ("C", "Emerging / not direct", eng["emerging"]),
              ("D", "Not yet mapped", eng["gap"])]
    for col, text, spec in legend:
        c = ws[f"{col}{key_row}"]
        c.value = text
        c.fill = fill(spec["fill"])
        c.font = Font(name=FONT, size=8, bold=True, color=spec["font"])
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[key_row].height = 22

    ws.merge_cells(f"A{unplaced_row}:G{unplaced_row}")
    ws.row_dimensions[unplaced_row].height = 25.5

    ws[f"A{title_row}"] = "KEY PERSONAS"
    ws[f"A{title_row}"].font = font(10, True, TEAL)
    ws[f"A{title_row}"].alignment = Alignment(vertical="bottom")
    ws.row_dimensions[title_row].height = 22

    for col, h in (("A", "Role"), ("B", "Name"), ("C", "Engagement")):
        header_band(ws, f"{col}{hdr_row}", h)
    ws.merge_cells(f"D{hdr_row}:G{hdr_row}")
    header_band(ws, f"D{hdr_row}", "Notes / Gap")
    ws.row_dimensions[hdr_row].height = 22

    for i, role in enumerate(ax["personas"]):
        r = hdr_row + 1 + i
        a = ws[f"A{r}"]
        a.value = role
        a.font = font(9, True, NAVY)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"B{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"B{r}"].font = font(10, False, BODY)
        ws[f"C{r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells(f"D{r}:G{r}")
        ws[f"D{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"D{r}"].font = font(10, False, BODY)
        underline(ws, r, 1, 7, RULE)
        ws.row_dimensions[r].height = 30

    last = hdr_row + len(ax["personas"])
    dv = DataValidation(type="list", formula1='"%s"' % ax["engagement_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = " ".join(f"C{r}" for r in range(hdr_row + 1, last + 1))

    gap = last + 2
    ws.merge_cells(f"A{gap}:G{gap}")
    c = ws[f"A{gap}"]
    c.fill = fill(OFFWHITE)
    c.font = font(10, True, NAVY)
    c.alignment = Alignment(vertical="top", wrap_text=True, indent=1)
    c.value = GAP_QUESTION
    ws.row_dimensions[gap].height = 24
    return ws


def check_config(cfg):
    """Fail if config.json's Summary coordinates disagree with summary_layout."""
    header, synopsis, labels = expected_cells(cfg)
    errs = []
    for key, coord in header.items():
        if cfg["header_cells"].get(key) != coord:
            errs.append(f"header_cells.{key} should be {coord}")
    for key, coord in synopsis.items():
        if cfg["synopsis_cells"].get(key) != coord:
            errs.append(f"synopsis_cells.{key} should be {coord}")
    over = {k for k in (cfg.get("label_overrides") or {}).get("cells", {}) if not k.startswith("_")}
    if over and over != labels:
        errs.append(f"label_overrides.cells should be {sorted(labels)}")
    if errs:
        raise SystemExit("config.json does not match the Summary layout:\n  " + "\n  ".join(errs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Close_Plan_TEMPLATE.xlsx")
    ap.add_argument("--config", default=None)
    a = ap.parse_args()

    cfg = load_config(a.config)
    check_config(cfg)
    ax = axes(cfg)

    wb = Workbook()
    build_summary(wb, cfg)
    build_health(wb, cfg, ax)
    build_actions(wb, cfg, ax)
    build_stakeholders(wb, cfg, ax)
    wb.save(a.out)
    print("wrote", a.out)
    print("  grid axes from config: %d seniority x %d functions, %d personas"
          % (len(ax["seniority"]), len(ax["functions"]), len(ax["personas"])))


if __name__ == "__main__":
    main()
