"""Writes the results for BVG staff.

    BVG_Plan_Metadata.csv    clean table, one row per plan, English column names (for importing)
    BVG_Plan_Metadata.xlsx   the same table, formatted in BVG colours, with a column guide (for reading)
    BVG_Plan_Text.csv        all text read on each plan, grouped by area of the plan, with a reading
                             quality in words (for searching any word)

Only the presentation changes here: the values come unchanged from the field rules.
The review notes are split into two kinds:
    Needs Review / Review Notes   a value WAS found but may be wrong -> a person should check it
    Missing Fields                nothing was found -> the cell is empty, there is nothing to check
If the file resources/bvg_logo.png exists, the logo is placed in the Excel file.
"""
from datetime import date

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import settings

# --- BVG colours -----------------------------------------------------------------
BVG_YELLOW = "F0D722"
BVG_DARK = "252424"
REVIEW_FILL = "FCF5C7"     # pale yellow for rows that should be checked by a person
LINE = "D0D0D0"     # light grey lines between rows and columns

LOGO = settings.PACKAGE_DIR / "resources" / "bvg_logo.png"

# --- Columns: internal name, English name, width in Excel, wrap text, meaning -------------
COLUMNS = [
    ("file_name", "File Name", 34, True,
     "Name of the plan file in the input folder (with its subfolder, if it is in one)."),
    ("station", "Station (Current Name)", 22, True,
     "Current name of the U-Bahn station the plan belongs to. Empty = no station found."),
    ("station_name_on_plan", "Station Name on Plan", 22, True,
     "The station name as written on the plan. Can be a former name (e.g. 'Danziger Straße')."),
    ("scale", "Scale", 14, True, "Scale(s) written on the plan, e.g. 1:50. Several values = detail drawings."),
    ("creation_date", "Creation Date", 14, False,
     "Date of the plan as DD.MM.YYYY. XX = part not known (e.g. XX.12.1961 = December 1961)."),
    ("stairs", "Stairs / Escalator", 12, False,
     "Yes / No / Unsure: is a stairs or escalator word ('Treppe', 'Fahrtreppe' ...) written on the plan?"),
    ("stairs_type", "Stairs Type", 16, False, "Stairs, Escalator, or Stairs + escalator."),
    ("plan_title", "Plan Title", 45, True, "Title as written on the plan. ' | ' marks a new line on the plan."),
    ("plan_number", "Plan Number", 24, True,
     "Drawing, sheet and archive numbers found on the plan. Several values are separated by ';'."),
    ("structure_number", "Structure Number", 14, False,
     "Structure number derived from an archive stamp (e.g. stamp D73-006 -> D073)."),
    ("needs_review", "Needs Review", 11, False,
     "Yes = a value was found but may be wrong, so a person should check it."),
    ("review_notes", "Review Notes", 45, True, "Which value should be checked, and why."),
    ("missing_fields", "Missing Fields", 26, True,
     "Fields that could not be found on the plan (their cells are empty). For information only."),
    ("keywords", "Keywords (All Text Read)", 60, False,
     "All clean lines of text read on the plan, separated by ';'. Useful for full-text search. "
     "Text is kept as read by OCR, so it can contain reading errors."),
]
EXCEL_CELL_LIMIT = 32000   # Excel cannot hold more characters in one cell

# --- All text read (BVG_Plan_Text.csv) ---------------------------------------------------
PLAN_TEXT_COLUMNS = ["File Name", "Area on Plan", "Text", "Reading Quality"]
QUALITY_HIGH, QUALITY_MEDIUM = 0.90, 0.60   # OCR confidence -> High / Medium / Low
ROWS3 = ("top", "middle", "bottom")
COLS3 = ("left", "centre", "right")


# Fields listed in "Missing Fields" when their cell is empty (structure number is left out on purpose:
# it can only be derived from an archive stamp, so it is empty on most plans by design)
MAIN_FIELDS = [("station", "station"), ("scale", "scale"), ("creation_date", "creation date"),
               ("plan_title", "plan title"), ("plan_number", "plan number")]


