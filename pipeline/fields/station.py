"""Field 1: station name (thesis notebook 06 and src/evaluation.py, unchanged).

All recognized texts are compared with the station list (current and former names),
using fuzzy matching with a threshold of 85. A weak match only counts next to a station
marker such as "U-Bhf". Result: the CURRENT name of the station.
"""
import re

import pandas as pd
from rapidfuzz import fuzz, process

from .. import settings
from .neighbours import chains

MARKER = re.compile(r"\b(u ?bahnhof|bahnhof|u ?bhf|bhf|haltestelle)\b")
STRONG = 90
VARIANTS, CURRENT, VAR_NOSPACE, VARIANT_NAME = {}, {}, {}, {}
VAR_LIST, NOSPACE_LIST = [], []


def norm(text):
    t = str(text).lower()
    t = t.replace("ß", "ss").replace("ſ", "s")
    t = t.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\bstr\b", "strasse", t)
    t = re.sub(r"(\w)str\b", r"\1strasse", t)
    t = re.sub(r"\bpl\b", "platz", t)
    return " ".join(t.split())


def load_stations(path=settings.STATION_LIST):
    stations = pd.read_csv(path, encoding="utf-8-sig")
    VARIANTS.clear(); CURRENT.clear(); VAR_NOSPACE.clear(); VARIANT_NAME.clear()
    for r in stations.itertuples():
        names = [r.current_name] + [n.strip() for n in str(r.old_names).split(";") if n.strip() and n.strip().lower() != "nan"]
        for n in names:
            VARIANTS.setdefault(norm(n), set()).add(r.current_name)
            VARIANT_NAME.setdefault(norm(n), n)
        CURRENT[norm(r.current_name)] = r.current_name
    VAR_LIST[:] = list(VARIANTS)
    VAR_NOSPACE.update({v.replace(" ", ""): v for v in VAR_LIST})
    NOSPACE_LIST[:] = list(VAR_NOSPACE)
    return len(stations), len(VAR_LIST)


def grams(text, max_words=4):
    w = text.split()
    for size in range(1, max_words + 1):
        for i in range(len(w) - size + 1):
            yield " ".join(w[i:i + size])


def match_text(t, mode, threshold):
    found = {}
    for g in grams(t):
        ns = g.replace(" ", "")
        if mode == "exact":
            if g in VARIANTS:
                found[g] = 100
            if ns in VAR_NOSPACE:
                found[VAR_NOSPACE[ns]] = 100
        else:
            for v, s, _ in process.extract(g, VAR_LIST, scorer=fuzz.ratio, score_cutoff=threshold, limit=None):
                found[v] = max(found.get(v, 0), s)
            for v, s, _ in process.extract(ns, NOSPACE_LIST, scorer=fuzz.ratio, score_cutoff=threshold, limit=None):
                found[VAR_NOSPACE[v]] = max(found.get(VAR_NOSPACE[v], 0), s)
    return found


def collect_hits(ocr, mode, threshold=settings.FUZZY_THRESHOLD):
    hits = {}
    for text, boxes in chains(ocr, 2):
        t = norm(text)
        marker = bool(MARKER.search(t))
        for variant, score in match_text(t, mode, threshold).items():
            if score < STRONG and not marker:
                continue
            targets = {CURRENT[variant]} if variant in CURRENT else VARIANTS[variant]
            for station in targets:
                h = hits.setdefault(station, {"boxes": set(), "marker": False, "best": 0, "variant": variant, "text": text})
                h["boxes"] |= boxes
                h["marker"] |= marker
                if score > h["best"]:
                    h["best"], h["variant"], h["text"] = score, variant, text
    return hits


def winner(hits):
    return max(hits, key=lambda s: (hits[s]["marker"], len(hits[s]["boxes"]), hits[s]["best"]))


def identify_full(ocr, mode="fuzzy", threshold=settings.FUZZY_THRESHOLD):
    """Same decision as in the thesis, plus whether the station was found next to a station marker."""
    if not VAR_LIST:
        load_stations()
    hits = collect_hits(ocr, mode, threshold)
    if not hits:
        return {"station": "no station", "name_on_plan": "", "text_read": "", "marker": False}
    station = winner(hits)
    h = hits[station]
    return {"station": station, "name_on_plan": VARIANT_NAME[h["variant"]], "text_read": h["text"], "marker": h["marker"]}


def extract(ocr):
    """Station for the output table. A station found WITHOUT a marker is marked for review
    (thesis Section 6.5: all false stations on the test plans were found without a marker)."""
    r = identify_full(ocr)
    if r["station"] == "no station":
        return {"station": "", "station_name_on_plan": "", "review": ""}
    return {"station": r["station"],
            "station_name_on_plan": r["name_on_plan"],
            "review": "" if r["marker"] else "station found without a station marker (U-Bhf, Bahnhof ...)"}
