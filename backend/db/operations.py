"""
db/operations.py
=================
All database read/write operations.
Replaces the in-memory session store with persistent Neon PostgreSQL.
"""

import json
import uuid
import pandas as pd
from datetime import datetime
from sqlalchemy import func, distinct, and_, or_
from sqlalchemy.orm import Session

from db.database import get_session, SalesRecord, UploadSession


# ── Write ──────────────────────────────────────────────────────────────────────

def save_upload_session(df: pd.DataFrame, filename: str) -> str:
    """
    Persist all rows of a DataFrame to Neon DB.
    Returns the new session_id.
    """
    session_id = str(uuid.uuid4())[:8]
    db: Session = get_session()

    try:
        # Save session metadata
        col_list = json.dumps(list(df.columns))
        upload   = UploadSession(
            session_id   = session_id,
            filename     = filename,
            rows         = len(df),
            columns_json = col_list,
        )
        db.add(upload)

        # Bulk insert all rows
        records = []
        for _, row in df.iterrows():
            rec = SalesRecord(
                session_id = session_id,
                order_id   = str(row.get("id", "")),
                date       = row.get("date") if pd.notna(row.get("date", None)) else None,
                category   = str(row.get("category", "")),
                product    = str(row.get("product", "")),
                region     = str(row.get("region", "")),
                rep        = str(row.get("rep", "")),
                units      = float(row.get("units", 0) or 0),
                unit_price = float(row.get("unit_price", 0) or 0),
                revenue    = float(row.get("revenue", 0) or 0),
                cost       = float(row.get("cost", 0) or 0),
                profit     = float(row.get("profit", 0) or 0),
                customer   = str(row.get("customer", "")),
            )
            records.append(rec)

        db.bulk_save_objects(records)
        db.commit()
        return session_id

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_session(session_id: str) -> bool:
    """Delete all rows and metadata for a session."""
    db = get_session()
    try:
        db.query(SalesRecord).filter_by(session_id=session_id).delete()
        rows = db.query(UploadSession).filter_by(session_id=session_id).delete()
        db.commit()
        return rows > 0
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ── Read Sessions ──────────────────────────────────────────────────────────────

def list_sessions() -> list:
    db = get_session()
    try:
        sessions = db.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).all()
        return [s.to_dict() for s in sessions]
    finally:
        db.close()


def get_session_info(session_id: str) -> dict | None:
    db = get_session()
    try:
        s = db.query(UploadSession).filter_by(session_id=session_id).first()
        return s.to_dict() if s else None
    finally:
        db.close()


def get_latest_session_id() -> str | None:
    db = get_session()
    try:
        s = db.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).first()
        return s.session_id if s else None
    finally:
        db.close()


# ── Query Builder ──────────────────────────────────────────────────────────────

def _base_query(db: Session, session_id: str, params: dict):
    """Build a filtered SQLAlchemy query for SalesRecord."""
    q = db.query(SalesRecord).filter(SalesRecord.session_id == session_id)

    if params.get("region"):
        q = q.filter(func.lower(SalesRecord.region) == params["region"].lower())
    if params.get("category"):
        q = q.filter(func.lower(SalesRecord.category) == params["category"].lower())
    if params.get("rep"):
        q = q.filter(func.lower(SalesRecord.rep) == params["rep"].lower())
    if params.get("date_from"):
        q = q.filter(SalesRecord.date >= datetime.strptime(params["date_from"], "%Y-%m-%d"))
    if params.get("date_to"):
        q = q.filter(SalesRecord.date <= datetime.strptime(params["date_to"], "%Y-%m-%d"))
    if params.get("search"):
        s = f"%{params['search']}%"
        q = q.filter(or_(
            SalesRecord.product.ilike(s),
            SalesRecord.category.ilike(s),
            SalesRecord.region.ilike(s),
            SalesRecord.rep.ilike(s),
            SalesRecord.customer.ilike(s),
        ))
    return q


# ── KPIs ───────────────────────────────────────────────────────────────────────

