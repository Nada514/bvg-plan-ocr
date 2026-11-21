"""Field 6: plan number, and Field 7: structure number
(thesis notebooks 12, rule version v6, and 12b, rule version v1, unchanged).

Plan numbers are of three kinds: drawing numbers ("UBwE/374", "Zeichnung Nr. ..."),
sheet numbers ("Blatt Nr. 1") and archive numbers (stamp at the edge, e.g. "S510-023").
They are read only from the text on the plan, never from the file name.
The structure number is derived from an archive number outside the S series ("D73-006" -> "D073").

Version 2 (after the evaluation on the test plans):
  P1  texts with a telephone or fax number are ignored (a phone number is never a plan number);
  P2  all spellings of the drawing-number label are accepted ("Zg.-Nr.", "Zg. Nr.", "Zeichng. Nr.");
  P3  the value after a drawing-number label may contain letters ("Zeichnung Nr. G-Notausstieg E11-02a"),
      and a value found NEXT TO a drawing-number label must contain a digit;
  P4  a text that consists ONLY of "Blatt" + number is a sheet number ("Blatt 9."), unlike "siehe Blatt …";
  P5  a text that consists ONLY of a short code (1-2 capitals + 3 digits, e.g. "DE-016", "E 001")
      in the title block is a plan number.
"""
import re

MIN_SCORE = 0.60
MAX_DIFF = 2
TITLE_ZONE = (0.80, 0.70)

SHEET_RE = re.compile(r"\b(?:blatt|bl)\s*\.?\s*[nh]r\s*\.?\s*(\d[\d.]*(?:\s?[a-z]{1,4}\b)?)", re.I)
LABEL_ONLY_RE = re.compile(r"^\W*(?:(blatt|bl)|(zeichn\w*|zg|plan))\s*[-.\s]*\s*[nh]r\s*\.?\s*:?\W*$", re.I)  # P2
DRAWING_RES = [
    re.compile(r"\b(?:zg|zeichn\w*|plan)\s*[-.\s]*\s*nr\s*\.?\s*:?\s*(\d[\d\s./-]*\d)", re.I),   # P2
    re.compile(r"\b(UBw\s?[A-Z]?\s?/?\s?\d[\d ]{1,8}\d)", re.I),
    re.compile(r"\b([A-Z]{1,3}\s?/\s?[A-Z]{1,3}\s?-\s?\d{1,3}(?:\s?-\s?\d{1,3})+)"),
    re.compile(r"\b(M\.\s?\d{3,5})(?![\d:,.])"),
]
ARCHIVE_RE = re.compile(r"(?<![\w.,/])([A-Z0-9£$§])\s?(\d{2,3})\s?[-–]\s?(\d{3})(?![\d.,])")
LETTER_FIX = {"0": "D", "8": "B", "2": "S", "5": "S", "£": "S", "$": "S", "§": "S"}

ARCHIVE_PARTS = re.compile(r"^([A-Z])(\d{2,3})-(\d{3})$")

# Version 2
PHONE_RE = re.compile(r"\b(?:tel|fax|telefon|fon)\b", re.I)                                           # P1
DRAWING_CODE_RE = re.compile(r"\b(?:zg|zeichn\w*|plan)\s*[-.\s]*\s*nr\s*\.?\s*:?\s*"
                             r"([A-Za-z][\w./-]*(?:\s[\w./-]+)?)\s*$", re.I)                            # P3
SHEET_ALONE_RE = re.compile(r"^\W*blatt\s+(\d[\w.]*?)\.?\W*$", re.I)                                 # P4
CODE_ALONE_RE = re.compile(r"^\W*([A-Z]{1,2})[\s-]?(\d{3})\W*$")                                       # P5
NO_STRUCTURE_LETTERS = {"S"}


def norm(t):
    t = str(t).lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        t = t.replace(a, b)
    return t


def compact(t):
    return re.sub(r"[^a-z0-9]", "", norm(t))


def box_table(ocr):
    b = ocr.copy()
    b["height"] = (b[["x2", "y2"]].values - b[["x1", "y1"]].values).min(axis=1)
    w, h = b["x2"].max(), b["y2"].max()
    b["x_rel"] = ((b["x1"] + b["x2"]) / 2 / w).round(2)
    b["y_rel"] = ((b["y1"] + b["y2"]) / 2 / h).round(2)
    return b


def clean(t):
    return re.sub(r"\s+", " ", t).strip(" .-/")


def is_value_box(r, label_id):
    t = str(r.text).strip()
    return (r.name != label_id and t != "" and len(t) <= 20
            and bool(re.search(r"[A-Za-z0-9]", t)) and not LABEL_ONLY_RE.match(t))


