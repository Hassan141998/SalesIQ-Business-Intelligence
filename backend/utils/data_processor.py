"""
utils/data_processor.py
========================
Core data processing engine.
Handles file parsing, normalization, filtering, and aggregation.
"""

import pandas as pd
import numpy as np
import json
import os
import uuid
from datetime import datetime
from typing import Optional

# ── Field name aliases (auto-detect column names) ──────────────────────────────
FIELD_MAP = {
    "id":         ["Order ID", "order_id", "OrderID", "id", "ID", "order id"],
    "date":       ["Date", "date", "OrderDate", "order_date", "Order Date"],
    "category":   ["Category", "category", "ProductCategory", "product_category"],
    "product":    ["Product", "product", "ProductName", "product_name", "Product Name"],
    "region":     ["Region", "region", "Territory", "territory"],
    "rep":        ["Sales Rep", "sales_rep", "SalesRep", "Rep", "rep", "Salesperson"],
    "units":      ["Units", "units", "Quantity", "quantity", "Qty", "qty"],
    "unit_price": ["Unit Price", "unit_price", "UnitPrice", "Price", "price"],
    "revenue":    ["Revenue", "revenue", "Sales", "sales", "Amount", "amount"],
    "cost":       ["Cost", "cost", "COGS", "cogs"],
    "profit":     ["Profit", "profit", "Net Profit", "net_profit"],
    "customer":   ["Customer", "customer", "CustomerName", "customer_name", "Client"],
}

# In-memory session store  {session_id: {"df": DataFrame, "filename": str, "uploaded_at": str}}
_sessions: dict = {}


# ── File Parsing ───────────────────────────────────────────────────────────────

def parse_file(filepath: str, filename: str, use_db: bool = False) -> tuple[pd.DataFrame, str]:
    """
    Parse uploaded file into a DataFrame.
    Returns (df, session_id).
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(filepath, sheet_name=0)
    elif ext == "json":
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Support: array, {"data":[...]}, {"sales":[...]}, {"records":[...]}
        if isinstance(raw, list):
            df = pd.DataFrame(raw)
        elif isinstance(raw, dict):
            for key in ("data", "sales", "records", "orders", "results"):
                if key in raw and isinstance(raw[key], list):
                    df = pd.DataFrame(raw[key])
                    break
            else:
                df = pd.DataFrame(list(raw.values())[0] if raw else [])
        else:
            raise ValueError("Unsupported JSON structure")
    elif ext == "tsv":
        df = pd.read_csv(filepath, sep="\t", encoding="utf-8", on_bad_lines="skip")
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    df = normalize_columns(df)
    df = clean_dataframe(df)

    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "df":           df,
        "filename":     filename,
        "uploaded_at":  datetime.now().isoformat(),
        "rows":         len(df),
        "columns":      list(df.columns),
    }
    return df, session_id


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename detected columns to standard internal names."""
    col_lower = {c.strip().lower(): c for c in df.columns}
    rename_map = {}
    for standard, aliases in FIELD_MAP.items():
        for alias in aliases:
            if alias.lower() in col_lower:
                rename_map[col_lower[alias.lower()]] = standard
                break
    return df.rename(columns=rename_map)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Parse types, fill missing computed fields, drop empty rows."""
    df.columns = [str(c).strip() for c in df.columns]

    # Parse date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Numeric coercion
    for col in ("units", "unit_price", "revenue", "cost", "profit"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Derive revenue if missing
    if "revenue" not in df.columns:
        if "units" in df.columns and "unit_price" in df.columns:
            df["revenue"] = df["units"] * df["unit_price"]
        else:
            df["revenue"] = 0

    # Derive profit if missing
    if "profit" not in df.columns:
        if "cost" in df.columns:
            df["profit"] = df["revenue"] - df["cost"]
        else:
            df["profit"] = 0

    # Derive cost if missing
    if "cost" not in df.columns:
        df["cost"] = df["revenue"] - df["profit"]

    # String columns
    for col in ("category", "product", "region", "rep", "customer"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", "")

    # Drop rows with no meaningful data
    df = df[df["revenue"] > 0].reset_index(drop=True)

    # Ensure id column
    if "id" not in df.columns:
        df["id"] = range(1001, 1001 + len(df))

    return df


# ── Session Management ─────────────────────────────────────────────────────────

def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)

def get_session_df(session_id: str) -> Optional[pd.DataFrame]:
    s = _sessions.get(session_id)
    return s["df"].copy() if s else None

def list_sessions() -> list:
    return [
        {
            "session_id":  sid,
            "filename":    s["filename"],
            "uploaded_at": s["uploaded_at"],
            "rows":        s["rows"],
        }
        for sid, s in _sessions.items()
    ]

def delete_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False

def get_latest_session_id() -> Optional[str]:
    if not _sessions:
        return None
    return list(_sessions.keys())[-1]


# ── Filtering ──────────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Apply query filters to a DataFrame.
    params keys: region, category, rep, date_from, date_to, search
    """
    if params.get("region"):
        df = df[df["region"].str.lower() == params["region"].lower()]

    if params.get("category"):
        df = df[df["category"].str.lower() == params["category"].lower()]

    if params.get("rep"):
        df = df[df["rep"].str.lower() == params["rep"].lower()]

    if params.get("date_from") and "date" in df.columns:
        df = df[df["date"] >= pd.to_datetime(params["date_from"])]

    if params.get("date_to") and "date" in df.columns:
        df = df[df["date"] <= pd.to_datetime(params["date_to"]) + pd.Timedelta(days=1)]

    if params.get("search"):
        q = params["search"].lower()
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1)
        df = df[mask]

    return df.reset_index(drop=True)


