"""OCR of ONE plan: rotation -> text detection -> cropping -> text recognition.

This file is started once per plan in its own process (by run_pipeline.py), so that the
memory of a very large scan is released after every plan and one failing plan does not
stop the others (same approach as in the thesis).

Usage (normally not needed by hand):
    python -m pipeline.ocr_worker <plan.tif> <ocr_table.csv> <plan_info.json>

The code is taken unchanged from the thesis: notebook 03b (rotation), src/detect_plan.py
(detection and cropping) and notebook 08 (recognition).
"""
import gc
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image

from . import settings
from .plan_files import read_dpi

Image.MAX_IMAGE_PIXELS = None
TURN = {90: Image.ROTATE_270, 180: Image.ROTATE_180, 270: Image.ROTATE_90}


# ---------- Step 1: rotation (notebook 03b) ----------
def detect_rotation(path, model):
    """How far the plan must be turned to be upright, and how sure the model is (0-1)."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((settings.ROTATION_PREVIEW_SIDE, settings.ROTATION_PREVIEW_SIDE))
    result = list(model.predict(np.array(img), batch_size=1))[0]
    label = int(result["label_names"][0])
    score = round(float(result["scores"][0]), 3)
    del img
    gc.collect()
    turn_by = (360 - label) % 360       # the model says how the plan IS turned -> turn it back
    return turn_by, score


def load_upright(path, turn_by, score):
    """Opens the plan and turns it only if the model is sure enough (rule: score >= 0.9)."""
    turn = turn_by if score >= settings.ROTATION_MIN_SCORE else 0
    img = Image.open(path)
    return (img.transpose(TURN[turn]) if turn else img), turn


# ---------- Step 2: smaller copy for detection (src/detect_plan.py) ----------
def make_small(img, dpi, target_dpi):
    scale = min(1.0, target_dpi / dpi, settings.MAX_SIDE / max(img.width, img.height))
    W, H = round(img.width * scale), round(img.height * scale)
    small = Image.new("L", (W, H), 255)
    for top in range(0, img.height, settings.STRIP):
        bottom = min(img.height, top + settings.STRIP)
        y0, y1 = round(top * scale), round(bottom * scale)
        if y1 > y0:
            strip = img.crop((0, top, img.width, bottom)).convert("L")
            small.paste(strip.resize((W, y1 - y0), Image.LANCZOS), (0, y0))
    return small.convert("RGB"), scale, round(dpi * scale)


# ---------- Step 3: cut each text region out of the full-resolution plan (src/detect_plan.py) ----------
def crop_box(img, poly_small, scale):
    poly = (poly_small / scale).astype(np.float32)
    w = int(max(np.linalg.norm(poly[0] - poly[1]), np.linalg.norm(poly[3] - poly[2])))
    h = int(max(np.linalg.norm(poly[0] - poly[3]), np.linalg.norm(poly[1] - poly[2])))
    m = max(2, int(h * settings.MARGIN))
    left, top = max(0, int(poly[:, 0].min()) - 2 * m), max(0, int(poly[:, 1].min()) - 2 * m)
    right, bottom = min(img.width, int(poly[:, 0].max()) + 2 * m), min(img.height, int(poly[:, 1].max()) + 2 * m)
    region = np.array(img.crop((left, top, right, bottom)).convert("L"))
    target = np.array([[m, m], [m + w, m], [m + w, m + h], [m, m + h]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform((poly - [left, top]).astype(np.float32), target)
    return cv2.warpPerspective(region, matrix, (w + 2 * m, h + 2 * m), borderValue=255), poly


# ---------- Step 4: read the text of every region (notebook 08) ----------
def recognize(crops, boxes, recognizer):
    """Vertical regions are read turned both ways; the reading with the higher confidence is kept."""
    images, owner, turn = [], [], []
    for crop, r in zip(crops, boxes.itertuples()):
        img = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)     # same 3-channel image as reading the saved crop
        if r.vertical:
            for direction, code in (("ccw", cv2.ROTATE_90_COUNTERCLOCKWISE), ("cw", cv2.ROTATE_90_CLOCKWISE)):
                images.append(cv2.rotate(img, code)); owner.append(r.box_id); turn.append(direction)
        else:
            images.append(img); owner.append(r.box_id); turn.append("none")
    if not images:
        return boxes.assign(turn=[], text=[], ocr_score=[])
    results = [(r["rec_text"], float(r["rec_score"]))
               for r in recognizer.predict(images, batch_size=settings.RECOGNITION_BATCH)]
    reads = pd.DataFrame({"box_id": owner, "turn": turn,
                          "text": [t for t, _ in results], "ocr_score": [s for _, s in results]})
    best = reads.sort_values("ocr_score", ascending=False).drop_duplicates("box_id")
    return boxes.merge(best, on="box_id").sort_values("box_id")


def run(plan_path, table_path, info_path):
    from paddleocr import DocImgOrientationClassification, TextDetection, TextRecognition

    start = time.time()
    dpi, dpi_found = read_dpi(plan_path)

    orient_model = DocImgOrientationClassification(model_name=settings.ROTATION_MODEL)
    turn_by, rot_score = detect_rotation(plan_path, orient_model)
    del orient_model
    img, turned = load_upright(plan_path, turn_by, rot_score)

    detector = TextDetection(model_name=settings.DETECTION_MODEL, limit_side_len=settings.MAX_SIDE, limit_type="max")
    small, scale, effective_dpi = make_small(img, dpi, settings.TARGET_DPI)
    result = list(detector.predict(np.array(small), batch_size=1))[0]
    polys = [np.array(p, dtype=float) for p in result["dt_polys"]]
    det_scores = [float(s) for s in result["dt_scores"]]
    del detector, small, result
    gc.collect()

    rows, crops = [], []
    for i, (poly_small, score) in enumerate(zip(polys, det_scores)):
        crop, poly = crop_box(img, poly_small, scale)
        crops.append(crop)
        rows.append({"box_id": i, "score": round(score, 3),
                     "crop_width": crop.shape[1], "crop_height": crop.shape[0], "vertical": crop.shape[0] > crop.shape[1],
                     "x1": round(poly[:, 0].min()), "y1": round(poly[:, 1].min()),
                     "x2": round(poly[:, 0].max()), "y2": round(poly[:, 1].max())})
    width, height = img.width, img.height
    del img
    gc.collect()
    seconds_detection = round(time.time() - start, 1)

    recognizer = TextRecognition(model_name=settings.RECOGNITION_MODEL)
    boxes = pd.DataFrame(rows, columns=["box_id", "score", "crop_width", "crop_height", "vertical",
                                        "x1", "y1", "x2", "y2"])
    ocr = recognize(crops, boxes, recognizer)
    Path(table_path).parent.mkdir(parents=True, exist_ok=True)
    ocr.to_csv(table_path, index=False, encoding="utf-8-sig")

    info = {"dpi": dpi, "dpi_in_file": dpi_found, "rotation_turn_by": turn_by, "rotation_score": rot_score,
            "turned_by": turned, "width_px": width, "height_px": height, "effective_dpi": effective_dpi,
            "text_regions": len(ocr), "seconds_detection": seconds_detection,
            "seconds_total": round(time.time() - start, 1)}
    Path(info_path).parent.mkdir(parents=True, exist_ok=True)
    Path(info_path).write_text(json.dumps(info), encoding="utf-8")
    print(f"regions {len(ocr)} | turned {turned} | {info['seconds_total']} s")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
