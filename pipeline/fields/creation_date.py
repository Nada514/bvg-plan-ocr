"""Field 3: creation date (thesis notebook 09, final version = Step 8i, unchanged except one point below).

Finds dates in many forms ("10.6.86", "März 97", "03.1997", "23.07." + "1998" in a nearby box),
skips change dates ("ergänzt am", "geändert", "freigegeben" ...) and returns the EARLIEST
complete date. A year alone is used only if nothing better exists.

Only change for unseen plans: the latest accepted year was fixed to 2026 (the year of the thesis);
it is now the current year, so that plans drawn after 2026 can also get a date. For all plans
processed in 2026 the result is identical.

Version 2 (after the evaluation on the test plans):
  D1  dates of REFERENCED documents are skipped ("vom 30.01.92", "v. 16.03.1994", "... gehörig");
  D2  dates next to a CREATION label ("bearbeitet", "gezeichnet", "entworfen", "aufgestellt",
      "gez.") are preferred over all other dates. Check labels ("geprüft") do not count.
      "Berlin, den" is NOT a creation label: on the development plans it also marks signature and
      approval dates (checked on UBwE374: "Berlin, den 2.2.67" is not the creation date 21.12.1966).
"""
import datetime
import re

import pandas as pd

from .neighbours import chains

LATEST_YEAR = datetime.date.today().year

MONTHS = {"januar": 1, "jan": 1, "februar": 2, "feb": 2, "märz": 3, "marz": 3, "maerz": 3, "mär": 3, "mrz": 3,
          "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7, "august": 8, "aug": 8,
          "september": 9, "sept": 9, "sep": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11,
          "dezember": 12, "dez": 12}
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12}
D = r"[\doO]"   # a digit, or the letter o/O that OCR often reads instead of 0

NUM_RE   = re.compile(rf"(?<![\dA-Za-z])({D}{{1,2}})\s?[.,]\s?({D}{{1,2}})\s?[.,]\s?({D}{{4}}(?!\d)|{D}{{2}}(?=\d[A-Za-zÄÖÜäöü]|(?!\d)))")
SEP_RE   = re.compile(rf"(?<![\dA-Za-z])({D}{{1,2}})\s?([/-])\s?({D}{{1,2}})\s?\2\s?({D}{{4}}|{D}{{2}})(?![\d])")
ISO_RE   = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
NAME_RE  = re.compile(r"(?:(\d{1,2})\.?\s*)?\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?\s*(\d{4}|\d{2})(?!\d)", re.IGNORECASE)
ROMAN_RE = re.compile(r"(?:(\d{1,2})\s*\.\s*)?\b(xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i)\b\s*\.?\s*(\d{4}|\d{2})(?!\d)", re.IGNORECASE)

YEAR = r"(18[89]\d|19\d\d|20[0-2]\d)"                                     # years 1880-2029
MY_RE = re.compile(rf"(?<![\d.,])(0?[1-9]|1[0-2])\s?[./]\s?{YEAR}(?!\d)")  # month + year: "03.1997", "3/1997"
YEAR_WORD_RE = re.compile(rf"(datum|gez|gezeichnet|bearb|aufgest|gepr|berlin)\D{{0,25}}?{YEAR}(?!\d)",
                          re.IGNORECASE)                                  # year next to a date word
YEAR_ALONE_RE = re.compile(rf"^\W*{YEAR}\W*$")                            # a box that contains only a year

CHANGE_RE = re.compile(r"erg(ä|a|ae)nzt|[g0](e|ä)?(ä|a|ae)ndert|letzt\w*\s*stand|freigegeben", re.IGNORECASE)

ROMAN_PAT = "xii|xi|x|ix|viii|vii|vi|v|iv|iii|ii|i"
DM_RE = re.compile(rf"(?<![\d.,])({D}{{1,2}})\s?\.\s?({D}{{1,2}}|{ROMAN_PAT})\s?\.(?!\s?\d)", re.IGNORECASE)
DATE_WORD_RE = re.compile(r"\b(den|d\.|am|datum|gez|gezeichnet|bearb|berlin)", re.IGNORECASE)

# Version 2
REFERENCE_RE = re.compile(r"\bvom\b|\bv\.\s*(?=\d)|geh[öo]r", re.IGNORECASE)                       # D1
CREATION_LABEL_RE = re.compile(r"bearb\w*|gezeichnet|\bgez\b\.?|\bgz\b|entw[oü]rfen|\bentw\b|aufgest\w*",
                               re.IGNORECASE)                                                             # D2
CHECK_LABEL_RE = re.compile(r"gepr|pr[üu]f", re.IGNORECASE)


def num(s):
    return int(s.replace("o", "0").replace("O", "0"))


def full_year(y):
    y = num(y) if isinstance(y, str) else y
    return y if y >= 100 else (2000 + y if y <= 30 else 1900 + y)


def valid(day, month, year):
    return (day is None or 1 <= day <= 31) and 1 <= month <= 12 and 1880 <= year <= LATEST_YEAR


def dates_in(t):
    found = set()

    def add(day, month, year):
        if valid(day, month, year):
            found.add((year, month, day if day else 0))

    for d, m, y in NUM_RE.findall(t):
        add(num(d), num(m), full_year(y))
    for d, _, m, y in SEP_RE.findall(t):
        add(num(d), num(m), full_year(y))
    for y, m, d in ISO_RE.findall(t):
        add(int(d), int(m), int(y))
    for d, name, y in NAME_RE.findall(t):
        add(int(d) if d else None, MONTHS[name.lower()], full_year(y))
    for d, rom, y in ROMAN_RE.findall(t):
        if d or "." in t:                       # a day or a dot must accompany a Roman month
            add(int(d) if d else None, ROMAN[rom.lower()], full_year(y))
    return found


