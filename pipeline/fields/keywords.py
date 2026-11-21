"""Field 8: keywords (thesis notebook 13, rule version v4, unchanged).

Every clean line of recognized text becomes a keyword, so that staff can find a plan by any
word written on it. Title-block admin fields (names, addresses, 'Datum' ...) are left out,
and two readings of the same label are merged.
"""
import re

from rapidfuzz import fuzz

MIN_SCORE = 0.60
MIN_LETTERS = 4
MIN_LETTER_SHARE = 0.5
MAX_ADMIN_WORDS = 4
MERGE_SIMILARITY = 85

ADMIN_START = ("gepr", "bearb", "datum", "massst", "masst", "maszst", "blatt", "zeichn", "auftrag",
               "exemplar", "projekt", "abt", "verkehrsbe", "betriebe", "werkstatt", "entwurf",
               "anderung", "geandert", "freigabe", "freigeg", "ersetzt", "unterschrift", "name", "pruf",
               "bauherr", "hauptabt", "architekt", "dipl", "telef", "anstal", "unternehmen", "kombinat",
               "einverstanden", "ubereinst", "ausfuhr", "beschein", "planung", "senator", "format",
               "anlage", "anmerkung")
ADMIN_EXACT = {"gez", "ing", "tel", "nr", "din"}
STREET_ENDS = ("str", "strasse", "allee", "weg", "damm", "platz", "ufer", "ring", "chaussee")


def norm(t):
    """Lowercase, replace umlauts, keep only letters/digits and single spaces."""
    t = str(t).lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def letters(t):
    return sum(c.isalpha() for c in str(t))


def is_admin(text):
    w = norm(text).split()
    if len([x for x in w if re.fullmatch(r"[a-z]{2,}", x)]) > MAX_ADMIN_WORDS:
        return False
    if any(x.startswith(ADMIN_START) or x in ADMIN_EXACT for x in w):
        return True
    return (bool(re.search(r"\d", str(text))) and len(w) <= 4
            and any(x.endswith(STREET_ENDS) or x == "berlin" for x in w))


def is_keyword(text, score):
    t = str(text).strip()
    if score < MIN_SCORE or letters(t) < MIN_LETTERS:
        return False
    chars = sum(not c.isspace() for c in t)
    if letters(t) / chars < MIN_LETTER_SHARE:
        return False
    if is_admin(t):
        return False
    return any(len(w) >= 3 for w in re.findall(r"[^\W\d_]+", t))


def short_tokens(t):
    return tuple(x for x in norm(t).split() if x.isdigit() or len(x) <= 2)


def same_label(a, b):
    return short_tokens(a) == short_tokens(b) and fuzz.ratio(norm(a), norm(b)) >= MERGE_SIMILARITY


def merge_variants(items):
    kept = []
    for t, s in sorted(items, key=lambda x: -x[1]):
        if not any(same_label(t, k) for k, _ in kept):
            kept.append((t, s))
    order = {t: i for i, (t, _) in enumerate(items)}
    return sorted(kept, key=lambda x: order[x[0]])


def extract_keywords(ocr):
    out, seen = [], set()
    for _, r in ocr.iterrows():
        t = re.sub(r"\s+", " ", str(r["text"])).strip()
        if is_keyword(t, r["ocr_score"]) and norm(t) not in seen:
            seen.add(norm(t))
            out.append((t, float(r["ocr_score"])))
    return merge_variants(out)


def extract(ocr):
    return {"keywords": "; ".join(k for k, _ in extract_keywords(ocr)), "review": ""}
