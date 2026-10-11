"""
Expense Tracking & OCR Subsystem - Receipt OCR Prototype
Owner: Preetkumar Navinbhai Patel

Extracts text from a receipt image using Tesseract OCR, then applies a simple
keyword-based classifier to guess a spending category. This is a prototype-stage
placeholder for what will later become a trained NLP classifier.

Requires: pip install pytesseract pillow --break-system-packages
          (and the tesseract-ocr system binary installed)

Usage:
    python ocr_prototype.py --image sample_receipt.jpg
"""

import argparse
import os
import re
import shutil
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageOps
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Default install locations for the Tesseract binary on Windows, where the
# installer doesn't add it to PATH. Checked only when TESSERACT_CMD isn't
# set and `tesseract` isn't already on PATH.
WINDOWS_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# Receipts are usually small and photographed at an angle - anything
# narrower than this is upscaled before OCR so Tesseract can read it.
MIN_OCR_WIDTH = 1000


class OCRUnavailableError(RuntimeError):
    """The OCR engine (pytesseract / the tesseract binary) can't be used."""


class InvalidImageError(ValueError):
    """The uploaded file isn't an image Pillow can open."""


CATEGORY_KEYWORDS = {
    "groceries": [
        "woolworths", "coles", "aldi", "iga", "foodland", "supermarket",
        "grocery", "market",
    ],
    "dining": [
        "cafe", "restaurant", "coffee", "kitchen", "diner", "eatery", "bar",
        "pizzeria", "bakery", "bistro", "takeaway",
    ],
    "utilities": [
        "electricity", "gas", "water", "energy", "telco", "internet",
        "broadband", "council rates",
    ],
    "transport": [
        "uber", "taxi", "fuel", "petrol", "parking", "transit", "myki",
        "opal", "train", "bus", "lyft", "rideshare",
    ],
    "entertainment": [
        "cinema", "movie", "netflix", "spotify", "theatre", "concert",
    ],
    "health": [
        "pharmacy", "chemist", "clinic", "medical", "doctor", "dental",
    ],
    "shopping": [
        "kmart", "target", "big w", "amazon", "retail", "department store",
    ],
}


def _configure_tesseract():
    """Point pytesseract at the tesseract binary. Honours TESSERACT_CMD
    (see backend/api/.env.example), then PATH, then the default Windows
    install locations."""
    configured = os.getenv("TESSERACT_CMD")
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
        return
    if shutil.which("tesseract"):
        return
    for candidate in WINDOWS_TESSERACT_PATHS:
        if Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def _prepare_image(image):
    """Light clean-up that makes phone photos of receipts far more
    readable: honour the EXIF rotation, convert to greyscale, upscale small
    images, and stretch the contrast."""
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    if image.width < MIN_OCR_WIDTH:
        scale = MIN_OCR_WIDTH / image.width
        image = image.resize((MIN_OCR_WIDTH, int(image.height * scale)), Image.LANCZOS)
    return ImageOps.autocontrast(image)


def extract_text(image_path):
    if not OCR_AVAILABLE:
        raise OCRUnavailableError(
            "pytesseract/Pillow not installed. Run: pip install pytesseract pillow"
        )
    try:
        with Image.open(image_path) as raw:
            image = _prepare_image(raw)
    except (OSError, ValueError) as exc:
        raise InvalidImageError("That file isn't a readable image.") from exc

    _configure_tesseract()
    try:
        text = pytesseract.image_to_string(image)
        # Block mode reads a single column of text, which suits most
        # receipts - used as a second pass when the default layout misses
        # the total.
        if extract_total(text) is None:
            text_block = pytesseract.image_to_string(image, config="--psm 6")
            if extract_total(text_block) is not None:
                text = text_block
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError(
            "Tesseract is not installed or not on PATH. Install it, or set "
            "TESSERACT_CMD in backend/api/.env to the tesseract executable."
        ) from exc
    return text


# A money amount like 45.20, $1,234.50, 45,20 or 45. 20 (common OCR slip).
_AMOUNT = r"\$?\s*(\d{1,3}(?:[,\s]\d{3})*|\d+)\s?[.,]\s?(\d{2})(?!\d)"
_TOTAL_LINE = re.compile(
    r"(grand\s*total|total\s*due|amount\s*due|balance\s*due|total)", re.IGNORECASE
)
_NOT_TOTAL = re.compile(r"sub\s*-?\s*total|total\s*(savings|discount|items|qty|gst|tax)", re.IGNORECASE)


def _parse_amount(whole, cents):
    return float(re.sub(r"[,\s]", "", whole) + "." + cents)


def extract_total(raw_text):
    """Find the receipt total: the last line labelled total / amount due
    (ignoring subtotal, GST and savings lines) that has an amount on it.
    Falls back to the largest amount on the receipt if no line is labelled."""
    if not raw_text:
        return None
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    total = None
    for line in lines:
        if not _TOTAL_LINE.search(line) or _NOT_TOTAL.search(line):
            continue
        amounts = re.findall(_AMOUNT, line)
        if amounts:
            total = _parse_amount(*amounts[-1])
    if total is not None:
        return total

    if not any(_TOTAL_LINE.search(line) for line in lines):
        return None
    all_amounts = [_parse_amount(*a) for line in lines for a in re.findall(_AMOUNT, line)]
    return max(all_amounts) if all_amounts else None


def extract_merchant(raw_text):
    """Best guess at the store name: the first line with a few letters in it."""
    for line in (raw_text or "").splitlines():
        line = line.strip()
        if len(re.findall(r"[A-Za-z]", line)) >= 3:
            return line[:150]
    return None


def classify_category(raw_text):
    text_lower = raw_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "uncategorised"


def process_receipt(image_path):
    raw_text = extract_text(image_path)
    return {
        "raw_text": raw_text.strip(),
        "predicted_total": extract_total(raw_text),
        "predicted_category": classify_category(raw_text),
    }


def process_receipt_from_text(raw_text):
    """Testing helper - lets us exercise the classifier without a real image/OCR
    engine installed, using text that OCR would typically produce."""
    return {
        "raw_text": raw_text.strip(),
        "predicted_total": extract_total(raw_text),
        "predicted_category": classify_category(raw_text),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Path to a receipt image")
    parser.add_argument("--text", help="Raw OCR-style text, for testing without an image")
    args = parser.parse_args()

    if args.text:
        result = process_receipt_from_text(args.text)
    elif args.image:
        result = process_receipt(args.image)
    else:
        # Fallback demo using sample OCR-style text
        sample_text = "WOOLWORTHS SUPERMARKET\nMilk 3.50\nBread 4.20\nTOTAL   45.20"
        print("No --image or --text given, running demo with sample text.\n")
        result = process_receipt_from_text(sample_text)

    print("Predicted category:", result["predicted_category"])
    print("Predicted total:", result["predicted_total"])
    print("Raw text:\n", result["raw_text"])
