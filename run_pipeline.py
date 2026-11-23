"""BVG plan OCR pipeline – the one file to run.

    python run_pipeline.py

1. Put the plans (TIFF or PDF, any file name, subfolders allowed) into the folder  input/
2. Run the command above.
3. The results appear in the folder  output/ :
     BVG_Plan_Metadata.xlsx   one row per plan with the extracted fields, formatted in BVG colours (for reading)
     BVG_Plan_Metadata.csv    the same table as a plain CSV file (for importing into other systems)
     BVG_Plan_Text.csv        all text read on each plan, with the area of the plan and a reading quality
     processing_log.csv       technical details per plan (rotation, resolution, time, errors)
     technical/bvg_ocr_full.csv   full OCR output with positions and scores (for checking and further work)

Plans that were already read are skipped when the command is run again (the OCR tables are kept
in output/_work/). Use  --redo  to read all plans again. Other folders:  --input  and  --output .
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from pipeline import settings
from pipeline.export import plan_text, write_plan_text, write_results
from pipeline.fields import FIELD_COLUMNS, extract_all, load_ocr_table
from pipeline.plan_files import convert_pdf, find_plans, plan_id

PACKAGE_DIR = settings.PACKAGE_DIR


def read_plan(path, work, input_dir, redo):
    """OCR of one plan in its own process. Returns (status, error message)."""
    pid = plan_id(path, input_dir)
    table = work / "ocr_tables" / f"{pid}.csv"
    info = work / "plan_info" / f"{pid}.json"
    if table.exists() and info.exists() and not redo:
        return pid, "done before", ""

    image_path = path
    if path.suffix.lower() == ".pdf":
        image_path = convert_pdf(path, work / "converted" / f"{pid}.tif")

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True"}
    r = subprocess.run([sys.executable, "-m", "pipeline.ocr_worker", str(image_path), str(table), str(info)],
                       cwd=PACKAGE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode == 0 and table.exists():
        return pid, "read now", ""
    lines = [l for l in (r.stderr or "").splitlines() if any(k in l for k in ("Error", "Exception", "error"))]
    message = " | ".join(lines[-3:]) if lines else (
        f"stopped without an error message (exit code {r.returncode}); "
        "often not enough free memory: close other programs and run again")
    return pid, "failed", message


def main():
    parser = argparse.ArgumentParser(description="Extract metadata from scanned BVG construction plans.")
    parser.add_argument("--input", default=str(PACKAGE_DIR / "input"), help="folder with the plans")
    parser.add_argument("--output", default=str(PACKAGE_DIR / "output"), help="folder for the results")
    parser.add_argument("--redo", action="store_true", help="read all plans again, even if read before")
    args = parser.parse_args()

    input_dir, output_dir = Path(args.input).resolve(), Path(args.output).resolve()
    work = output_dir / "_work"
    plans = find_plans(input_dir)
    print(f"Plans found in {input_dir}: {len(plans)}")
    if not plans:
        print("Nothing to do. Put TIFF or PDF plans into the input folder.")
        return

    # ---- Part 1: text recognition, one plan after the other ----
    status = {}
    for n, path in enumerate(plans, 1):
        name = str(path.relative_to(input_dir))
        print(f"[{n}/{len(plans)}] {name[:60]:60} ", end="", flush=True)
        start = time.time()
        try:
            pid, state, error = read_plan(path, work, input_dir, args.redo)
        except Exception as e:                       # e.g. a damaged file: note it and continue
            pid, state, error = plan_id(path, input_dir), "failed", str(e)
        status[path] = (pid, state, error)
        print(f"{state} ({time.time() - start:.0f} s)" + (f" -> {error}" if error else ""), flush=True)

    # ---- Part 2: the 8 fields and the output files ----
    print("\nExtracting the fields ...")
    clean_rows, ocr_parts, text_parts, log_rows = [], [], [], []
    for path in plans:
        pid, state, error = status[path]
        folder = str(path.parent.relative_to(input_dir))
        base = {"file_name": path.name, "folder": "" if folder == "." else folder}
        info_file = work / "plan_info" / f"{pid}.json"
        info = json.loads(info_file.read_text(encoding="utf-8")) if info_file.exists() and state != "failed" else {}
        log_rows.append({**base, "status": "failed" if state == "failed" else "ok", **info, "error": error})

        if state == "failed":
            row = {c: "" for c in FIELD_COLUMNS}
            row.update({"needs_review": "Yes", "review_notes": f"plan could not be processed: {error}"})
            clean_rows.append({**base, **row})
            continue

        ocr = load_ocr_table(work / "ocr_tables" / f"{pid}.csv")
        clean_rows.append({**base, **extract_all(ocr)})
        label = f"{base['folder']}/{base['file_name']}" if base["folder"] else base["file_name"]
        text_parts.append(plan_text(ocr, label))
        dump = ocr[["box_id", "text", "ocr_score", "x1", "y1", "x2", "y2", "vertical", "turn", "score"]].rename(
            columns={"turn": "read_turned", "score": "detection_score"})
        ocr_parts.append(dump.assign(**base)[list(base) + list(dump.columns)])

    output_dir.mkdir(parents=True, exist_ok=True)
    csv = dict(index=False, sep=settings.CSV_SEPARATOR, encoding=settings.CSV_ENCODING)
    review = write_results(pd.DataFrame(clean_rows), output_dir)   # Excel file + clean CSV
    write_plan_text(text_parts, output_dir)                          # all text, for staff
    technical = output_dir / "technical"
    technical.mkdir(exist_ok=True)
    if ocr_parts:
        pd.concat(ocr_parts, ignore_index=True).to_csv(technical / "bvg_ocr_full.csv", **csv)
    pd.DataFrame(log_rows).to_csv(output_dir / "processing_log.csv", **csv)

    failed = sum(s == "failed" for _, s, _ in status.values())
    print(f"Done. Plans: {len(plans)} | failed: {failed} | marked for review: {review}")
    print(f"Results in: {output_dir}")


if __name__ == "__main__":
    main()