# BVG Plan OCR – Reading metadata from scanned construction plans

This program reads scanned historical construction plans of BVG (Berliner Verkehrsbetriebe)
and automatically fills in a table with eight pieces of information for every plan, such as the
station name, scale, date and title. It was developed in the Bachelor's thesis of
**Nada Elnaggar** at HTW Berlin (supervisor: Prof. Dr. Katharina Simbeck, 2026).

> **Important:** The results are a **suggestion that saves typing, not a final answer.**
> Values the program is unsure about are marked for review, and fields stay empty when the
> text on the plan could not be read. Please read section 7, "What to expect", before using the results.

**Current version: 2.0** (see section 17, "Versions").

---

## Contents

**Part 1 – User guide (for everyone)**
1. What does this program do?
2. What you need
3. Installation (only once)
4. Using the program (every time)
5. The result files
6. How to read the result table
7. What to expect (accuracy)
8. Problems and solutions

**Part 2 – Documentation (according to the HTW guide "Documentation of Data & Code in Final Theses")**

9. What? – Software package
10. Who? – Origin, author and license
11. When? – Time period
12. Which? How much? – Data formats and size
13. Tools
14. Quality assurance
15. Data protection
16. Storage location
17. Versions

---

# Part 1 – User guide

## 1. What does this program do?

BVG's archive holds many old construction plans as scanned images. To find a plan, someone has
to open it and type its information into a table by hand. This program does a large part of that
work automatically:

```
Scanned plans  →  Read all text on the plan  →  Pick out the useful information  →  Excel table
 (TIFF / PDF)          (text recognition)          (8 fields, see below)           (one row per plan)
```

The program finds these **8 fields**:

| Field | Example |
|---|---|
| Station name | Bismarckstraße |
| Scale | 1:100 |
| Creation date | 23.07.1998 |
| Stairs / escalator mentioned | Yes – Escalator |
| Plan title | Einbau eines Aufzuges im U-Bhf Bismarckstraße |
| Plan number | UBwE/374 |
| Structure number | D073 |
| Keywords (all text read) | for searching any word on the plan |

Everything runs **on your own computer**. No plan or result is sent anywhere.

---

## 2. What you need

| What | Details |
|---|---|
| Computer | Windows, **at least 16 GB RAM** (large scans need a lot of memory) |
| Free disk space | About **2 GB** for Python, the program packages and the text recognition models |
| Python 3.11 | Free programming language the program runs on (installation in step 3) |
| Internet | Only **once**, during installation |

---

## 3. Installation (only once)

### Step 3.1 – Install Python 3.11
1. Go to https://www.python.org/downloads/ and download **Python 3.11** (for example 3.11.9).
2. Start the installer. **Tick the box "Add Python to PATH"** at the bottom of the first window.
3. Click **"Install Now"** and wait until it finishes.

### Step 3.2 – Download this program
1. On this GitHub page, click the green button **"Code"** (top right of the file list).
2. Click **"Download ZIP"**.
3. Unzip the file into a folder of your choice, for example `C:\BVG_Plan_OCR`.

### Step 3.3 – Open PowerShell in the program folder
1. Open the program folder in Windows Explorer (the folder that contains `run_pipeline.py`).
2. Click into the **address bar** at the top, type `powershell` and press **Enter**.
3. A blue or black window opens. This is where you type the commands below.

### Step 3.4 – Check Python
Type this and press Enter:
```
python --version
```
It should show `Python 3.11.…`. If it shows an error, repeat step 3.1 and make sure that
"Add Python to PATH" is ticked.

### Step 3.5 – Install the program packages
Type this and press Enter:
```
pip install -r requirements.txt
```
This takes a few minutes. The text recognition models (about 250 MB) are downloaded
automatically the first time the program runs.

**Installation done.** You never need to repeat it on this computer.

---

## 4. Using the program (every time)

1. **Put the plans into the folder `input`.**
   TIFF and PDF files are accepted, with any file name. Subfolders are allowed.
2. **Open PowerShell in the program folder** (as in step 3.3) and type:
   ```
   python run_pipeline.py
   ```
