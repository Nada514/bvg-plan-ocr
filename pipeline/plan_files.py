"""Finding plans in the input folder, converting PDFs and reading the resolution.

Works for any file name: nothing here depends on the names of the thesis plans.
"""
import hashlib
import re
from pathlib import Path

from PIL import Image

from . import settings

Image.MAX_IMAGE_PIXELS = None   # allow very large scans


def find_plans(input_dir):
    """All TIFF and PDF files in the input folder and its subfolders, sorted by path."""
    input_dir = Path(input_dir)
    files = [p for p in input_dir.rglob("*")
             if p.is_file() and p.suffix.lower() in settings.PLAN_EXTENSIONS and not p.name.startswith(".")]
    return sorted(files, key=lambda p: str(p.relative_to(input_dir)).lower())


def plan_id(path, input_dir):
    """A short, safe and stable name for the work files of one plan.
    Built from the file name (letters/digits only) and a short code of the full path,
    so that umlauts, spaces or two plans with the same name in different folders cause no problems."""
    relative = str(Path(path).relative_to(input_dir))
    code = hashlib.md5(relative.encode("utf-8")).hexdigest()[:8]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(path).stem).strip("_")[:40]
    return f"{stem}_{code}"


def convert_pdf(pdf_path, out_path):
    """First page of a PDF as TIFF (thesis notebook 01, unchanged):
    a scanned picture inside the PDF is taken out without resizing; a drawn plan is rendered at 400 DPI."""
    import pymupdf as fitz
    doc = fitz.open(pdf_path)
    page = doc[0]
    images = page.get_images()
    biggest = max(images, key=lambda im: im[2] * im[3]) if images else None
    if biggest and biggest[2] >= settings.PDF_MIN_SCAN_WIDTH:
        pix = fitz.Pixmap(doc, biggest[0])
        if pix.n - pix.alpha > 3:                  # CMYK -> RGB
            pix = fitz.Pixmap(fitz.csRGB, pix)
        dpi = round(pix.width / (page.rect.width / 72))
    else:
        dpi = settings.PDF_RENDER_DPI
        pix = page.get_pixmap(dpi=dpi)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pix.pil_save(str(out_path), format="TIFF", dpi=(dpi, dpi))
    return out_path


def read_dpi(path):
    """Resolution stored in the image file (as in thesis notebook 01).
    Returns (dpi, True) if the file has a usable value, otherwise (DEFAULT_DPI, False).
    Values below 50 are not real scan resolutions (some programs write 1 when none is known)."""
    with Image.open(path) as img:
        dpi = img.info.get("dpi", (None, None))
    if dpi and dpi[0] and float(dpi[0]) >= 50:
        return round(float(dpi[0])), True
    return settings.DEFAULT_DPI, False
