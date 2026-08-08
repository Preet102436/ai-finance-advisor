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
import re

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

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


def extract_text(image_path):
    if not OCR_AVAILABLE:
        raise RuntimeError(
            "pytesseract/Pillow not installed. Run: "
            "pip install pytesseract pillow --break-system-packages"
        )
    image = Image.open(image_path)
    return pytesseract.image_to_string(image)


def extract_total(raw_text):
    """Very simple heuristic: find a line containing 'total' followed by a number."""
    match = re.search(r"total[^\d]{0,10}(\d+\.\d{2})", raw_text, re.IGNORECASE)
    return float(match.group(1)) if match else None


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