3. **Wait.** Each plan takes about 0.5–3 minutes. One line per plan is shown when it is finished.
4. **Open the results** in the folder **`output`** (see section 5).

### Useful options

| You want to … | Type this |
|---|---|
| Add new plans later | Just put them into `input` and run `python run_pipeline.py` again – plans already read are skipped, so only the new ones are read |
| Read **all** plans again | `python run_pipeline.py --redo` |
| Use other folders | `python run_pipeline.py --input "D:\Scans" --output "D:\Results"` |

---

## 5. The result files

All results are written into the folder **`output`**:

| File | What it contains | Who it is for |
|---|---|---|
| **`BVG_Plan_Metadata.xlsx`** | **The main result – open this one.** One row per plan with all fields, formatted for reading, plus a second sheet "Column Guide" | Everyone |
| `BVG_Plan_Metadata.csv` | The same table as a plain CSV file (comma-separated, UTF-8) | For importing into other systems |
| `bvg_ocr_full.csv` | **Everything the program read:** one row per text region of every plan, with its position on the plan | For searching any word or number |
| `processing_log.csv` | Technical details per plan (resolution, rotation, time, errors) | For checking problems |
| `_work` (folder) | Intermediate files of each plan, including the recognized text. **Do not delete it while the program is running** – it lets the program skip plans that were already read | The program itself |

---

## 6. How to read the result table

| Column | Meaning |
|---|---|
| File Name | The plan file in `input` (with its subfolder in front, if it is in one) |
| Station (Current Name) | Today's name of the U-Bahn station the plan belongs to (empty = no station found) |
| Station Name on Plan | The station name as written on the plan – can be a former name, e.g. "Danziger Straße" |
| Scale | Scale(s) on the plan, e.g. `1:50`. Several values = detail drawings with their own scale |
| Creation Date | Date of the plan as `DD.MM.YYYY`. `XX` = part not known (e.g. `XX.12.1961`) |
| Stairs / Escalator | `Yes` / `No` / `Unsure`: is a stairs word ("Treppe", "Fahrtreppe" …) written on the plan? |
| Stairs Type | `Stairs`, `Escalator` or `Stairs + escalator` |
| Plan Title | Title as written on the plan; ` \| ` marks a new line on the plan |
| Plan Number | Drawing, sheet ("Blatt Nr.") and archive numbers found on the plan, separated by `;` |
| Structure Number | Structure number derived from an archive stamp (e.g. stamp `D73-006` → `D073`) |
| Needs Review | `Yes` = a value **was found but may be wrong** – a person should check it |
| Review Notes | Which value to check and why, e.g. `station: station found without a station marker` |
| Missing Fields | Fields that were **not found** on the plan (their cells are empty) – for information only |
| Keywords (All Text Read) | All clean lines of text on the plan, separated by `;` – for full-text search |

**Three simple rules:**
- **Needs Review = Yes** → check the values named in *Review Notes* on the plan.
- **Empty cell** → nothing was found; there is nothing to check (it is listed in *Missing Fields*).
- Station names, titles and keywords stay **in German, exactly as written** on the plans.

---

## 7. What to expect (accuracy)

Version 1.0 was tested **once** on **30 plans that were not used while building the program**,
and the results were compared with BVG's own metadata table:

| Field | Version 1.0 (independent test) | Version 2.0 on the same plans* | What this means for you |
|---|---|---|---|
| Station | 22 of 30 correct | 22 of 30 | Check stations marked "without a station marker" |
| Scale | Found on 19 of 26 plans – **all 19 correct** | unchanged | Values can be trusted; empty = not readable |
| Creation date | Correct to the month on 11 of 25, 4 wrong | 14 of 25, 2 wrong | **Check:** plans often carry several dates |
| Stairs | 27 of 30 correct | unchanged | Stairs that are only drawn (no label) are not found |
| Plan title | Complete on 12 of 30 | unchanged | Titles marked for review are usually incomplete |
| Plan number | BVG's number found on 12 of 29 | 18 of 29 | Check; some number formats are not known |
| Structure number | Derived on 7 plans, 6 correct | 6 correct, 0 wrong | Only from archive stamps outside the S series |
| Keywords | 71 % of BVG's keywords found | unchanged | Good for full-text search |

