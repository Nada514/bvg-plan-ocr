"""Field 4: stairs and escalators (thesis notebook 10, unchanged).

Searches the recognized text for stairs words ("Treppe", "Fahrtreppe", "Rolltreppe" ...).
Stairs that are only DRAWN, without any label, cannot be found by text recognition.
"""
import re

from rapidfuzz import fuzz

STAIRS_WORDS = ["treppe", "treppen", "fahrtreppe", "rolltreppe", "treppenanlage", "treppenhaus"]
REVIEW_SCORE = 0.80   # below this OCR confidence a human should check


def norm(t):
    """Lowercase and replace umlauts so 'Treppe' and 'TREPPE' match."""
    t = str(t).lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        t = t.replace(a, b)
    return t


def stairs_in(ocr):
    """exact = word contains 'trepp'; fuzzy = almost a stairs word (small OCR error).
    evidence = the full text lines where a stairs word was found, with their OCR confidence."""
    exact, fuzzy, evidence = set(), set(), []
    for text, score in zip(ocr["text"].astype(str), ocr["ocr_score"]):
        hit = False
        for word in re.findall(r"[a-z]{5,}", norm(text)):
            if "trepp" in word:
                exact.add(word)
                hit = True
            elif any(fuzz.ratio(word, w) >= 85 for w in STAIRS_WORDS):
                fuzzy.add(word)
                hit = True
        if hit:
            evidence.append((text.strip(), float(score)))
    return exact, fuzzy, evidence


def stairs_type(words):
    """Label what was found: normal stairs, escalator, or both."""
    esc = any("fahrtrepp" in w or "rolltrepp" in w for w in words)
    other = any("trepp" in w and "fahrtrepp" not in w and "rolltrepp" not in w for w in words)
    return ("Stairs + escalator" if esc and other else
            "Escalator" if esc else
            "Stairs" if other else "")


def extract(ocr):
    exact, fuzzy, evidence = stairs_in(ocr)
    found = bool(exact or fuzzy)
    best = max((s for _, s in evidence), default=None)
    unsure = found and (not exact or best < REVIEW_SCORE)
    return {"stairs": "Unsure" if unsure else ("Yes" if found else "No"),
            "stairs_type": stairs_type(exact | fuzzy),
            "stairs_text": " | ".join(t for t, _ in evidence[:3]),
            "review": "stairs word unclear or hard to read" if unsure else ""}
