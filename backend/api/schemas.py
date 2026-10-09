"""Pydantic request/response models for the auth, users, budgets, and forecasts routes."""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BudgetOut(BaseModel):
    budget_id: int
    category_id: int
    category_name: str
    period_month: date
    recommended_amount: float
    months_considered: int
    generated_by: str


class BudgetCreate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)


class BudgetUpdate(BaseModel):
    amount: float = Field(gt=0)


class InsightOut(BaseModel):
    severity: str  # "info" | "warning" | "critical"
    message: str
    category_name: str | None = None


class ChatRatingUpdate(BaseModel):
    rating: str = Field(pattern="^(up|down)$")


class ForecastPoint(BaseModel):
    forecast_date: date
    predicted_balance: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(BaseModel):
    account_id: int
    method: str
    days_ahead: int
    forecast: list[ForecastPoint]


class CategoryOut(BaseModel):
    category_id: int
    name: str


class TransactionOut(BaseModel):
    transaction_id: int
    account_id: int
    category_id: int | None = None
    category_name: str | None = None
    amount: float
    description: str | None = None
    merchant: str | None = None
    txn_date: date
    source: str


class SavingsSuggestionOut(BaseModel):
    category: str
    overspend: float
    annual_savings: float
    top_merchant: str | None = None
    merchant_total_spent: float | None = None
    merchant_visit_count: int | None = None
    suggestion: str


class ConsentOut(BaseModel):
    data_processing_consent: bool


class ConsentUpdate(BaseModel):
    data_processing_consent: bool


class SettingsOut(BaseModel):
    data_processing_consent: bool
    ai_enabled: bool


class SettingsUpdate(BaseModel):
    data_processing_consent: bool | None = None
    ai_enabled: bool | None = None


class BankAccountOut(BaseModel):
    account_id: int
    provider_name: str
    account_type: str | None = None
    account_number_display: str | None = None
    currency: str | None = None
    linked_at: datetime


class AnomalyOut(BaseModel):
    anomaly_id: int
    transaction_id: int
    category_id: int
    category_name: str
    txn_date: date
    amount: float
    merchant: str | None = None
    z_score: float
    reason: str


class TransactionCreate(BaseModel):
    amount: float
    txn_date: date
    category_name: str | None = None
    merchant: str | None = None
    description: str | None = None
    account_id: int | None = None


class TransactionCategoryUpdate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)


class CsvImportRowError(BaseModel):
    row: int
    reason: str


class CsvImportResult(BaseModel):
    total_rows: int
    imported: int
    skipped: list[CsvImportRowError]


class ReceiptPreviewOut(BaseModel):
    receipt_id: int
    predicted_merchant: str | None = None
    predicted_total: float | None = None
    predicted_category: str
    predicted_date: date
    raw_text: str


class ReceiptConfirm(BaseModel):
    total: float
    category_name: str = Field(min_length=1, max_length=100)
    merchant: str | None = None
    txn_date: date


class ReceiptConfirmOut(BaseModel):
    receipt_id: int
    transaction_id: int
    category_name: str
    total: float


class ReceiptOut(BaseModel):
    receipt_id: int
    transaction_id: int | None = None
    ocr_raw_text: str | None = None
    processed_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    monthly_income: float | None = None


class UserProfileOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    monthly_income: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