\* Version 2.0 was improved using the errors found on these 30 plans, so its numbers are
**not an independent test**. They show the effect of the changes, not the expected result on
new plans. On the 12 plans used to build the program, version 2.0 gives the same results as
version 1.0, except for one plan number (one more number that is written on the plan was found).

### Known limitations
- **Only written text is used.** Anything that is only drawn (stairs, rooms) cannot be found.
- **Old, hand-lettered or faint text** is often misread or not read at all.
- **Creation date:** the program prefers a date next to "bearbeitet", "gezeichnet", "entworfen",
  "aufgestellt" or "gez."; dates of referenced documents ("vom …") are skipped. Otherwise it
  takes the earliest complete date, which can be the date of a revision or of another document.
  Handwritten or misread dates (e.g. "4927" for 1927) cannot be corrected.
- **Plan numbers:** the program knows labelled numbers ("Zeichnung Nr.", "Zg.-Nr.", "Blatt Nr."),
  typical BVG formats (`UBwE/374`, archive stamps like `S510-023`) and short codes standing alone
  in the title block (`DE-016`, `E 001`). Other formats (e.g. sketch numbers `SK 4995`) are not found.
- **Rotation:** a plan is turned automatically only if the program is very sure about its
  orientation. Plans scanned sideways are otherwise read sideways, which gives worse results.

---

## 8. Problems and solutions

| Problem | Solution |
|---|---|
| `python` is not recognized | Python is not installed or "Add Python to PATH" was not ticked → repeat step 3.1 |
| A plan shows `failed` | Usually the computer ran out of memory. Close other programs and run `python run_pipeline.py` again – only the failed plans are read again |
| `PermissionError` | A result file is still open in Excel. Close it and run again |
| The program is very slow | Normal for very large scans (up to about 3 minutes per plan) |
| A value is wrong | Check rows with **Needs Review = Yes** first; see section 7 for each field's reliability |

---

# Part 2 – Documentation

This part follows the HTW Berlin guide *"Documentation of Data & Code in Final Theses"*
(FitForFDM project, 2025).

## 9. What? – Software package

| | |
|---|---|
| **Type** | Software: Python program (scripts organised as a package) |
| **Purpose** | Automatic extraction of metadata from scanned historical BVG construction plans, to make BVG's digital plan archive easier to search and to complete its existing metadata |
| **Method** | Optical character recognition (OCR) with PaddleOCR, followed by rule-based extraction (text patterns, positions on the plan, word lists) and fuzzy matching against a list of station names. In the thesis, PaddleOCR was compared with EasyOCR; PaddleOCR was selected. All rules were developed on 12 development plans and evaluated once on 30 unseen test plans |
| **Language of the plans** | German (DE) |
| **Language of code and documentation** | English (EN) |
| **Data in this repository** | Program code (Python), a station list (CSV) and its sources (TXT). No plans and no results |

## 10. Who? – Origin, author and license

| | |
|---|---|
| **Author** | Nada Elnaggar, HTW Berlin (Bachelor's thesis, Business Informatics) |
| **Supervisor** | Prof. Dr. Katharina Simbeck |
| **Program code** | Written by the author. License: **MIT License** (see file `LICENSE`) |
| **Station list** (`resources/stations.csv`, `SOURCES.txt`) | Compiled by the author from public sources (BVG press releases, newspapers, UrbanRail.Net; listed in `SOURCES.txt`). License: **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/) |
| **Construction plans and BVG metadata table** | Property of BVG. **Restricted access:** not public and not part of this repository. They can only be obtained from BVG, with BVG's permission |
| **Identifier** | No DOI. The software is identified by its repository address https://github.com/Nada514/bvg-plan-ocr and the version tags `v1.0` (thesis version) and `v2.0` (current version) |

## 11. When? – Time period

