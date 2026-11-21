"""Field 2: scale (thesis notebook 09, Step 7, unchanged).

Finds "1:number" in the recognized text and keeps only common scale values, so that
ratios such as slopes are ignored. A plan can show several scales (detail drawings),
so all of them are returned.
"""
import re

SCALES = {1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 200, 250, 500, 1000, 2000, 2500, 5000, 10000}
SCALE_RE = re.compile(r"(?<!\d)1\s*[:;]\s*([\do]{1,5})(?!\d)(?![.,]\d)", re.IGNORECASE)


def extract_scales(texts):
    found = set()
    for t in texts:
        for m in SCALE_RE.finditer(str(t)):
            number = int(m.group(1).lower().replace("o", "0"))
            if number in SCALES:
                found.add(f"1:{number}")
    return found


def extract(ocr):
    scales = sorted(extract_scales(ocr["text"]), key=lambda s: int(s[2:]))
    return {"scale": "; ".join(scales), "review": ""}