def compute_kpis(session_id: str, params: dict) -> dict:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        agg = q.with_entities(
            func.coalesce(func.sum(SalesRecord.revenue), 0).label("revenue"),
            func.coalesce(func.sum(SalesRecord.profit),  0).label("profit"),
            func.coalesce(func.sum(SalesRecord.cost),    0).label("cost"),
            func.coalesce(func.sum(SalesRecord.units),   0).label("units"),
            func.count(SalesRecord.id).label("orders"),
        ).one()

        revenue = float(agg.revenue)
        profit  = float(agg.profit)
        cost    = float(agg.cost)
        units   = int(agg.units)
        orders  = int(agg.orders)
        margin  = round(profit / revenue * 100, 2) if revenue else 0

        # Top category
        top_cat_row = (
            q.with_entities(SalesRecord.category, func.sum(SalesRecord.revenue).label("rev"))
            .group_by(SalesRecord.category).order_by(func.sum(SalesRecord.revenue).desc())
            .first()
        )

        # Date range
        dates = (
            q.with_entities(func.min(SalesRecord.date), func.max(SalesRecord.date)).one()
        )
        date_range = {}
        if dates[0]:
            date_range = {
                "from": dates[0].strftime("%Y-%m-%d"),
                "to":   dates[1].strftime("%Y-%m-%d"),
            }

        return {
            "total_revenue":       round(revenue, 2),
            "total_profit":        round(profit, 2),
            "total_cost":          round(cost, 2),
            "total_units":         units,
            "total_orders":        orders,
            "profit_margin_pct":   margin,
            "avg_order_value":     round(revenue / orders, 2) if orders else 0,
            "avg_units_per_order": round(units / orders, 2) if orders else 0,
            "top_category":        top_cat_row.category if top_cat_row else "",
            "date_range":          date_range,
        }
    finally:
        db.close()


# ── Aggregations ───────────────────────────────────────────────────────────────

