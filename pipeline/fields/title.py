"""Field 5: plan title (thesis notebook 11, rule version v3, review rule v3.1).

On modern plans, the title stands in the title block at the bottom right: the rule starts
from typical title words ("U-Bahnhof", "Lageplan", "Umbau" ...) and adds the lines stacked
directly above and below. Older plans without a title block: the largest heading is taken.
' | ' marks a new line on the plan.
"""
import re

TITLE_ZONE   = (0.80, 0.70)  # title block = right 20 % and bottom 30 % of the plan
MIN_SCORE    = 0.60          # ignore boxes that OCR is very unsure about
REVIEW_SCORE = 0.80          # below this mean confidence, a human should check the title
MAX_GAP      = 1.3           # title lines are at most 1.3 line heights apart
MIN_HEIGHT   = 0.67          # a title line has at least 2/3 of the letter height of its neighbour
MIN_ANCHOR_LETTERS = 8       # an anchor line needs at least 8 letters
STAMP_WORDS = ("schlechtes", "original", "unscharf")   # stamps and notes, not real titles

ANCHORS = ("bahnhof", "ubhf", "ubahn", "haltestelle", "lageplan", "grundris", "schnitt", "ansicht",
           "einbau", "umbau", "neubau", "rekonstruktion", "sanierung")

ADMIN_START = ("gepr", "bearb", "datum", "massst", "masst", "maszst", "blatt", "zeichn", "auftrag",
               "exemplar", "projekt", "abt", "verkehrsbe", "betriebe", "werkstatt", "entwurf",
               "anderung", "geandert", "freigabe", "freigeg", "ersetzt", "unterschrift", "name", "pruf",
               "bauherr", "hauptabt", "architekt", "dipl", "telef", "anstal", "unternehmen", "kombinat",
               "einverstanden", "ubereinst", "ausfuhr", "beschein", "planung", "senator", "format",
               "anlage", "anmerkung")
ADMIN_EXACT = {"gez", "ing", "tel", "nr", "din"}
STREET_ENDS = ("str", "strasse", "allee", "weg", "damm", "platz", "ufer", "ring", "chaussee")

PLAN_TYPES = {"lageplan": "Lageplan", "grundris": "Grundriss", "querschnitt": "Querschnitt",
              "langsschnitt": "Längsschnitt", "schnitt": "Schnitt", "ansicht": "Ansicht",
              "detail": "Detail", "ubersicht": "Übersichtsplan"}


def norm(t):
    """Lowercase and replace umlauts so 'Grundriß' and 'GRUNDRISS' can be compared."""
    t = str(t).lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        t = t.replace(a, b)
    return t


def box_table(ocr):
    """Add letter height and relative position (0 = left/top, 1 = right/bottom) to each box."""
    b = ocr.copy()
    b["height"] = (b[["x2", "y2"]].values - b[["x1", "y1"]].values).min(axis=1)
    w, h = b["x2"].max(), b["y2"].max()
    b["x_rel"] = ((b["x1"] + b["x2"]) / 2 / w).round(2)
    b["y_rel"] = ((b["y1"] + b["y2"]) / 2 / h).round(2)
    return b


def words_of(text):
    return re.findall(r"[a-z]+", norm(text))


def letters(text):
    return sum(c.isalpha() for c in str(text))


def is_admin(text):
    """Admin field or address line (e.g. 'Bauherr', 'Dipl.-Ing.', 'Potsdamer Str. 184')."""
    w = words_of(text)
    if any(x.startswith(ADMIN_START) or x in ADMIN_EXACT for x in w):
        return True
    return (bool(re.search(r"\d", str(text))) and len(w) <= 4
            and any(x.endswith(STREET_ENDS) or x == "berlin" for x in w))


def is_title_line(r):
    return letters(r.text) >= 4 and r.ocr_score >= MIN_SCORE and not is_admin(r.text)


def is_anchor(r):
    flat = re.sub(r"[^a-z]", "", norm(r.text))
    return is_title_line(r) and letters(r.text) >= MIN_ANCHOR_LETTERS and any(a in flat for a in ANCHORS)