def review_only(notes):
    """Keeps only the real review notes (a value was found but may be wrong).
    'Not found' notes such as 'plan number: no plan number found' are dropped: they go to Missing Fields."""
    keep = []
    for note in [n.strip() for n in str(notes).split(" | ") if n.strip()]:
        reason = note.partition(":")[2].strip()
        if not (reason.startswith("no ") and reason.endswith("found")):
            keep.append(note)
    return " | ".join(keep)


def write_results(fields, output_dir):
    """fields = one row per plan with the internal column names. Writes the CSV and the Excel file.
    Returns the number of plans that need review."""
    fields = fields.fillna("").astype(str).copy()
    fields["file_name"] = [f"{d}/{f}" if d else f for d, f in zip(fields["folder"], fields["file_name"])]
    fields["review_notes"] = [review_only(n) for n in fields["review_notes"]]
    fields["needs_review"] = ["Yes" if n else "No" for n in fields["review_notes"]]
    fields["missing_fields"] = [", ".join(label for col, label in MAIN_FIELDS if not row[col].strip())
                                for _, row in fields.iterrows()]

    table = fields.reindex(columns=[c[0] for c in COLUMNS]).fillna("").astype(str)
    table.columns = [c[1] for c in COLUMNS]
    table.to_csv(output_dir / "BVG_Plan_Metadata.csv", index=False,
                 sep=settings.CSV_SEPARATOR, encoding=settings.CSV_ENCODING)
    write_excel(table, output_dir / "BVG_Plan_Metadata.xlsx")
    return int((table["Needs Review"] == "Yes").sum())