def vertical_pairs(ocr, max_gap=1.5):
    """Each box joined with the box directly BELOW it (overlapping left-right and close)."""
    if not {"x1", "y1", "x2", "y2"} <= set(ocr.columns):
        return []
    boxes = ocr.sort_values("y1").reset_index(drop=True)
    out = []
    for _, a in boxes.iterrows():
        h = a["y2"] - a["y1"]
        below = boxes[(boxes["y1"] > a["y1"]) & (boxes["y1"] - a["y2"] <= max_gap * h)
                      & (boxes["x1"] < a["x2"]) & (boxes["x2"] > a["x1"])]
        if len(below):
            b = below.sort_values("y1").iloc[0]
            out.append(f"{a['text']} {b['text']}")
    return out


def before_change_word(t):
    """Keep only the text BEFORE a change word (dates after it are change dates) and, in version 2,
    BEFORE a reference word (dates after "vom" belong to another document)."""
    return REFERENCE_RE.split(CHANGE_RE.split(t)[0])[0]


def labelled_dates(t):
    """Version 2 (D2): complete dates that follow a creation label in the same text,
    up to the next check label ('geprüft')."""
    found = set()
    for m in CREATION_LABEL_RE.finditer(t):
        part = CHECK_LABEL_RE.split(t[m.end():])[0]
        found |= {d for d in dates_in(part) if d[1]}
        for month, year in MY_RE.findall(part):
            found.add((int(year), int(month), 0))
    return found


def all_dates(ocr):
    """All possible creation dates as (year, month, day). 0 = unknown part. Change dates are skipped."""
    found = set()
    texts = [str(text) for text, _ in chains(ocr, 2)]   # single boxes and side-by-side pairs
    texts += vertical_pairs(ocr)                        # box + the box below it
    for t in texts:
        t = before_change_word(t)
        LABELLED.update(labelled_dates(t))
        found |= dates_in(t)
        for month, year in MY_RE.findall(t):
            found.add((int(year), int(month), 0))
        for _, year in YEAR_WORD_RE.findall(t):
            found.add((int(year), 0, 0))
    for t in ocr["text"]:
        m = YEAR_ALONE_RE.match(str(t))
        if m:
            found.add((int(m.group(1)), 0, 0))
    return found


def month_value(m):
    m = m.lower()
    return ROMAN[m] if m in ROMAN else num(m)


def day_months(ocr):
    """'day.month.' WITHOUT a year: alone in a box, or after a date word (den, am, Berlin ...)."""
    out = []
    for _, r in ocr.iterrows():
        t = before_change_word(str(r["text"]))
        for dm in DM_RE.finditer(t):
            alone = len(t.strip()) <= len(dm.group(0)) + 2
            after_word = DATE_WORD_RE.search(t[:dm.start()]) is not None
            if alone or after_word:
                day, month = num(dm.group(1)), month_value(dm.group(2))
                if 1 <= day <= 31 and 1 <= month <= 12:
                    out.append((day, month, r))
    return out


def year_near(ocr, r, max_gap=1.5, side=2.0):
    """A box with only a year above, below or diagonally next to box r (up to 2 box-heights to the side)."""
    h = max(1, r["y2"] - r["y1"])
    gap = pd.concat([ocr["y1"] - r["y2"], r["y1"] - ocr["y2"]], axis=1).max(axis=1)
    near = ocr[(ocr["box_id"] != r["box_id"]) & (gap <= max_gap * h)
               & (ocr["x1"] < r["x2"] + side * h) & (ocr["x2"] > r["x1"] - side * h)].copy()
    near["gap"] = gap[near.index]
    for _, o in near.sort_values("gap").iterrows():
        m = YEAR_ALONE_RE.match(str(o["text"]))
        if m:
            return int(m.group(1))
    return None


LABELLED = set()   # filled by all_dates(): dates found next to a creation label (version 2)


def best_creation_date3(ocr):
    LABELLED.clear()
    dates = all_dates(ocr)
    labelled = [d for d in LABELLED if 1880 <= d[0] <= LATEST_YEAR]
    if labelled:                                                  # version 2 (D2)
        y, m, d = min(labelled)
        return (d or None, m, y), ("day+month+year" if d else "month+year") + " (labelled)"
    joined, no_year = set(), []
    for day, month, r in day_months(ocr):
        y = year_near(ocr, r)
        if y and valid(day, month, y):
            joined.add((y, month, day))
        elif not y:
            no_year.append((day, month))
    full = [d for d in dates | joined if d[1]]
    year_only = [d for d in dates if not d[1]]
    if full:
        y, m, d = min(full)
        prec = ("day+month+year" if d else "month+year") + (" (joined)" if (y, m, d) in joined else "")
        return (d or None, m, y), prec
    if year_only:
        y, _, _ = min(year_only)
        return (None, None, y), "year only"
    if no_year:
        d, m = no_year[0]
        return (d, m, None), "day+month (year missing)"
    return None, "none"


def show3(d):
    if d is None:
        return ""
    day = f"{d[0]:02d}" if d[0] else "XX"
    month = f"{d[1]:02d}" if d[1] else "XX"
    year = str(d[2]) if d[2] else "XXXX"
    return f"{day}.{month}.{year}"


def extract(ocr):
    """Date in BVG's notation (XX = unknown part). Anything less than month + year is marked for review."""
    found, precision = best_creation_date3(ocr)
    ok = precision.startswith(("day+month+year", "month+year"))
    review = "" if ok else ("no date found" if found is None else f"incomplete date ({precision})")
    return {"creation_date": show3(found), "review": review}
