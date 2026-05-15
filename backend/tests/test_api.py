"""
tests/test_api.py
==================
Automated test suite for SalesIQ backend.
Run with: python -m pytest tests/ -v

Tests cover:
  - File upload (CSV, JSON, bad format)
  - Analytics endpoints (summary, revenue, categories, regions, reps, dax)
  - Data explorer (records, columns, sample)
  - Export endpoints (csv, xlsx, json, tsv, summary)
  - Filter logic
  - DAX engine unit tests
"""

import io
import json
import sys
import os
import pytest

# Make sure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from utils.dax_engine import DAXEngine
import pandas as pd

# ── Sample data ────────────────────────────────────────────────────────────────
SAMPLE_CSV = b"""Order ID,Date,Category,Product,Region,Sales Rep,Units,Unit Price,Revenue,Cost,Profit,Customer
1001,2024-01-05,Electronics,Laptop Pro,North,Alice,2,1299.99,2599.98,1800.00,799.98,TechCorp
1002,2024-01-07,Clothing,Jacket,South,Bob,5,89.99,449.95,225.00,224.95,FashionHub
1003,2024-02-10,Electronics,Headphones,East,Carol,8,149.99,1199.92,600.00,599.92,SoundWorld
1004,2024-03-12,Home & Garden,Thermostat,West,David,3,249.99,749.97,375.00,374.97,SmartHome
1005,2024-04-15,Food & Beverage,Coffee Set,North,Alice,20,34.99,699.80,350.00,349.80,CafeWorld
"""

