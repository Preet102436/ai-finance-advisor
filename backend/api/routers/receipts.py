"""Stub router for /receipts - not implemented yet.

TODO:
- POST /receipts               upload a receipt image, store it, run OCR (see
                                backend/expense-ocr/ocr_prototype.py), create a
                                transactions row with source='receipt_ocr'
- GET  /receipts                list current user's receipts
- GET  /receipts/{id}           fetch a receipt (incl. ocr_raw_text, linked transaction)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/receipts", tags=["receipts"])
