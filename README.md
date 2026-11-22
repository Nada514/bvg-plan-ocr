# BVG Plan OCR – metadata from scanned construction plans

This program reads scanned historical construction plans of the BVG (TIFF or PDF) and
extracts eight metadata fields from the text written on each plan. It was developed in the
Bachelor's thesis of Nada ElNaggar (HTW Berlin, supervisor Prof. Dr. Katharina Simbeck, 2026).

**Version 2.0.** Version 1.0 is the version evaluated in the thesis; version 2.0 contains improved
rules for the creation date and the plan number (see "Versions" below).

The results are a **suggestion that saves typing, not a final answer**: values that the
program is unsure about are marked for review, and some fields stay empty when the text could
not be read. Please read "What to expect" before using the results.

---

## Part 1 – Quick start for BVG staff

### What you need
- A Windows computer with **at least 16 GB RAM** (large scans need a lot of memory)
- **Python 3.11** (https://www.python.org/downloads/ – tick "Add Python to PATH" during installation)
- About 2 GB of free disk space for the programs and models

### Install (only once)
Open **PowerShell** in this folder (in Explorer: open the folder, type `powershell` in the
address bar, press Enter) and run:

```
pip install -r requirements.txt
```

The first run downloads the text recognition models automatically (internet needed once).

### Use (every time)

1. Put the plans into the folder **`input`**. TIFF and PDF files are accepted, with any file
   name. Subfolders are allowed.
2. In PowerShell, in this folder, run:
   ```
   python run_pipeline.py
   ```
3. Wait. Each plan takes about 0.5–3 minutes. One line per plan is printed when it is done.
4. Open the results in the folder **`output`**:

| File | Content |
|---|---|
| `BVG_Plan_Metadata.xlsx` | **The main result – open this one.** One row per plan with all fields, formatted for reading, with a second sheet "Column Guide". |
| `BVG_Plan_Metadata.csv` | The same table as a plain CSV file (comma-separated, UTF-8), for importing into other systems. |
| `bvg_ocr_full.csv` | **Everything the program read**: one row per text region of every plan, with its position. Use it to search for any word or number. |
| `processing_log.csv` | Technical details per plan (resolution, rotation, time, errors). |

### Good to know
- **Running again:** plans that were already read are skipped, so after adding new plans
  only the new ones are read. To read everything again: `python run_pipeline.py --redo`
- **Other folders:** `python run_pipeline.py --input "D:\Scans" --output "D:\Results"`
- **A plan shows `failed`:** usually the computer ran out of memory. Close other programs and
  run the same command again; only the failed plans are read again.
- **Close the result files in Excel before running again.** Otherwise Windows does not allow the
  program to overwrite them (error message `PermissionError`).
- **Never delete** the folder `output\_work` while a run is going on: it holds the recognized
  text of every plan.

---

## Part 2 – How to read `BVG_Plan_Metadata` (Excel and CSV)

| Column | Meaning |
|---|---|
| File Name | The plan file in `input` (with its subfolder in front, if it is in one) |
| Station (Current Name) | Current name of the U-Bahn station the plan belongs to (empty = no station found) |
| Station Name on Plan | The station name as written on the plan (can be a former name, e.g. "Danziger Straße") |
| Scale | Scale(s) written on the plan, e.g. `1:50`. Several values = detail drawings with own scales |
| Creation Date | Date of the plan as `DD.MM.YYYY`; `XX` = part not known (e.g. `XX.12.1961`) |
| Stairs / Escalator | `Yes` / `No` / `Unsure`: is a stairs word ("Treppe", "Fahrtreppe" …) written on the plan? |
| Stairs Type | `Stairs`, `Escalator` or `Stairs + escalator` |
| Plan Title | Title as written on the plan; ` \| ` marks a new line on the plan |
| Plan Number | Drawing, sheet ("Blatt Nr.") and archive numbers found on the plan, separated by `;` |
| Structure Number | Structure number derived from an archive stamp (e.g. stamp `D73-006` → `D073`) |
| Needs Review | `Yes` = a value **was found but may be wrong** – a person should check it |
| Review Notes | Which value should be checked and why, e.g. `station: station found without a station marker` |
| Missing Fields | Fields that were **not found** on the plan (their cells are empty) – for information only |
| Keywords (All Text Read) | All clean lines of text on the plan, separated by `;` – for full-text search |

- **Needs Review vs. Missing Fields:** an empty cell needs no check (there is nothing to check); it is
  listed in *Missing Fields*. *Needs Review* marks only values that are there but uncertain.
- Multiple values in one cell are separated by `;`. An empty cell means: not found.
- Station names, titles and keywords are kept in German, exactly as written on the plans.

---

## What to expect (results on 30 unseen test plans)

Version 1.0 was tested once on 30 plans that were not used during development, and the
results were compared with BVG's metadata table:

| Field | Version 1.0 on the test plans | Version 2.0 on the same plans* | Advice |
|---|---|---|---|
| Station | 22 of 30 correct | 22 of 30 | Check stations marked "without a station marker" |
| Scale | Found on 19 of 26 plans – **all 19 correct** | unchanged | Values can be trusted; empty = not readable |
| Creation date | Correct to the month on 11 of 25, 4 wrong | 14 of 25, 2 wrong | **Check**: plans carry several dates |
| Stairs | 27 of 30 correct | unchanged | Stairs that are only drawn (no label) are not found |
| Plan title | Complete on 12 of 30 | unchanged | Titles marked for review are usually incomplete |
| Plan number | BVG's number found on 12 of 29 | 18 of 29 | Check; some number formats are not known |
| Structure number | Derived on 7 plans, 6 correct | 6 correct, 0 wrong | Only from archive stamps outside the S series |
| Keywords | 71 % of BVG's keywords found | unchanged | Good for full-text search |

\* Version 2.0 was improved using the errors found on these test plans, so its numbers are
**not an independent test**. They show the effect of the changes, not the expected result on
new plans. On the 12 development plans, version 2.0 gives the same results as version 1.0, except
one plan number (one additional number that is written on the plan was found).

### Known limitations
- **Only written text** is used. Anything only drawn (stairs, rooms) cannot be found.
- **Old, hand-lettered or faint text** is often misread or not read.
- **Creation date:** the program prefers a date next to "bearbeitet", "gezeichnet",
  "entworfen", "aufgestellt" or "gez."; dates of referenced documents ("vom …") are skipped.
  Otherwise it takes the earliest complete date, which can be the date of a revision or of
  another document. Handwritten or misread dates (e.g. "4927" for 1927) cannot be corrected.
- **Plan numbers:** the program knows labelled numbers ("Zeichnung Nr.", "Zg.-Nr.",
  "Blatt Nr."), typical BVG formats (`UBwE/374`, archive stamps like `S510-023`), and short
  codes standing alone in the title block (`DE-016`, `E 001`). Other formats (e.g. sketch
  numbers `SK 4995`) are not found. Several values in one cell mean several numbers were found.
- **Rotation:** a plan is turned automatically only if the orientation model is very sure;
  plans scanned sideways are otherwise read sideways (worse results).

---

## Part 3 – Technical documentation

### What
Python program for optical character recognition (OCR) of scanned construction plans and
rule-based extraction of eight metadata fields. Language of the plans: German.
Language of code and documentation: English.

### How it works
For every plan, in its own process (to free the memory of large scans):
1. **PDF** → the first page is converted to TIFF (scanned picture taken out unchanged,
   drawn plans rendered at 400 DPI).
2. **Rotation**: orientation model `PP-LCNet_x1_0_doc_ori` on a 1500 px copy; the plan is
   turned only if the score is at least 0.9.
3. **Text detection**: `PP-OCRv5_server_det` on a copy of about 150 DPI (at most 4000 px).
4. **Cropping**: every text region is cut out of the full-resolution plan.
5. **Text recognition**: `latin_PP-OCRv5_mobile_rec`; vertical regions are read turned both
   ways and the more confident reading is kept.
6. **Fields**: rules on the recognized text (positions, patterns, word lists, comparison
   with the station list using fuzzy matching, threshold 85).

### Folder structure
```
bvg_plan_ocr/
├── run_pipeline.py          the program to run
├── requirements.txt         Python packages and versions
├── input/                   plans to process (not part of the repository)
├── output/                  results (not part of the repository)
│   └── _work/               recognized text per plan, used for re-runs
├── resources/
│   ├── stations.csv         176 stations with 213 current and former names
│   └── SOURCES.txt          sources of the former station names
└── pipeline/
    ├── settings.py          all fixed settings (resolution, thresholds, models)
    ├── plan_files.py        finding plans, PDF conversion, reading the resolution
    ├── ocr_worker.py        rotation, detection, cropping, recognition of one plan
    ├── export.py            writes BVG_Plan_Metadata.xlsx and .csv (column names, review, layout)
    └── fields/              one file per field (station, scale, creation_date, stairs,
                             title, plan_number incl. structure number, keywords)
```

### Tools and versions
Python 3.11.9 · PaddleOCR 3.7.0 · PaddlePaddle 3.2.0 · OpenCV · Pillow · NumPy · pandas ·
RapidFuzz · PyMuPDF 1.28.2 · openpyxl 3.1.5 (exact versions in `requirements.txt`).

### Quality assurance
- All rules were developed on 12 development plans and frozen before the test.
- The handed-over program was checked against the thesis code: on the 12 development plans
  all fields are identical; on the 30 test plans the recognized text is identical for every
  plan and the station names reproduce the thesis result (22 of 30).
- Test results: see "What to expect".

### Data protection
- The plans and BVG's metadata are **confidential and not part of this repository**.
  The `.gitignore` file excludes `input/`, `output/` and all plan and result files.
- The output files contain text from the plans and must be treated as confidential as well.
- The program runs completely on the local computer; no data is sent anywhere (internet is
  only needed once to download the models).

### Versions
- **1.0** – rules developed on 12 development plans and frozen; evaluated once on 30 unseen
  test plans (results in the thesis).
- **2.0** – general improvements after the error analysis of the test plans:
  dates of referenced documents ("vom …") are skipped; dates next to a creation label are
  preferred; telephone and fax numbers are ignored; all spellings of the drawing-number label
  ("Zg.-Nr.") and codes with letters after it are accepted; standalone "Blatt + number" and
  standalone short codes in the title block are read as plan numbers; when one station name
  contains another, the longer one is chosen. Not changed on purpose: the scale rule (accepting
  misread forms would create false scales from dimensions) and sketch numbers ("SK …" also
  appears as a reference to other sheets).
  Output of version 2.0: formatted Excel file and clean CSV with English column names
  (`BVG_Plan_Metadata`, replaces `bvg_fields.csv`); comma as CSV separator; "not found" is reported
  in the new column *Missing Fields*, and *Needs Review* marks only values that were found but may
  be wrong.

### Time period
Development October–November 2026; final test of version 1.0 on 21.11.2026; version 2.0 on
21.11.2026; new output files and run on all 42 plans on 22.11.2026.

### Author and license
Author: Nada ElNaggar, HTW Berlin (Bachelor's thesis, Business Informatics).
Supervisor: Prof. Dr. Katharina Simbeck.
License: see `LICENSE`.
