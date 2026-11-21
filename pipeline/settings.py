"""All fixed settings of the pipeline in one place.

These values were chosen on the 12 development plans of the thesis and then frozen.
Changing them changes the results, so only change them on purpose.
"""
from pathlib import Path

VERSION = "2.0"   # 1.0 = thesis version (evaluated on the test plans); 2.0 = improved rules for BVG

PACKAGE_DIR = Path(__file__).resolve().parent.parent
STATION_LIST = PACKAGE_DIR / "resources" / "stations.csv"

# --- Which files count as plans ------------------------------------------------
PLAN_EXTENSIONS = {".tif", ".tiff", ".pdf"}

# --- PDF conversion (thesis notebook 01) -----------------------------------------
PDF_MIN_SCAN_WIDTH = 2000   # a picture at least this wide inside a PDF is taken out unchanged
PDF_RENDER_DPI = 400        # otherwise the PDF page is rendered at this resolution
DEFAULT_DPI = 300           # NEW for unseen plans: used only if a TIFF has no DPI information

# --- Rotation (thesis notebook 03b, rule from Section 4.2) -------------------------
ROTATION_MODEL = "PP-LCNet_x1_0_doc_ori"
ROTATION_PREVIEW_SIDE = 1500   # the orientation model looks at a copy of at most 1500 px
ROTATION_MIN_SCORE = 0.9       # the plan is turned only if the model is at least this sure

# --- Text detection (src/detect_plan.py) -------------------------------------------
DETECTION_MODEL = "PP-OCRv5_server_det"
TARGET_DPI = 150     # resolution of the detection copy
MAX_SIDE = 4000      # largest side of the detection copy
STRIP = 2000         # rows of the original processed at a time (saves memory)
MARGIN = 0.15        # white margin around each cropped text region (share of its height)

# --- Text recognition (notebook 08) -------------------------------------------------
RECOGNITION_MODEL = "latin_PP-OCRv5_mobile_rec"
RECOGNITION_BATCH = 16

# --- Station matching (notebook 06 / src/evaluation.py) --------------------------
FUZZY_THRESHOLD = 85

# --- Output files ------------------------------------------------------------------
CSV_SEPARATOR = ";"          # ';' so that German Excel opens the files in columns
CSV_ENCODING = "utf-8-sig"   # keeps umlauts readable in Excel