def grow(b, start_ids):
    """Start from the anchor lines and add the lines stacked directly above and below them."""
    rows = {i: r for i, r in b.iterrows()}
    keep, todo = set(start_ids), list(start_ids)
    while todo:
        cur = rows[todo.pop()]
        cy = (cur.y1 + cur.y2) / 2
        for side in (-1, 1):
            cands = []
            for i, r in rows.items():
                if i == cur.name or letters(r.text) < 4:
                    continue
                if min(cur.x2, r.x2) - max(cur.x1, r.x1) <= 0:
                    continue
                if ((r.y1 + r.y2) / 2 - cy) * side <= 0:
                    continue
                gap = (r.y1 - cur.y2) if side == 1 else (cur.y1 - r.y2)
                cands.append((gap, i))
            if not cands:
                continue
            near = rows[min(cands)[1]]
            for gap, i in cands:
                r = rows[i]
                if i in keep or not (near.y1 <= (r.y1 + r.y2) / 2 <= near.y2):
                    continue
                if (gap <= MAX_GAP * max(cur.height, r.height)
                        and r.height >= MIN_HEIGHT * cur.height and is_title_line(r)):
                    keep.add(i)
                    todo.append(i)
    return b.loc[sorted(keep)]


def fill_in(b, lines):
    """Add short words (2-3 letters, e.g. 'im', 'an') directly between two selected title lines."""
    extra = []
    for i, r in b.iterrows():
        if i in lines.index or r.ocr_score < MIN_SCORE or is_admin(r.text):
            continue
        if not re.fullmatch(r"[^\W\d_]{2,3}\.?", str(r.text).strip()):
            continue
        col = lines[(lines["x2"].clip(upper=r.x2) - lines["x1"].clip(lower=r.x1)) > 0]
        up = col[col["y2"] <= (r.y1 + r.y2) / 2]
        down = col[col["y1"] >= (r.y1 + r.y2) / 2]
        if (len(up) and len(down)
                and (r.y1 - up["y2"]).min() <= MAX_GAP * up["height"].max()
                and (down["y1"] - r.y2).min() <= MAX_GAP * down["height"].max()):
            extra.append(i)
    return b.loc[sorted(set(lines.index) | set(extra))]


def reading_order(lines):
    """Sort lines row by row (top to bottom), and left to right within a row."""
    lines = lines.assign(yc=(lines["y1"] + lines["y2"]) / 2).sort_values("yc")
    row, start, ids = 0, None, []
    for _, r in lines.iterrows():
        if start is not None and r.yc - start > 0.5 * r.height:
            row += 1
            start = r.yc
        if start is None:
            start = r.yc
        ids.append(row)
    return lines.assign(row=ids).sort_values(["row", "x1"])


def plan_type(title):
    """Plan type(s) named in the title, e.g. 'Grundriss, Schnitt'."""
    t = norm(title)
    found = [label for key, label in PLAN_TYPES.items() if key in t]
    if "Querschnitt" in found or "Längsschnitt" in found:
        found = [f for f in found if f != "Schnitt"]
    return ", ".join(found)


def extract_title(ocr):
    """Title from the title block (anchor + stacked lines); if there is none, the largest heading."""
    b = box_table(ocr)
    b = b[b["ocr_score"] >= MIN_SCORE]
    zone = b[(b["x_rel"] >= TITLE_ZONE[0]) & (b["y_rel"] >= TITLE_ZONE[1])]
    anchors = [i for i, r in zone.iterrows() if is_anchor(r)]
    if anchors:
        lines, source = grow(zone, anchors), "title block"
    else:
        heads = b[[is_title_line(r) and letters(r.text) >= 8 for _, r in b.iterrows()]]
        if heads.empty:
            return {"title": "", "source": "not found", "conf": None}
        lines, source = grow(b, [heads["height"].idxmax()]), "largest heading"
    lines = reading_order(fill_in(zone if source == "title block" else b, lines))
    return {"title": " | ".join(lines["text"].str.strip()),
            "source": source,
            "conf": round(float(lines["ocr_score"].mean()), 2)}


def looks_like_junk(title):
    """Too short, or just a stamp word: a person should check it. (review rule v3.1)"""
    return letters(title) < 8 or any(w in norm(title) for w in STAMP_WORDS)


def extract(ocr):
    r = extract_title(ocr)
    if not r["title"]:
        reason = "no title found"
    elif r["conf"] is None or r["conf"] < REVIEW_SCORE:
        reason = "title hard to read (low OCR confidence)"
    elif looks_like_junk(r["title"]):
        reason = "title looks like a stamp or is too short"
    else:
        reason = ""
    return {"plan_title": r["title"], "plan_type": plan_type(r["title"]), "review": reason}