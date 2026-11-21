"""Joining neighbouring text regions (from src/evaluation.py of the thesis, unchanged).

Used by the station name and the creation date: a name or date is often split over
two regions that stand next to each other or directly below each other.
"""


def neighbours(ocr):
    x1, y1, x2, y2 = (ocr[c].values for c in ("x1", "y1", "x2", "y2"))
    h = (y2 - y1).clip(min=1)
    nxt = {i: [] for i in range(len(ocr))}
    for i in range(len(ocr)):
        for j in range(len(ocr)):
            if i == j:
                continue
            same_line = min(y2[i], y2[j]) - max(y1[i], y1[j]) > 0.5 * min(h[i], h[j])
            if same_line and -1.0 * h[i] <= x1[j] - x2[i] <= 2 * h[i]:
                nxt[i].append(j)
            elif -0.3 * h[i] <= y1[j] - y2[i] <= h[i] and min(x2[i], x2[j]) > max(x1[i], x1[j]):
                nxt[i].append(j)
    return nxt


def chains(ocr, max_boxes):
    """All texts of single regions and of chains of up to max_boxes neighbouring regions."""
    texts = ocr["text"].tolist()
    nxt = neighbours(ocr)
    found = []

    def walk(path):
        found.append((" ".join(texts[k] for k in path), frozenset(path)))
        if len(path) < max_boxes:
            for j in nxt[path[-1]]:
                if j not in path:
                    walk(path + [j])

    for i in range(len(texts)):
        walk([i])
    return found
