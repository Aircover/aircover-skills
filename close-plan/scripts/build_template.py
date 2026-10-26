#!/usr/bin/env python3
"""
build_template.py - Regenerate assets/Close_Plan_TEMPLATE.xlsx (V3.1, four tabs).

The template ships BLANK: labels, banding, widths, dropdowns and formulas only.
No customer content, no vendor name, no example prose. fill_close_plan.py writes
the values in.

The stakeholder axes (seniority, functions, persona roles) and the marker and
engagement dropdown options are READ FROM config.json rather than hardcoded here.
That matters: those lists used to live in two places, so retargeting the grid to a
new vendor's buyer set meant editing config and then discovering the template header
still asked about someone else's departments. One source, no drift.

Run:  python build_template.py --out Close_Plan_TEMPLATE.xlsx [--config config.json]
"""
import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ORANGE = "FFFF6C37"
INK = "FF1E1E1E"
GREY_HDR = "FFF2F2F2"
MUTED = "FF666666"
WHITE = "FFFFFFFF"

GREEN = "FFC6EFCE"
AMBER = "FFFFEB9C"
RED = "FFFFC7CE"
NEUTRAL = "FFF2F2F2"

BUCKET_TINT = {
    "Stakeholder Alignment": "FFFDE9DD",
    "Technical Validation": "FFE8F0FE",
    "Commercial": "FFE6F4EA",
    "Competition": "FFFCE8E6",
    "Timeline & Risk": "FFF3E8FD",
}

# (bucket title, header row, [item labels]) - rows follow the header contiguously.
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

