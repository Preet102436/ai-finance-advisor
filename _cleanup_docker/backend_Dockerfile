# Builds the FastAPI backend (backend/api) plus the three sibling subsystem
# folders it imports from (expense-ocr, budgeting-forecasting, chatbot-savings).
# Build context must be the backend/ folder, not backend/api/, so all four are
# available - that's why docker-compose.yml at the repo root points context
# at "./backend".
FROM python:3.11-slim

# tesseract-ocr is the system binary pytesseract (in requirements.txt) wraps -
# needed for the receipt-upload OCR feature to actually work.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY . .

WORKDIR /app/api
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