def value_next_to(label, b, need_digit=False):
    h = label.height
    best, best_dist = None, None
    for i, r in b.iterrows():
        if not is_value_box(r, label.name):
            continue
        if need_digit and not re.search(r"\d", str(r.text)):     # P3
            continue
        same_row = min(label.y2, r.y2) - max(label.y1, r.y1) >= 0.5 * min(h, r.height)
        right = same_row and 0 <= r.x1 - label.x2 <= 3 * h
        below = (min(label.x2, r.x2) - max(label.x1, r.x1) > 0) and -0.3 * h <= r.y1 - label.y2 <= 1.5 * h
        if right or below:
            dist = (r.x1 - label.x2) if right else (r.y1 - label.y2)
            if best is None or dist < best_dist:
                best, best_dist = r, dist
    if best is None:
        return []
    parts = [best]
    for _ in range(2):
        cur = parts[-1]
        nxt = [r for i, r in b.iterrows()
               if is_value_box(r, label.name) and all(r.name != p.name for p in parts)
               and len(re.sub(r"[^A-Za-z0-9]", "", str(r.text))) >= 2
               and min(cur.x2, r.x2) - max(cur.x1, r.x1) >= 0.5 * min(cur.x2 - cur.x1, r.x2 - r.x1)
               and -0.5 * cur.height <= r.y1 - cur.y2 <= 0.5 * cur.height]
        if not nxt:
            break
        parts.append(min(nxt, key=lambda r: r.y1))
    return parts


def n_diff(a, b):
    a, b = compact(a), compact(b)
    return sum(x != y for x, y in zip(a, b)) if len(a) == len(b) else 99


def merge_readings(items):
    kept = []
    for value, score in sorted(items, key=lambda x: -x[1]):
        if all(n_diff(value, k) > MAX_DIFF for k, _ in kept):
            kept.append((value, score))
    return kept


def extract_numbers(ocr):
    """Drawing, sheet and archive numbers found in the text of one plan."""
    found = {"drawing": [], "sheet": [], "archive": []}
    repaired = False

    def add(kind, value, score):
        if value and compact(value) not in [compact(v) for v, _ in found[kind]]:
            found[kind].append((value, score))

    b = box_table(ocr)
    b = b[b["ocr_score"] >= MIN_SCORE]
    b = b[~b["text"].astype(str).str.contains(PHONE_RE)]                 # P1
    zone = b[(b["x_rel"] >= TITLE_ZONE[0]) & (b["y_rel"] >= TITLE_ZONE[1])]
    for _, lab in zone.iterrows():
        m = LABEL_ONLY_RE.match(str(lab["text"]))
        if m:
            parts = value_next_to(lab, zone, need_digit=not m.group(1))
            if parts:
                kind = "sheet" if m.group(1) else "drawing"
                value = clean(" ".join(str(p.text) for p in parts))
                score = sum(p.ocr_score for p in parts) / len(parts)
                add(kind, ("Blatt Nr. " + value) if kind == "sheet" else value, score)

    for _, r in b.iterrows():
        t = str(r["text"])
        for m in SHEET_RE.finditer(t):
            add("sheet", "Blatt Nr. " + clean(m.group(1)), r["ocr_score"])
        for rx in DRAWING_RES:
            for m in rx.finditer(t):
                add("drawing", clean(m.group(1)), r["ocr_score"])
        if not DRAWING_RES[0].search(t):                                   # P3
            m = DRAWING_CODE_RE.search(t)
            if m and re.search(r"\d", m.group(1)) and len(m.group(1)) <= 30:
                add("drawing", clean(m.group(1)), r["ocr_score"])
        m = SHEET_ALONE_RE.match(t)                                        # P4
        if m:
            add("sheet", "Blatt " + m.group(1), r["ocr_score"])
        m = CODE_ALONE_RE.match(t)                                         # P5
        if m and r["x_rel"] >= TITLE_ZONE[0] and r["y_rel"] >= TITLE_ZONE[1]:
            add("drawing", clean(t), r["ocr_score"])
        for m in ARCHIVE_RE.finditer(t):
            first, mid, last = m.groups()
            if not first.isalpha():
                if first not in LETTER_FIX:
                    continue
                first, repaired = LETTER_FIX[first], True
            add("archive", f"{first.upper()}{mid}-{last}", r["ocr_score"])

    found["archive"] = merge_readings(found["archive"])
    scores = [s for k in ("drawing", "sheet", "archive") for _, s in found[k]]
    result = {k: [v for v, _ in found[k]] for k in ("drawing", "sheet", "archive")}
    result["conf"] = round(sum(scores) / len(scores), 2) if scores else None
    result["repaired"] = repaired
    return result


def derive_structure(archive_numbers):
    """'D73-006' -> 'D073'; 'S510-023' -> '' (S stamps contain no structure number)."""
    out = []
    for a in str(archive_numbers).split(";"):
        m = ARCHIVE_PARTS.match(a.strip())
        if m and m.group(1) not in NO_STRUCTURE_LETTERS:
            value = f"{m.group(1)}{int(m.group(2)):03d}"
            if value not in out:
                out.append(value)
    return "; ".join(out)


def extract(ocr):
    f = extract_numbers(ocr)
    values = f["drawing"] + f["sheet"] + f["archive"]
    several = any(len(f[k]) > 1 for k in ("drawing", "sheet", "archive"))
    review = "no plan number found" if not values else ("several numbers of the same kind" if several else "")
    archive = "; ".join(f["archive"])
    return {"drawing_number": "; ".join(f["drawing"]),
            "sheet_number": "; ".join(f["sheet"]),
            "archive_number": archive,
            "structure_number": derive_structure(archive),
            "review": review}