def revenue_over_time(session_id: str, params: dict, period: str = "monthly") -> list:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)

        # PostgreSQL date truncation
        trunc = {"monthly": "month", "quarterly": "quarter", "yearly": "year"}.get(period, "month")

        rows = (
            q.with_entities(
                func.date_trunc(trunc, SalesRecord.date).label("period"),
                func.sum(SalesRecord.revenue).label("revenue"),
                func.sum(SalesRecord.profit).label("profit"),
                func.sum(SalesRecord.cost).label("cost"),
                func.count(SalesRecord.id).label("orders"),
                func.sum(SalesRecord.units).label("units"),
            )
            .group_by(func.date_trunc(trunc, SalesRecord.date))
            .order_by(func.date_trunc(trunc, SalesRecord.date))
            .all()
        )

        return [
            {
                "period":  r.period.strftime("%Y-%m") if period == "monthly"
                           else r.period.strftime("%Y-Q") + str((r.period.month - 1) // 3 + 1)
                           if period == "quarterly" else str(r.period.year),
                "revenue": round(float(r.revenue or 0), 2),
                "profit":  round(float(r.profit or 0), 2),
                "cost":    round(float(r.cost or 0), 2),
                "orders":  int(r.orders),
                "units":   int(r.units or 0),
            }
            for r in rows
        ]
    finally:
        db.close()


def by_category(session_id: str, params: dict) -> list:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        rows = (
            q.with_entities(
                SalesRecord.category,
                func.sum(SalesRecord.revenue).label("revenue"),
                func.sum(SalesRecord.profit).label("profit"),
                func.sum(SalesRecord.cost).label("cost"),
                func.count(SalesRecord.id).label("orders"),
            )
            .group_by(SalesRecord.category)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .all()
        )
        return [
            {
                "category":   r.category,
                "revenue":    round(float(r.revenue or 0), 2),
                "profit":     round(float(r.profit or 0), 2),
                "cost":       round(float(r.cost or 0), 2),
                "orders":     int(r.orders),
                "margin_pct": round(float(r.profit or 0) / float(r.revenue or 1) * 100, 2),
            }
            for r in rows
        ]
    finally:
        db.close()


def by_region(session_id: str, params: dict) -> list:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        rows = (
            q.with_entities(
                SalesRecord.region,
                func.sum(SalesRecord.revenue).label("revenue"),
                func.sum(SalesRecord.profit).label("profit"),
                func.count(SalesRecord.id).label("orders"),
            )
            .group_by(SalesRecord.region)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .all()
        )
        total = sum(float(r.revenue or 0) for r in rows)
        return [
            {
                "region":       r.region,
                "revenue":      round(float(r.revenue or 0), 2),
                "profit":       round(float(r.profit or 0), 2),
                "orders":       int(r.orders),
                "pct_of_total": round(float(r.revenue or 0) / total * 100, 2) if total else 0,
            }
            for r in rows
        ]
    finally:
        db.close()


def by_rep(session_id: str, params: dict) -> list:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        rows = (
            q.with_entities(
                SalesRecord.rep,
                func.sum(SalesRecord.revenue).label("revenue"),
                func.sum(SalesRecord.profit).label("profit"),
                func.sum(SalesRecord.units).label("units"),
                func.count(SalesRecord.id).label("orders"),
            )
            .group_by(SalesRecord.rep)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .all()
        )
        return [
            {
                "rep":        r.rep,
                "revenue":    round(float(r.revenue or 0), 2),
                "profit":     round(float(r.profit or 0), 2),
                "units":      int(r.units or 0),
                "orders":     int(r.orders),
                "margin_pct": round(float(r.profit or 0) / float(r.revenue or 1) * 100, 2),
            }
            for r in rows
        ]
    finally:
        db.close()


def top_products(session_id: str, params: dict, n: int = 10) -> list:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        rows = (
            q.with_entities(
                SalesRecord.product,
                func.sum(SalesRecord.revenue).label("revenue"),
                func.sum(SalesRecord.profit).label("profit"),
                func.sum(SalesRecord.units).label("units"),
                func.count(SalesRecord.id).label("orders"),
            )
            .group_by(SalesRecord.product)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .limit(n)
            .all()
        )
        return [
            {
                "product":    r.product,
                "revenue":    round(float(r.revenue or 0), 2),
                "profit":     round(float(r.profit or 0), 2),
                "units":      int(r.units or 0),
                "orders":     int(r.orders),
                "margin_pct": round(float(r.profit or 0) / float(r.revenue or 1) * 100, 2),
            }
            for r in rows
        ]
    finally:
        db.close()


def get_filter_options(session_id: str) -> dict:
    db = get_session()
    try:
        q = db.query(SalesRecord).filter_by(session_id=session_id)
        return {
            "region":   sorted(set(r.region   for r in q.with_entities(SalesRecord.region).distinct()   if r.region)),
            "category": sorted(set(r.category for r in q.with_entities(SalesRecord.category).distinct() if r.category)),
            "rep":      sorted(set(r.rep      for r in q.with_entities(SalesRecord.rep).distinct()      if r.rep)),
        }
    finally:
        db.close()


def get_records_paginated(session_id: str, params: dict,
                          page: int = 1, page_size: int = 20,
                          sort_by: str = "revenue", sort_dir: str = "desc") -> dict:
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        total = q.count()

        sort_col = getattr(SalesRecord, sort_by, SalesRecord.revenue)
        if sort_dir == "desc":
            q = q.order_by(sort_col.desc())
        else:
            q = q.order_by(sort_col.asc())

        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "records":   [r.to_dict() for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     max(1, -(-total // page_size)),
        }
    finally:
        db.close()


def get_all_records_df(session_id: str, params: dict) -> pd.DataFrame:
    """Return filtered records as DataFrame (for export)."""
    db = get_session()
    try:
        q = _base_query(db, session_id, params)
        rows = q.all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in rows])
    finally:
        db.close()