def write_excel(table, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan Metadata"
    n_cols = len(COLUMNS)
    last = get_column_letter(n_cols)
    thin = Side(style="thin", color=LINE)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    white = Side(style="thin", color="FFFFFF")
    header_border = Border(left=white, right=white)      # thin white lines between the column names
    ws.sheet_view.showGridLines = False
    review_count = int((table["Needs Review"] == "Yes").sum())

    # --- Row 1-2: title bar ---
    has_logo = LOGO.exists()
    title_col = "B" if has_logo else "A"
    ws.merge_cells(f"{title_col}1:{last}1")
    ws.merge_cells(f"{title_col}2:{last}2")
    ws[f"{title_col}1"] = "BVG Historical Construction Plans – Extracted Metadata"
    ws[f"{title_col}1"].font = Font(name="Arial", size=16, bold=True, color=BVG_DARK)
    ws[f"{title_col}2"] = (f"{len(table)} plans  ·  {review_count} marked for review  ·  "
                           f"created {date.today():%d.%m.%Y}  ·  BVG Plan OCR version {settings.VERSION}")
    ws[f"{title_col}2"].font = Font(name="Arial", size=10, color=BVG_DARK)
    for row in (1, 2):
        for col in range(1, n_cols + 1):
            ws.cell(row, col).fill = PatternFill("solid", fgColor=BVG_YELLOW)
        ws[f"{title_col}{row}"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 32
    ws.row_dimensions[2].height = 20
    if has_logo:
        from openpyxl.drawing.image import Image as XLImage
        logo = XLImage(str(LOGO))
        ratio = 60 / logo.height
        logo.height, logo.width = 60, round(logo.width * ratio)
        ws.add_image(logo, "A1")

    # --- Row 4: column names ---
    header_row = 4
    for col, (_, name, width, _, _) in enumerate(COLUMNS, 1):
        cell = ws.cell(header_row, col, name)
        cell.font = Font(name="Arial", size=10, bold=True, color=BVG_YELLOW)
        cell.fill = PatternFill("solid", fgColor=BVG_DARK)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = header_border
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[header_row].height = 30

    # --- Rows 5+: one row per plan ---
    for r, values in enumerate(table.itertuples(index=False), header_row + 1):
        needs_review = values[[c[1] for c in COLUMNS].index("Needs Review")] == "Yes"
        for col, (value, (_, name, _, wrap, _)) in enumerate(zip(values, COLUMNS), 1):
            cell = ws.cell(r, col, value[:EXCEL_CELL_LIMIT])
            cell.font = Font(name="Arial", size=10, bold=(name == "Needs Review" and needs_review))
            cell.alignment = Alignment(vertical="top", wrap_text=wrap)
            cell.border = border
            if needs_review and name in ("Needs Review", "Review Notes"):
                cell.fill = PatternFill("solid", fgColor=REVIEW_FILL)
            cell.number_format = "@"      # keep everything as text (dates like 01.03.1986 stay as written)

    ws.auto_filter.ref = f"A{header_row}:{last}{header_row + len(table)}"

    # --- Second sheet: what each column means ---
    guide = wb.create_sheet("Column Guide")
    guide.sheet_view.showGridLines = False
    guide.merge_cells("A1:B1")
    guide["A1"] = "Column Guide"
    guide["A1"].font = Font(name="Arial", size=14, bold=True, color=BVG_DARK)
    for col in (1, 2):
        guide.cell(1, col).fill = PatternFill("solid", fgColor=BVG_YELLOW)
    guide.row_dimensions[1].height = 28
    guide["A2"] = ("The values are suggestions from automatic text recognition (OCR). "
                   "Plans with 'Yes' in 'Needs Review' (highlighted in pale yellow) have a value that should be "
                   "checked by a person. An empty cell means: not found on the plan (see 'Missing Fields').")
    guide.merge_cells("A2:B2")
    guide["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    guide["A2"].font = Font(name="Arial", size=10, italic=True)
    guide.row_dimensions[2].height = 32
    for col, name in enumerate(("Column", "Meaning"), 1):
        cell = guide.cell(4, col, name)
        cell.font = Font(name="Arial", size=10, bold=True, color=BVG_YELLOW)
        cell.fill = PatternFill("solid", fgColor=BVG_DARK)
        cell.border = header_border
    for r, (_, name, _, _, meaning) in enumerate(COLUMNS, 5):
        guide.cell(r, 1, name).font = Font(name="Arial", size=10, bold=True)
        guide.cell(r, 2, meaning).font = Font(name="Arial", size=10)
        guide.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
        guide.cell(r, 1).alignment = Alignment(vertical="top")
        for col in (1, 2):
            guide.cell(r, col).border = border
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 90

    wb.save(path)


def reading_quality(score):
    """Turns the OCR confidence (0 to 1) into words that staff understand."""
    if score >= QUALITY_HIGH:
        return "High"
    if score >= QUALITY_MEDIUM:
        return "Medium"
    return "Low"


def plan_text(ocr, file_label):
    """All text of one plan for staff, without technical columns.
    Area on Plan: the plan is divided into 3 x 3 areas (top/middle/bottom x left/centre/right),
    measured from the outermost text on the plan, so the area is approximate.
    Order: area by area (top left first), and inside an area line by line, left to right."""
    t = ocr[["text", "ocr_score", "x1", "y1", "x2", "y2"]].copy()
    t["text"] = t["text"].fillna("").astype(str).str.strip()
    t = t[t["text"] != ""]
    if t.empty:
        return pd.DataFrame(columns=PLAN_TEXT_COLUMNS)
    cx, cy = (t["x1"] + t["x2"]) / 2, (t["y1"] + t["y2"]) / 2
    left, right, top, bottom = t["x1"].min(), t["x2"].max(), t["y1"].min(), t["y2"].max()
    t["_col"] = ((cx - left) / max(right - left, 1) * 3).clip(0, 2.999).astype(int)
    t["_row"] = ((cy - top) / max(bottom - top, 1) * 3).clip(0, 2.999).astype(int)
    line_height = max(float((t["y2"] - t["y1"]).median()), 1.0)
    t["_line"] = (cy / line_height).round()
    t = t.sort_values(["_row", "_col", "_line", "x1"], kind="stable")
    area = ["middle" if (r, c) == (1, 1) else f"{ROWS3[r]} {COLS3[c]}" for r, c in zip(t["_row"], t["_col"])]
    return pd.DataFrame({"File Name": file_label, "Area on Plan": area, "Text": t["text"].tolist(),
                         "Reading Quality": [reading_quality(s) for s in t["ocr_score"]]})


def write_plan_text(parts, output_dir):
    """Writes BVG_Plan_Text.csv (one row per piece of text, all plans)."""
    table = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=PLAN_TEXT_COLUMNS)
    table.to_csv(output_dir / "BVG_Plan_Text.csv", index=False,
                 sep=settings.CSV_SEPARATOR, encoding=settings.CSV_ENCODING)
