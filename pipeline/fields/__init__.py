"""The 8 fields, each in its own file. extract_all() runs all of them on the OCR table of one plan.

The OCR table has one row per text region with the columns
box_id, x1, y1, x2, y2 (position in pixels), text and ocr_score (confidence 0-1).
"""
import pandas as pd

from . import creation_date, keywords, plan_number, scale, stairs, station, title

# Columns of the clean CSV, in this order (8 fields; some fields have more than one column)
FIELD_COLUMNS = [
    "station", "station_name_on_plan",          # 1 station name (current name + name as written)
    "scale",                                     # 2 scale
    "creation_date",                             # 3 creation date
    "stairs", "stairs_type",                     # 4 stairs and escalators
    "plan_title",                                # 5 plan title
    "plan_number",                               # 6 plan number(s)
    "structure_number",                          # 7 structure number
    "keywords",                                  # 8 keywords
]


def load_ocr_table(path):
    """Reads an OCR table exactly as the thesis notebooks did (empty text -> '', missing score -> 0)."""
    ocr = pd.read_csv(path).fillna({"text": "", "ocr_score": 0})
    ocr["text"] = ocr["text"].astype(str)
    return ocr


def extract_all(ocr):
    """All 8 fields of one plan, plus the reasons why a human should check the result."""
    if len(ocr) == 0:
        row = {c: "" for c in FIELD_COLUMNS}
        row.update({"needs_review": "Yes", "review_notes": "no text found on the plan"})
        return row

    results = {
        "station": station.extract(ocr),
        "scale": scale.extract(ocr),
        "creation date": creation_date.extract(ocr),
        "stairs": stairs.extract(ocr),
        "plan title": title.extract(ocr),
        "plan number": plan_number.extract(ocr),
        "keywords": keywords.extract(ocr),
    }
    pn = results["plan number"]
    row = {
        "station": results["station"]["station"],
        "station_name_on_plan": results["station"]["station_name_on_plan"],
        "scale": results["scale"]["scale"],
        "creation_date": results["creation date"]["creation_date"],
        "stairs": results["stairs"]["stairs"],
        "stairs_type": results["stairs"]["stairs_type"],
        "plan_title": results["plan title"]["plan_title"],
        "plan_number": "; ".join(v for v in (pn["drawing_number"], pn["sheet_number"], pn["archive_number"]) if v),
        "structure_number": pn["structure_number"],
        "keywords": results["keywords"]["keywords"],
    }
    notes = [f"{name}: {r['review']}" for name, r in results.items() if r["review"]]
    row["needs_review"] = "Yes" if notes else "No"
    row["review_notes"] = " | ".join(notes)
    return row


def extract_details(ocr):
    """The same results with all intermediate values (used for checking against the thesis)."""
    return {
        "station": station.identify_full(ocr),
        "scale": scale.extract(ocr),
        "creation_date": creation_date.best_creation_date3(ocr),
        "stairs": stairs.extract(ocr),
        "title": title.extract_title(ocr),
        "plan_number": plan_number.extract(ocr),
        "keywords": keywords.extract_keywords(ocr),
    }
