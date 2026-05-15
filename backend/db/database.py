"""
db/database.py
==============
Neon PostgreSQL connection via SQLAlchemy.
Handles connection pooling, session management, and table creation.

Neon DB URL format:
  postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
"""

import os
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, Text, func, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool
from datetime import datetime

Base = declarative_base()

# ── Models ─────────────────────────────────────────────────────────────────────

class SalesRecord(Base):
    """Stores each uploaded sales row."""
    __tablename__ = "sales_records"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    session_id  = Column(String(64),  nullable=False, index=True)
    order_id    = Column(String(64))
    date        = Column(DateTime)
    category    = Column(String(128))
    product     = Column(String(256))
    region      = Column(String(128))
    rep         = Column(String(128))
    units       = Column(Float, default=0)
    unit_price  = Column(Float, default=0)
    revenue     = Column(Float, default=0)
    cost        = Column(Float, default=0)
    profit      = Column(Float, default=0)
    customer    = Column(String(256))
    created_at  = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.order_id or self.id,
            "date":       self.date.strftime("%Y-%m-%d") if self.date else None,
            "category":   self.category,
            "product":    self.product,
            "region":     self.region,
            "rep":        self.rep,
            "units":      self.units,
            "unit_price": self.unit_price,
            "revenue":    self.revenue,
            "cost":       self.cost,
            "profit":     self.profit,
            "customer":   self.customer,
        }


class UploadSession(Base):
    """Tracks each file upload session."""
    __tablename__ = "upload_sessions"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(String(64), unique=True, nullable=False, index=True)
    filename     = Column(String(256))
    rows         = Column(Integer, default=0)
    columns_json = Column(Text)          # JSON list of column names
    uploaded_at  = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "session_id":  self.session_id,
            "filename":    self.filename,
            "rows":        self.rows,
            "columns":     json.loads(self.columns_json or "[]"),
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ── Engine & Session Factory ───────────────────────────────────────────────────

_engine  = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv("DATABASE_URL", "")

        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set.\n"
                "Add it to your .env file:\n"
                "DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require"
            )

        # Neon requires SSL; NullPool works best for serverless (Vercel)
        _engine = create_engine(
            db_url,
            poolclass=NullPool,
            connect_args={"sslmode": "require"} if "neon.tech" in db_url else {},
        )
    return _engine


def get_session() -> Session:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db():
    """Create all tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ Database tables created (or already exist)")


def test_connection() -> bool:
    """Returns True if DB connection works."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False