# ── KPI Calculations ───────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    revenue  = float(df["revenue"].sum())
    profit   = float(df["profit"].sum())
    cost     = float(df["cost"].sum())
    units    = int(df["units"].sum()) if "units" in df.columns else 0
    orders   = len(df)
    margin   = (profit / revenue * 100) if revenue > 0 else 0
    avg_order= revenue / orders if orders > 0 else 0
    avg_units= units / orders if orders > 0 else 0

    top_cat = ""
    if "category" in df.columns:
        cat_rev = df.groupby("category")["revenue"].sum()
        if not cat_rev.empty:
            top_cat = cat_rev.idxmax()

    date_range = {}
    if "date" in df.columns:
        valid = df["date"].dropna()
        if not valid.empty:
            date_range = {
                "from": valid.min().strftime("%Y-%m-%d"),
                "to":   valid.max().strftime("%Y-%m-%d"),
            }

    return {
        "total_revenue":    round(revenue, 2),
        "total_profit":     round(profit, 2),
        "total_cost":       round(cost, 2),
        "total_units":      units,
        "total_orders":     orders,
        "profit_margin_pct":round(margin, 2),
        "avg_order_value":  round(avg_order, 2),
        "avg_units_per_order": round(avg_units, 2),
        "top_category":     top_cat,
        "date_range":       date_range,
    }


# ── Aggregations ───────────────────────────────────────────────────────────────

def revenue_over_time(df: pd.DataFrame, period: str = "monthly") -> list:
    if "date" not in df.columns:
        return []
    tmp = df.dropna(subset=["date"]).copy()
    if period == "monthly":
        tmp["period"] = tmp["date"].dt.to_period("M").astype(str)
    elif period == "quarterly":
        tmp["period"] = tmp["date"].dt.to_period("Q").astype(str)
    else:
        tmp["period"] = tmp["date"].dt.year.astype(str)

    grp = tmp.groupby("period").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        cost=("cost", "sum"),
        orders=("revenue", "count"),
        units=("units", "sum") if "units" in tmp.columns else ("revenue", "count"),
    ).reset_index().sort_values("period")

    return grp.round(2).to_dict(orient="records")


def by_category(df: pd.DataFrame) -> list:
    if "category" not in df.columns:
        return []
    grp = df.groupby("category").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        cost=("cost", "sum"),
        orders=("revenue", "count"),
    ).reset_index()
    grp["margin_pct"] = (grp["profit"] / grp["revenue"] * 100).round(2)
    return grp.sort_values("revenue", ascending=False).round(2).to_dict(orient="records")


def by_region(df: pd.DataFrame) -> list:
    if "region" not in df.columns:
        return []
    grp = df.groupby("region").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("revenue", "count"),
    ).reset_index()
    total = grp["revenue"].sum()
    grp["pct_of_total"] = (grp["revenue"] / total * 100).round(2) if total > 0 else 0
    return grp.sort_values("revenue", ascending=False).round(2).to_dict(orient="records")


