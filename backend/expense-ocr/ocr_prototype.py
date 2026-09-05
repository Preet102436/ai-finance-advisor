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
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
    # pytesseract shells out to the `tesseract` binary via PATH by default,
    # which Windows installs frequently don't add automatically. TESSERACT_CMD
    # (set in backend/api/.env, already loaded into the process environment
    # by the time this module is imported from the running app) points
    # straight at the binary so a PATH edit + terminal restart isn't required.
    if os.environ.get("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
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

KNOWN_CATEGORIES = list(CATEGORY_KEYWORDS.keys()) + ["uncategorised"]


def extract_text(image_path):
    if not OCR_AVAILABLE:
        raise RuntimeError(
            "pytesseract/Pillow not installed. Run: "
            "pip install pytesseract pillow --break-system-packages"
        )
    image = Image.open(image_path)
    return pytesseract.image_to_string(image)


def extract_total(raw_text):
    """Very simple heuristic: on the first line containing 'total', take the
    last two-decimal amount on that line. Real receipts often put a currency
    code (e.g. "Total :   CHF   54.50") or wide column-alignment whitespace
    between the label and the right-aligned amount, so this scans the whole
    line instead of capping the gap to a fixed number of characters."""
    for line in raw_text.splitlines():
        if "total" not in line.lower():
            continue
        amounts = re.findall(r"\d+\.\d{2}", line)
        if amounts:
            return float(amounts[-1])
    return None


def classify_category(raw_text):
    text_lower = raw_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "uncategorised"


def extract_receipt_fields_llm(raw_text):
    """Ask an LLM to pull {category, total} out of arbitrary OCR'd receipt
    text - handles the range of real-world receipt formats the fixed keyword
    list and regex below can't (foreign-language items/labels, a currency
    code or symbol in an unexpected place, no literal "TOTAL" line at all, a
    subtotal + tax + tip to reconcile, ...).

    Mirrors chatbot_prototype.py's call_llm(): same OPENAI_API_KEY env var,
    same "gpt-5" model, same offline behaviour - returns None (rather than
    raising) when no key is configured or the call fails for any reason, so
    extract_receipt_fields() below always has the heuristic fallback to use.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import openai
    except ImportError:
        return None

    prompt = f"""You extract structured data from OCR'd receipt text. The
text may be in any language, use any currency, and may not contain the word
"total" at all - use judgement to find the final amount actually paid
(after tax/tip if the receipt shows a breakdown, not a subtotal).

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{"total": <number or null>, "category": <string>}}

"total" must be null if you cannot find a total. "category" must be exactly
one of: {", ".join(KNOWN_CATEGORIES)} - use "uncategorised" if none clearly fit.

Receipt text:
{raw_text}
"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-5",
            # "gpt-5" is a reasoning model that spends completion tokens on
            # hidden reasoning before writing any visible output - 100 and
            # 500 were both seen to come back empty in practice, so this
            # gives it enough room to reason AND still write the JSON.
            max_completion_tokens=2000,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError(
                f"LLM returned no content (finish_reason={response.choices[0].finish_reason!r})"
            )
        data = json.loads(content)
    except Exception:
        logger.exception(
            "LLM receipt-field extraction failed; falling back to keyword/regex heuristics"
        )
        return None

    total = data.get("total")
    try:
        total = float(total) if total is not None else None
    except (TypeError, ValueError):
        total = None

    category = data.get("category")
    if category not in KNOWN_CATEGORIES:
        category = "uncategorised"

    return {"total": total, "category": category}


def extract_receipt_fields(raw_text):
    """Production entry point for /receipts/upload. Tries the LLM extraction
    above first - it generalises far better to receipt formats/languages the
    keyword+regex heuristics were never written for - and fills in whatever
    it leaves blank (or the whole result, if no OPENAI_API_KEY is configured
    or the call fails) from those heuristics, so a receipt is never rejected
    just because the LLM found one field but not the other."""
    llm_result = extract_receipt_fields_llm(raw_text)
    total = llm_result["total"] if llm_result else None
    category = llm_result["category"] if llm_result else "uncategorised"

    if total is None:
        total = extract_total(raw_text)
    if category == "uncategorised":
        category = classify_category(raw_text)

    return {"total": total, "category": category}


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