OVERVIEW_QUESTIONS = [
    (7, "Who are the primary business units using the product?"),
    (9, "How are they using the product today?"),
    (11, "What is the primary use case vs. what is the secondary use case? "
         "(use case = what problem are we solving)"),
    (13, "What is the product's impact to the customer's business? (cite specific metrics)"),
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


def band(ws, coord, text, fill=ORANGE, color=WHITE, size=12, bold=True):
    c = ws[coord]
    c.value = text
    c.fill = PatternFill("solid", fgColor=fill)
    c.font = Font(name="Calibri", size=size, bold=bold, color=color)
    c.alignment = Alignment(vertical="center", wrap_text=True)


def build_overview(wb):
    ws = wb.active
    ws.title = "Deal Overview"
    for col, w in (("A", 30), ("B", 30), ("C", 18), ("D", 30)):
        ws.column_dimensions[col].width = w

    pairs = [("Close Plan for:", "AE:"), ("CRM:", "SE:"),
             ("Close Date:", "Partner:"), ("Net Incremental ARR", "Deal in Forecast:")]
    for i, (left, right) in enumerate(pairs, start=1):
        for coord, text in ((f"A{i}", left), (f"C{i}", right)):
            c = ws[coord]
            c.value = text
            c.fill = PatternFill("solid", fgColor=GREY_HDR)
            c.font = Font(name="Calibri", size=10, bold=True)

    ws.merge_cells("A6:D6")
    band(ws, "A6", "DEAL SYNOPSIS & OVERVIEW")
    ws.row_dimensions[6].height = 21.75

    for row, label in OVERVIEW_QUESTIONS:
        ws.merge_cells(f"A{row}:D{row}")
        c = ws[f"A{row}"]
        c.value = label
        c.fill = PatternFill("solid", fgColor=GREY_HDR)
        c.font = Font(name="Calibri", size=10, bold=True)
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[row].height = 18

        ws.merge_cells(f"A{row + 1}:D{row + 1}")
        ws[f"A{row + 1}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[row + 1].height = 69.75
    return ws


def build_health(wb, cfg, ax):
    ws = wb.create_sheet("Health Score")
    for col, w in (("A", 16), ("B", 70), ("C", 14)):
        ws.column_dimensions[col].width = w

    ws["A1"] = "HEALTH SCORE"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=INK)

    ws["A3"] = "Overall Close Plan Score"
    ws["A3"].font = Font(name="Calibri", size=12, bold=True)
    hdr_rows = [r for _, r, _ in BUCKETS]
    ws["B3"] = "=AVERAGE(%s)" % ",".join(f"C{r}" for r in hdr_rows)
    ws["B3"].font = Font(name="Calibri", size=12, bold=True)
    ws["B3"].number_format = "0%"

    ws.merge_cells("A5:C5")
    ws["A5"] = ('Key: every item scored "No", "In Progress" or "Needs Input" generates a '
                'recommended action in the Action Plan tab. "Yes" items are validated and get '
                'no bullet there, which keeps this tab scannable. Each item is worth an equal '
                'share of its bucket: Yes = 100%, In Progress = 50%, No and Needs Input = 0%. '
                'Overall = the five bucket scores weighted equally.')
    ws["A5"].font = Font(name="Calibri", size=9, color=MUTED)
    ws["A5"].alignment = Alignment(vertical="top", wrap_text=True)
    ws.row_dimensions[5].height = 41

    marker_cells = []
    for title, hdr, labels in BUCKETS:
        first, last = hdr + 1, hdr + len(labels)
        ws.merge_cells(f"A{hdr}:B{hdr}")
        band(ws, f"A{hdr}", title, fill=INK, size=11)
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
        c.fill = PatternFill("solid", fgColor=INK)
        c.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        c.number_format = "0%"
        c.alignment = Alignment(horizontal="center", vertical="center")

        for i, label in enumerate(labels):
            r = first + i
            a = ws[f"A{r}"]
            a.alignment = Alignment(horizontal="center", vertical="center")
            a.fill = PatternFill("solid", fgColor=NEUTRAL)
            marker_cells.append(f"A{r}")
            b = ws[f"B{r}"]
            b.value = label
            b.alignment = Alignment(vertical="top", wrap_text=True)
            ws.row_dimensions[r].height = 15.75

    dv = DataValidation(type="list", formula1='"%s"' % ax["status_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = " ".join(marker_cells)

    # Coverage note block. Two rows clear of the last item so a bucket range can
    # never swallow it, and merged so the engine's autofit has somewhere to grow.
    last_item = max(hdr + len(labels) for _, hdr, labels in BUCKETS)
    band_row = last_item + 2
    ws.merge_cells(f"A{band_row}:C{band_row}")
    band(ws, f"A{band_row}", COVERAGE_BAND, fill=INK, size=10)
    ws.row_dimensions[band_row].height = 18

    note_first = band_row + 1
    ws.merge_cells(f"A{note_first}:C{note_first + 3}")
    c = ws[f"A{note_first}"]
    c.fill = PatternFill("solid", fgColor=NEUTRAL)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    for r in range(note_first, note_first + 4):
        ws.row_dimensions[r].height = 14.5
    return ws


def build_actions(wb, ax):
    ws = wb.create_sheet("Action Plan")
    for col, w in (("A", 18), ("B", 42), ("C", 60), ("D", 16), ("E", 14), ("F", 42)):
        ws.column_dimensions[col].width = w

    ws.merge_cells("A1:F1")
    ws["A1"] = "ACTION PLAN: one row per Health Score item that is not a Yes"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=INK)

    headers = ["Bucket", "Gap (from Health Score)", "Recommended Action",
               "Owner", "Status", "Comments"]
    for i, h in enumerate(headers, start=1):
        band(ws, f"{get_column_letter(i)}3", h)
    ws.row_dimensions[3].height = 19.5

    dv = DataValidation(type="list", formula1='"%s"' % ax["action_status_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = "E4:E200"
    return ws


def build_stakeholders(wb, cfg, ax):
    ws = wb.create_sheet("Stakeholder Map")
    for col, w in (("A", 24), ("B", 20), ("C", 16), ("D", 16),
                   ("E", 16), ("F", 16), ("G", 16)):
        ws.column_dimensions[col].width = w

    ws.merge_cells("A1:G1")
    ws["A1"] = "STAKEHOLDER MAP: heat map of persona engagement"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=INK)

    ws.merge_cells("A3:G3")
    ws["A3"] = "Buying Committee Heat Map: seniority x function"
    ws["A3"].font = Font(name="Calibri", size=11, bold=True)
    ws.row_dimensions[3].height = 18

    # C-Suite sits above the grid as one full-width band.
    ws["A5"] = "C-Suite"
    ws["A5"].font = Font(name="Calibri", size=10, bold=True, color=ORANGE)
    ws["A5"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B5:G5")
    ws["B5"].alignment = Alignment(vertical="top", wrap_text=True)
    ws["B5"].fill = PatternFill("solid", fgColor=NEUTRAL)
    ws.row_dimensions[5].height = 31.5

    ws["A7"] = "Seniority"
    ws["A7"].font = Font(name="Calibri", size=9, bold=True)
    for i, fn in enumerate(ax["functions"]):
        c = ws[f"{get_column_letter(2 + i)}7"]
        c.value = fn
        c.font = Font(name="Calibri", size=9, bold=True, color=ORANGE)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[7].height = 27.75

    for i, sen in enumerate(ax["seniority"]):
        r = 8 + i
        a = ws[f"A{r}"]
        a.value = sen
        a.font = Font(name="Calibri", size=10, bold=True, color=ORANGE)
        a.alignment = Alignment(horizontal="center", vertical="center")
        for j in range(len(ax["functions"])):
            c = ws[f"{get_column_letter(2 + j)}{r}"]
            c.fill = PatternFill("solid", fgColor=NEUTRAL)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = 30

    # Rows below the grid are DERIVED from the seniority axis, never hardcoded.
    # With a 4-row axis this reproduces the original 13/14/15/16/17 layout exactly;
    # add a row to the axis and the legend, unplaced line, and persona table all
    # slide down together instead of the grid overwriting the legend.
    grid_last = 7 + len(ax["seniority"])
    key_row = grid_last + 2
    unplaced_row = key_row + 1
    title_row = unplaced_row + 1
    hdr_row = title_row + 1

    ws[f"A{key_row}"] = "Key:"
    ws[f"A{key_row}"].font = Font(name="Calibri", size=9, bold=True)
    legend = [("B", "Engaged", GREEN), ("C", "Emerging / not direct", AMBER),
              ("D", "Not yet mapped", RED)]
    for col, text, fill in legend:
        c = ws[f"{col}{key_row}"]
        c.value = text
        c.fill = PatternFill("solid", fgColor=fill)
        c.font = Font(name="Calibri", size=8)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[key_row].height = 24

    ws.merge_cells(f"A{unplaced_row}:G{unplaced_row}")
    ws.row_dimensions[unplaced_row].height = 25.5

    ws[f"A{title_row}"] = "Key Persona Detail"
    ws[f"A{title_row}"].font = Font(name="Calibri", size=11, bold=True)

    for col, h in (("A", "Role"), ("B", "Name"), ("C", "Engagement")):
        band(ws, f"{col}{hdr_row}", h)
    ws.merge_cells(f"D{hdr_row}:G{hdr_row}")
    band(ws, f"D{hdr_row}", "Notes / Gap")
    ws.row_dimensions[hdr_row].height = 19.5

    for i, role in enumerate(ax["personas"]):
        r = hdr_row + 1 + i
        a = ws[f"A{r}"]
        a.value = role
        a.font = Font(name="Calibri", size=9, bold=True)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"B{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"C{r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"C{r}"].fill = PatternFill("solid", fgColor=NEUTRAL)
        ws.merge_cells(f"D{r}:G{r}")
        ws[f"D{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 39.75

    last = hdr_row + len(ax["personas"])
    dv = DataValidation(type="list", formula1='"%s"' % ax["engagement_options"],
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.sqref = " ".join(f"C{r}" for r in range(hdr_row + 1, last + 1))

    gap = last + 2
    ws.merge_cells(f"A{gap}:G{gap}")
    c = ws[f"A{gap}"]
    c.fill = PatternFill("solid", fgColor=GREY_HDR)
    c.font = Font(name="Calibri", size=10, bold=True)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    c.value = GAP_QUESTION
    ws.row_dimensions[gap].height = 24
    return ws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Close_Plan_TEMPLATE.xlsx")
    ap.add_argument("--config", default=None)
    a = ap.parse_args()

    cfg = load_config(a.config)
    ax = axes(cfg)

    wb = Workbook()
    build_overview(wb)
    build_health(wb, cfg, ax)
    build_actions(wb, ax)
    build_stakeholders(wb, cfg, ax)
    wb.save(a.out)
    print("wrote", a.out)
    print("  grid axes from config: %d seniority x %d functions, %d personas"
          % (len(ax["seniority"]), len(ax["functions"]), len(ax["personas"])))


if __name__ == "__main__":
    main()