def by_rep(df: pd.DataFrame) -> list:
    if "rep" not in df.columns:
        return []
    grp = df.groupby("rep").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("revenue", "count"),
        units=("units", "sum") if "units" in df.columns else ("revenue", "count"),
    ).reset_index()
    grp["margin_pct"] = (grp["profit"] / grp["revenue"] * 100).round(2)
    return grp.sort_values("revenue", ascending=False).round(2).to_dict(orient="records")


def top_products(df: pd.DataFrame, n: int = 10) -> list:
    if "product" not in df.columns:
        return []
    grp = df.groupby("product").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        units=("units", "sum") if "units" in df.columns else ("revenue", "count"),
        orders=("revenue", "count"),
    ).reset_index()
    grp["margin_pct"] = (grp["profit"] / grp["revenue"] * 100).round(2)
    return grp.sort_values("revenue", ascending=False).head(n).round(2).to_dict(orient="records")


def dax_measures(df: pd.DataFrame) -> list:
    """Compute Power BI DAX-equivalent measures."""
    revenue = float(df["revenue"].sum())
    profit  = float(df["profit"].sum())
    cost    = float(df["cost"].sum())
    units   = float(df["units"].sum()) if "units" in df.columns else 0
    orders  = len(df)

    safe = lambda n, d: round(n / d, 4) if d != 0 else 0

    return [
        {"name": "Total Revenue",         "formula": "SUM(Revenue)",                                   "value": round(revenue, 2),                    "unit": "$"},
        {"name": "Total Profit",          "formula": "SUM(Profit)",                                    "value": round(profit, 2),                     "unit": "$"},
        {"name": "Total Cost",            "formula": "SUM(Cost)",                                      "value": round(cost, 2),                       "unit": "$"},
        {"name": "Profit Margin %",       "formula": "DIVIDE(SUM(Profit), SUM(Revenue)) * 100",        "value": round(safe(profit, revenue) * 100, 2),"unit": "%"},
        {"name": "Cost Ratio %",          "formula": "DIVIDE(SUM(Cost), SUM(Revenue)) * 100",          "value": round(safe(cost, revenue) * 100, 2),  "unit": "%"},
        {"name": "Avg Order Value",       "formula": "DIVIDE(SUM(Revenue), COUNTROWS())",              "value": round(safe(revenue, orders), 2),      "unit": "$"},
        {"name": "Revenue per Unit",      "formula": "DIVIDE(SUM(Revenue), SUM(Units))",               "value": round(safe(revenue, units), 2),       "unit": "$"},
        {"name": "Profit per Order",      "formula": "DIVIDE(SUM(Profit), COUNTROWS())",               "value": round(safe(profit, orders), 2),       "unit": "$"},
        {"name": "Units per Order",       "formula": "DIVIDE(SUM(Units), COUNTROWS())",                "value": round(safe(units, orders), 2),        "unit": "units"},
        {"name": "Total Orders",          "formula": "COUNTROWS(Sales)",                               "value": orders,                               "unit": ""},
        {"name": "Total Units Sold",      "formula": "SUM(Units)",                                     "value": int(units),                           "unit": "units"},
        {"name": "Gross Margin $",        "formula": "SUM(Revenue) - SUM(Cost)",                       "value": round(revenue - cost, 2),             "unit": "$"},
    ]


# ── Pagination / Sorting ───────────────────────────────────────────────────────

def paginate(df: pd.DataFrame, page: int = 1, page_size: int = 20,
             sort_by: str = None, sort_dir: str = "asc") -> dict:
    total = len(df)

    if sort_by and sort_by in df.columns:
        ascending = sort_dir.lower() != "desc"
        df = df.sort_values(sort_by, ascending=ascending)

    start = (page - 1) * page_size
    end   = start + page_size
    page_df = df.iloc[start:end].copy()

    # Serialize dates
    if "date" in page_df.columns:
        page_df["date"] = page_df["date"].dt.strftime("%Y-%m-%d").where(page_df["date"].notna(), None)

    records = page_df.replace({np.nan: None}).to_dict(orient="records")

    return {
        "records":    records,
        "total":      total,
        "page":       page,
        "page_size":  page_size,
        "pages":      max(1, -(-total // page_size)),  # ceiling div
    }


# ── Filter Options ─────────────────────────────────────────────────────────────

def get_filter_options_from_df(df: pd.DataFrame) -> dict:
    return get_filter_options(df)


def get_filter_options(df: pd.DataFrame) -> dict:
    opts = {}
    for col in ("region", "category", "rep", "customer"):
        if col in df.columns:
            opts[col] = sorted(df[col].dropna().unique().tolist())
    return opts