| Period | Activity |
|---|---|
| October 2026 | Receiving the plans and BVG's metadata table, inventory, station list, development of rotation, text detection and OCR, engine comparison (PaddleOCR vs. EasyOCR) |
| November 2026 | Development of the field rules on 12 development plans |
| 21.11.2026 | Final test of version 1.0 on 30 test plans; version 2.0 |
| 22.11.2026 | New result files (Excel and CSV), run on all 42 plans, installation test from GitHub |
| 23.11.2026 | Documentation completed |

## 12. Which? How much? – Data formats and size

**Input (not in this repository):**
- 42 scanned construction plans: 40 TIFF files (`.tif`) and 2 PDF files (`.pdf`), together **about 245 MB**
- Resolution 200–400 DPI; 9.9 to 365 megapixels per plan

**Output per run (example: 42 plans; not in this repository):**

| File | Format | Size (42 plans) |
|---|---|---|
| `BVG_Plan_Metadata.xlsx` | Excel | about 40 KB |
| `BVG_Plan_Metadata.csv` | CSV (comma, UTF-8) | about 60 KB |
| `bvg_ocr_full.csv` | CSV (comma, UTF-8) | about 1 MB |
| `processing_log.csv` | CSV | under 10 KB |
| `_work/` | Intermediate files per plan | about 750 MB |

**In this repository:** Python code (`.py`), station list (`.csv`, 176 stations with 213 current
and former names), sources (`.txt`), documentation (`.md`) – together well under 1 MB.

**Downloaded automatically on first run:** text recognition models, about 250 MB.

## 13. Tools

| Purpose | Tool | Version | Link |
|---|---|---|---|
| Programming language | Python | 3.11.9 | https://www.python.org |
| Deep learning framework (runs the models) | PaddlePaddle | 3.2.0 | https://github.com/PaddlePaddle/Paddle |
| Rotation, text detection and text recognition | PaddleOCR | 3.7.0 | https://github.com/PaddlePaddle/PaddleOCR |
| – orientation model | PP-LCNet_x1_0_doc_ori | (PaddleOCR 3.7.0) | see PaddleOCR |
| – text detection model | PP-OCRv5_server_det | (PaddleOCR 3.7.0) | see PaddleOCR |
| – text recognition model | latin_PP-OCRv5_mobile_rec | (PaddleOCR 3.7.0) | see PaddleOCR |
| Image processing (cutting out and turning text regions) | OpenCV (opencv-python) | 5.0.0.93 | https://opencv.org |
| Opening large images | Pillow | 12.3.0 | https://python-pillow.org |
| Calculations on images | NumPy | 2.3.5 | https://numpy.org |
| Tables | pandas | 2.2.3 | https://pandas.pydata.org |
| Fuzzy matching of station names | RapidFuzz | 3.14.6 | https://github.com/rapidfuzz/RapidFuzz |
| Converting PDF to image | PyMuPDF | 1.28.2 | https://pymupdf.readthedocs.io |
| Writing the Excel file | openpyxl | 3.1.5 | https://openpyxl.readthedocs.io |
| Version control | Git and GitHub | – | https://github.com |

The exact package versions are also listed in `requirements.txt`. AI assistance used during
development is documented in the thesis (Appendix A).

## 14. Quality assurance

- **Separate development and test plans:** all rules were built on 12 development plans only.
  They were frozen before the 30 test plans were processed, and the test was run once.
- **Checked reference data:** results were compared with BVG's metadata table and a manually
  created reference (ground truth). Errors found in BVG's table were checked on the plan itself
  and recorded as documented corrections; BVG's original table was never changed.
- **No overfitting:** rules contain no plan names or reference values; every change was checked
  for side effects on all development plans.
- **Program checked against the thesis code:** on the 12 development plans all fields are
  identical; on the 30 test plans the recognized text is identical for every plan, and the station
  names reproduce the thesis result (22 of 30).
- **Installation test:** the program was downloaded from GitHub into an empty folder, installed
  with `requirements.txt` and run on a TIFF and a PDF plan without errors.
