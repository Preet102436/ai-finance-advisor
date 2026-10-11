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
    phone: str | None = None
    date_of_birth: date | None = None
    location: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    location: str | None = Field(default=None, max_length=150)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=255)


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


class TransactionCreate(BaseModel):
    txn_date: date
    amount: float
    merchant: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=255)
    category_name: str | None = Field(default=None, max_length=100)


class TransactionUpdate(BaseModel):
    # All optional - only the fields actually sent get changed.
    txn_date: date | None = None
    amount: float | None = None
    merchant: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=255)
    category_name: str | None = Field(default=None, max_length=100)


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
    top_merchant: str | None = None
    merchant_total_spent: float | None = None
    merchant_visit_count: int | None = None
    suggestion: str


class ConsentOut(BaseModel):
    data_processing_consent: bool


class ConsentUpdate(BaseModel):
    data_processing_consent: bool


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
