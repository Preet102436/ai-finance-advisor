"""
SQLAlchemy ORM models mirroring db/schema.sql.

These describe the tables for querying purposes only - the tables themselves
are created by running db/schema.sql directly against Postgres (see
backend/api/README.md), not by SQLAlchemy migrations.
"""

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    data_processing_consent = Column(Boolean, nullable=False, default=False, server_default="false")
    ai_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    phone = Column(String(30))
    address = Column(String(255))
    monthly_income = Column(Numeric(12, 2))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    account_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    provider_name = Column(String(100), nullable=False)
    external_ref = Column(String(255), nullable=False)
    account_type = Column(String(50))
    account_number_display = Column(String(50))
    currency = Column(String(10), default="AUD")
    linked_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    parent_category = Column(Integer, ForeignKey("categories.category_id"))


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.account_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255))
    merchant = Column(String(150))
    txn_date = Column(Date, nullable=False)
    source = Column(String(20), nullable=False, default="bank_sync")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id", ondelete="CASCADE"))
    image_path = Column(String(255), nullable=False)
    ocr_raw_text = Column(Text)
    processed_at = Column(TIMESTAMP)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category_id", "period_month"),)

    budget_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    period_month = Column(Date, nullable=False)
    recommended_amount = Column(Numeric(12, 2), nullable=False)
    generated_by = Column(String(20), nullable=False, default="ai_engine")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class Forecast(Base):
    __tablename__ = "forecasts"

    forecast_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    forecast_date = Column(Date, nullable=False)
    predicted_balance = Column(Numeric(12, 2), nullable=False)
    lower_bound = Column(Numeric(12, 2))
    upper_bound = Column(Numeric(12, 2))
    model_version = Column(String(50))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class Anomaly(Base):
    __tablename__ = "anomalies"

    anomaly_id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id"), nullable=False)
    anomaly_score = Column(Numeric(6, 4), nullable=False)
    reason = Column(String(255))
    detected_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    retrieved_context = Column(Text)
    rating = Column(String(10))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
