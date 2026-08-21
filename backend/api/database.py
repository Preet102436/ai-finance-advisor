"""
Database connection layer - reads PostgreSQL connection details from .env and
exposes a SQLAlchemy engine/session for the rest of the app.

The schema itself is owned by db/schema.sql and applied manually with psql
(see backend/api/README.md) - this module does not create or migrate tables.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).resolve().parent / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "finance_advisor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Credentials are percent-encoded since a raw password/user containing
# characters like @, :, or # would otherwise corrupt the connection URL.
DATABASE_URL = (
    f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# pool_pre_ping avoids handing out dead connections; engine connects lazily,
# so the app can still start even if Postgres isn't reachable yet.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