SAMPLE_JSON = json.dumps({
    "sales": [
        {"order_id": "J001", "date": "2024-01-05", "category": "Electronics",
         "product": "Laptop", "region": "North", "sales_rep": "Alice",
         "units": 2, "revenue": 2599.98, "cost": 1800.00, "profit": 799.98},
        {"order_id": "J002", "date": "2024-02-10", "category": "Clothing",
         "product": "Jacket", "region": "South", "sales_rep": "Bob",
         "units": 5, "revenue": 449.95, "cost": 225.00, "profit": 224.95},
    ]
}).encode()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def session_id(client):
    """Upload sample CSV and return session_id for use in tests."""
    data = {"file": (io.BytesIO(SAMPLE_CSV), "test_sales.csv")}
    resp = client.post("/api/upload/file", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    return resp.get_json()["session_id"]


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & ROOT
# ══════════════════════════════════════════════════════════════════════════════

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SalesIQ" in r.get_json()["app"]


def test_docs(client):
    r = client.get("/api/docs")
    assert r.status_code == 200
    assert "endpoints" in r.get_json()


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

class TestUpload:

    def test_upload_csv_success(self, client):
        data = {"file": (io.BytesIO(SAMPLE_CSV), "sales.csv")}
        r = client.post("/api/upload/file", data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        body = r.get_json()
        assert body["success"] is True
        assert body["rows"] == 5
        assert "session_id" in body
        assert "filter_options" in body

    def test_upload_json_success(self, client):
        data = {"file": (io.BytesIO(SAMPLE_JSON), "sales.json")}
        r = client.post("/api/upload/file", data=data, content_type="multipart/form-data")
        assert r.status_code == 201
        assert r.get_json()["rows"] == 2

    def test_upload_no_file(self, client):
        r = client.post("/api/upload/file", data={}, content_type="multipart/form-data")
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_upload_bad_extension(self, client):
        data = {"file": (io.BytesIO(b"hello"), "bad_file.pdf")}
        r = client.post("/api/upload/file", data=data, content_type="multipart/form-data")
        assert r.status_code == 400

    def test_list_sessions(self, client, session_id):
        r = client.get("/api/upload/sessions")
        assert r.status_code == 200
        sessions = r.get_json()["sessions"]
        assert any(s["session_id"] == session_id for s in sessions)

    def test_get_session_info(self, client, session_id):
        r = client.get(f"/api/upload/session/{session_id}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["session_id"] == session_id
        assert body["rows"] == 5

    def test_get_session_not_found(self, client):
        r = client.get("/api/upload/session/NOTREAL")
        assert r.status_code == 404

    def test_delete_session(self, client, session_id):
        r = client.delete(f"/api/upload/session/{session_id}")
        assert r.status_code == 200
        assert r.get_json()["success"] is True

        # Confirm gone
        r2 = client.get(f"/api/upload/session/{session_id}")
        assert r2.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalytics:

    def test_summary(self, client, session_id):
        r = client.get(f"/api/analytics/summary?session_id={session_id}")
        assert r.status_code == 200
        body = r.get_json()
        kpis = body["kpis"]
        assert kpis["total_revenue"] > 0
        assert kpis["total_orders"] == 5
        assert "profit_margin_pct" in kpis

    def test_summary_with_filter(self, client, session_id):
        r = client.get(f"/api/analytics/summary?session_id={session_id}&region=North")
        assert r.status_code == 200
        body = r.get_json()
        assert body["filtered_rows"] == 2  # Alice North rows

    def test_revenue_monthly(self, client, session_id):
        r = client.get(f"/api/analytics/revenue?session_id={session_id}&period=monthly")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1
        assert "revenue" in data[0]
        assert "profit" in data[0]

    def test_revenue_bad_period(self, client, session_id):
        r = client.get(f"/api/analytics/revenue?session_id={session_id}&period=weekly")
        assert r.status_code == 400

    def test_categories(self, client, session_id):
        r = client.get(f"/api/analytics/categories?session_id={session_id}")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1
        assert "category" in data[0]
        assert "margin_pct" in data[0]

    def test_regions(self, client, session_id):
        r = client.get(f"/api/analytics/regions?session_id={session_id}")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert any(d["region"] == "North" for d in data)

    def test_reps(self, client, session_id):
        r = client.get(f"/api/analytics/reps?session_id={session_id}")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) >= 1

    def test_products(self, client, session_id):
        r = client.get(f"/api/analytics/products?session_id={session_id}&n=3")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data) <= 3

    def test_dax(self, client, session_id):
        r = client.get(f"/api/analytics/dax?session_id={session_id}")
        assert r.status_code == 200
        measures = r.get_json()["measures"]
        names = [m["name"] for m in measures]
        assert "Total Revenue" in names
        assert "Profit Margin %" in names

    def test_filters_endpoint(self, client, session_id):
        r = client.get(f"/api/analytics/filters?session_id={session_id}")
        assert r.status_code == 200
        opts = r.get_json()["filter_options"]
        assert "region" in opts
        assert "category" in opts

    def test_no_session(self, client):
        r = client.get("/api/analytics/summary?session_id=FAKEID")
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# DATA EXPLORER
# ══════════════════════════════════════════════════════════════════════════════

class TestData:

    def test_records_default(self, client, session_id):
        r = client.get(f"/api/data/records?session_id={session_id}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["total"] == 5
        assert len(body["records"]) == 5

    def test_records_pagination(self, client, session_id):
        r = client.get(f"/api/data/records?session_id={session_id}&page=1&page_size=2")
        assert r.status_code == 200
        body = r.get_json()
        assert len(body["records"]) == 2
        assert body["pages"] == 3

    def test_records_filter(self, client, session_id):
        r = client.get(f"/api/data/records?session_id={session_id}&category=Electronics")
        assert r.status_code == 200
        records = r.get_json()["records"]
        assert all(rec["category"] == "Electronics" for rec in records)

    def test_records_sort(self, client, session_id):
        r = client.get(f"/api/data/records?session_id={session_id}&sort_by=revenue&sort_dir=desc")
        assert r.status_code == 200
        records = r.get_json()["records"]
        revenues = [rec["revenue"] for rec in records]
        assert revenues == sorted(revenues, reverse=True)

    def test_columns(self, client, session_id):
        r = client.get(f"/api/data/columns?session_id={session_id}")
        assert r.status_code == 200
        cols = r.get_json()["columns"]
        col_names = [c["name"] for c in cols]
        assert "revenue" in col_names

    def test_sample(self, client, session_id):
        r = client.get(f"/api/data/sample?session_id={session_id}&n=2")
        assert r.status_code == 200
        records = r.get_json()["records"]
        assert len(records) == 2


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════════

class TestExport:

    def test_export_csv(self, client, session_id):
        r = client.get(f"/api/export/csv?session_id={session_id}")
        assert r.status_code == 200
        assert "text/csv" in r.content_type
        assert b"revenue" in r.data.lower()

    def test_export_json(self, client, session_id):
        r = client.get(f"/api/export/json?session_id={session_id}")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "data" in body
        assert body["records"] == 5

    def test_export_tsv(self, client, session_id):
        r = client.get(f"/api/export/tsv?session_id={session_id}")
        assert r.status_code == 200
        assert b"\t" in r.data

    def test_export_xlsx(self, client, session_id):
        r = client.get(f"/api/export/xlsx?session_id={session_id}")
        assert r.status_code == 200
        assert b"xl/" in r.data or len(r.data) > 1000  # xlsx binary

    def test_export_summary(self, client, session_id):
        r = client.get(f"/api/export/summary?session_id={session_id}")
        assert r.status_code == 200
        assert b"SALESIQ" in r.data
        assert b"Total Revenue" in r.data or b"total_revenue" in r.data.lower()

    def test_export_with_filter(self, client, session_id):
        r = client.get(f"/api/export/csv?session_id={session_id}&region=North")
        assert r.status_code == 200
        lines = r.data.decode().strip().split("\n")
        # Header + 2 North rows
        assert len(lines) == 3


# ══════════════════════════════════════════════════════════════════════════════
# DAX ENGINE (unit tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestDAXEngine:

    @pytest.fixture
    def engine(self):
        df = pd.DataFrame([
            {"revenue": 1000.0, "profit": 400.0, "cost": 600.0, "units": 10,
             "category": "Electronics", "product": "Laptop", "rep": "Alice",
             "date": pd.Timestamp("2024-01-15")},
            {"revenue": 500.0,  "profit": 150.0, "cost": 350.0, "units": 5,
             "category": "Clothing",    "product": "Jacket", "rep": "Bob",
             "date": pd.Timestamp("2024-02-10")},
            {"revenue": 300.0,  "profit": 120.0, "cost": 180.0, "units": 3,
             "category": "Electronics", "product": "Headphones", "rep": "Alice",
             "date": pd.Timestamp("2024-02-20")},
        ])
        return DAXEngine(df)

    def test_total_revenue(self, engine):
        assert engine.total_revenue() == 1800.0

    def test_total_profit(self, engine):
        assert engine.total_profit() == 670.0

    def test_profit_margin(self, engine):
        expected = round(670 / 1800 * 100, 2)
        assert engine.profit_margin_pct() == expected

    def test_avg_order_value(self, engine):
        assert engine.avg_order_value() == round(1800 / 3, 2)

    def test_revenue_per_unit(self, engine):
        assert engine.revenue_per_unit() == round(1800 / 18, 2)

    def test_top_category(self, engine):
        assert engine.top_category() == "Electronics"

    def test_top_rep(self, engine):
        assert engine.top_rep() == "Alice"

    def test_safe_div_zero(self, engine):
        assert engine._safe_div(100, 0) == 0

    def test_all_measures_returns_list(self, engine):
        measures = engine.all_measures()
        assert isinstance(measures, list)
        assert len(measures) >= 15
        for m in measures:
            assert "name" in m and "dax" in m and "value" in m

    def test_mom_growth(self, engine):
        mom = engine.mom_revenue_growth()
        assert isinstance(mom, dict)

    def test_running_total(self, engine):
        rt = engine.running_total_revenue()
        assert len(rt) >= 2
        # Cumulative should be increasing
        vals = [r["revenue"] for r in rt]
        assert vals == sorted(vals)