- **Review marking:** uncertain values are marked *Needs Review* so that a person checks them.

## 15. Data protection

- **Sensitive data:** the plans and BVG's metadata table are **confidential**. They are not part
  of this repository; the file `.gitignore` excludes `input/`, `output/` and all plan and result files.
- **Personal data:** the plans can contain names of people (e.g. draftsmen or approvers in the
  title block). These names can appear in the result files (*Keywords*, `bvg_ocr_full.csv`).
  **Treat all result files as confidential, like the plans themselves.**
- **Local processing:** the program runs completely on the local computer; no data is sent
  anywhere. Internet is only needed once to download the models.
- **Copyright:** the plans are owned by BVG. The program code is the author's own work (MIT
  License). The tools used are open-source software under their own licenses. Information on
  copyright: https://bibliothek.htw-berlin.de/urheberrecht/

## 16. Storage location

**Folder structure**
```
bvg_plan_ocr/
├── run_pipeline.py          the program to run (start here)
├── requirements.txt         Python packages and versions
├── README.md                this documentation
├── LICENSE                  license of the program code (MIT)
├── input/                   put plans here (not part of the repository)
├── output/                  results appear here (not part of the repository)
│   └── _work/               intermediate files per plan, used for re-runs
├── resources/
│   ├── stations.csv         176 stations with 213 current and former names
│   └── SOURCES.txt          sources of the former station names
└── pipeline/
    ├── settings.py          all fixed settings (resolution, thresholds, models, version)
    ├── plan_files.py        finds the plans, converts PDFs, reads the resolution
    ├── ocr_worker.py        rotation, text detection, cutting out and reading the text of one plan
    ├── export.py            writes the Excel and CSV result files
    └── fields/              one file per field: station.py, scale.py, creation_date.py,
                             stairs.py, title.py, plan_number.py (incl. structure number),
                             keywords.py; neighbours.py = shared helper for text regions
                             lying next to each other
```
(`.gitkeep` in `input/` and `output/` is an empty placeholder: Git does not store empty
folders, so this file keeps them in the repository.)

**File naming conventions**
- Input plans: any file name (the program does not rely on file names).
- Result files: fixed names (`BVG_Plan_Metadata.xlsx`, `BVG_Plan_Metadata.csv`,
  `bvg_ocr_full.csv`, `processing_log.csv`); each run overwrites them.
- Code: lower case with underscores, named after what the file does (e.g. `creation_date.py`).
- Versions: Git tags `v1.0` and `v2.0`.

**Storage and access**

| What | Where | Who has access |
|---|---|---|
| Program code, station list, documentation | GitHub: https://github.com/Nada514/bvg-plan-ocr (public) | Everyone |
| Plans and BVG metadata table | BVG; for the thesis a copy on the author's laptop with backups on OneDrive/USB | BVG, the author, the examiners |
| Result files | Handed over directly to BVG (never via GitHub) | BVG, the author, the examiners |

**Deletion date**
- Program code and documentation: kept permanently on GitHub.
- The author's copies of the plans, BVG's table and the result files (laptop and backups) are
  deleted after the thesis has been graded, **at the latest on 31.03.2027**.

## 17. Versions

- **1.0** – rules developed on 12 development plans and frozen; evaluated once on 30 unseen test
  plans. These are the results reported in the thesis.
- **2.0** (current) – general improvements after the error analysis of the test plans:
  - dates of referenced documents ("vom …") are skipped; dates next to a creation label are preferred
  - telephone and fax numbers are ignored
  - all spellings of the drawing-number label ("Zg.-Nr.") and codes with letters after it are accepted
  - standalone "Blatt + number" and short codes in the title block are read as plan numbers
  - when one station name contains another, the longer one is chosen
  - not changed on purpose: the scale rule (accepting misread forms would create false scales
    from dimensions) and sketch numbers ("SK …" also appears as a reference to other sheets)
  - new result files: formatted Excel file and clean CSV with English column names
    (`BVG_Plan_Metadata`); "not found" is reported in the column *Missing Fields*, and
    *Needs Review* marks only values that were found but may be wrong