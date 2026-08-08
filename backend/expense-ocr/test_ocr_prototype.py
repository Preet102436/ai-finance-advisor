"""
Unit tests for the receipt classifier in ocr_prototype.py
Owner: Preetkumar Navinbhai Patel

Run with:
    pytest backend/expense-ocr/test_ocr_prototype.py
"""

from ocr_prototype import process_receipt_from_text

SAMPLE_RECEIPTS = {
    "groceries": "WOOLWORTHS SUPERMARKET\nMilk 3.50\nBread 4.20\nTOTAL   45.20",
    "dining": "THE CORNER BISTRO\nPasta 18.00\nCoffee 4.50\nTOTAL   22.50",
    "transport": "UBER TRIP RECEIPT\nFare 14.30\nTOTAL   14.30",
    "entertainment": "HOYTS CINEMA\n2x Movie Tickets 32.00\nTOTAL   32.00",
    "health": "CITY CHEMIST PHARMACY\nVitamins 12.99\nTOTAL   12.99",
    "shopping": "KMART\nHousehold items 27.45\nTOTAL   27.45",
}


def test_classifies_known_categories_correctly():
    for expected_category, receipt_text in SAMPLE_RECEIPTS.items():
        result = process_receipt_from_text(receipt_text)
        assert result["predicted_category"] == expected_category


def test_extracts_total_from_sample_receipts():
    assert process_receipt_from_text(SAMPLE_RECEIPTS["dining"])["predicted_total"] == 22.50
    assert process_receipt_from_text(SAMPLE_RECEIPTS["entertainment"])["predicted_total"] == 32.00


def test_unmatched_text_is_uncategorised():
    result = process_receipt_from_text("RANDOM SHOP\nWidget 9.99\nTOTAL   9.99")
    assert result["predicted_category"] == "uncategorised"


def test_classification_is_case_insensitive():
    result = process_receipt_from_text("aldi grocery run\nTOTAL 15.00")
    assert result["predicted_category"] == "groceries"


def test_missing_total_returns_none():
    result = process_receipt_from_text("CAFE ROMA\nCoffee 4.50")
    assert result["predicted_total"] is None
