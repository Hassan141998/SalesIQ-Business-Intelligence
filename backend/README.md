# SalesIQ Backend — Flask REST API

Python/Flask backend for the SalesIQ Business Intelligence Dashboard.  
Provides file upload, data processing, analytics, and multi-format export via REST API.

---

## 🗂️ Project Structure

```
backend/
├── app.py                    ← Flask app entry point
├── config.py                 ← Environment-based configuration
├── requirements.txt          ← Python dependencies
├── seed_data.py              ← Generate sample data files
├── Procfile                  ← Gunicorn for production deployment
├── .env.example              ← Environment variable template
│
├── routes/
│   ├── upload.py             ← File upload endpoints
│   ├── analytics.py          ← KPI & chart data endpoints
│   ├── data.py               ← Data explorer (paginate/filter/sort)
│   └── export.py             ← Download in CSV/XLSX/JSON/TSV
│
├── utils/
│   ├── data_processor.py     ← Core: parse, normalize, filter, aggregate
│   └── dax_engine.py         ← Power BI DAX-equivalent measures in Python
│
├── tests/
│   └── test_api.py           ← 45 automated tests (pytest)
│
├── uploads/                  ← Uploaded files (auto-created)
└── exports/                  ← Export temp files (auto-created)
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env as needed
```

### 3. Generate sample data
```bash
python seed_data.py
```

### 4. Run the server
```bash
python app.py
```

Server starts at: **http://localhost:5000**  
API docs at: **http://localhost:5000/api/docs**

---

## 📡 API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | App info |
| GET | `/api/health` | Health check |
| GET | `/api/docs` | Full endpoint list |

---

### Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload/file` | Upload CSV/XLSX/JSON/TSV file |
| GET | `/api/upload/sessions` | List all data sessions |
| GET | `/api/upload/session/<id>` | Session metadata |
| DELETE | `/api/upload/session/<id>` | Delete session |

**Upload example (curl):**
```bash
curl -X POST http://localhost:5000/api/upload/file \
  -F "file=@sample-data/sales_data.csv"
```

**Response:**
```json
{
  "success": true,
  "session_id": "a3b1c9f2",
  "filename": "sales_data.csv",
  "rows": 120,
  "columns": ["id", "date", "category", "revenue", ...],
  "filter_options": { "region": ["East", "North", ...], ... },
  "date_range": { "from": "2024-01-01", "to": "2024-12-29" }
}
```

---

### Analytics
All endpoints accept these query filters: `region`, `category`, `rep`, `date_from`, `date_to`

| Method | Endpoint | Extra Params |
|--------|----------|-------------|
| GET | `/api/analytics/summary` | — |
| GET | `/api/analytics/revenue` | `period=monthly\|quarterly\|yearly` |
| GET | `/api/analytics/categories` | — |
| GET | `/api/analytics/regions` | — |
| GET | `/api/analytics/reps` | — |
| GET | `/api/analytics/products` | `n=10` |
| GET | `/api/analytics/dax` | — |
| GET | `/api/analytics/filters` | — |

**Examples:**
```bash
# Full KPI summary
curl "http://localhost:5000/api/analytics/summary?session_id=a3b1c9f2"

# Revenue by month, filtered to North region
curl "http://localhost:5000/api/analytics/revenue?session_id=a3b1c9f2&period=monthly&region=North"

# DAX measures
curl "http://localhost:5000/api/analytics/dax?session_id=a3b1c9f2"
```

---

### Data Explorer
| Method | Endpoint | Params |
|--------|----------|--------|
| GET | `/api/data/records` | `page`, `page_size`, `sort_by`, `sort_dir`, filters |
| GET | `/api/data/columns` | — |
| GET | `/api/data/sample` | `n=5` |

```bash
# Page 2, sorted by revenue descending
curl "http://localhost:5000/api/data/records?session_id=a3b1c9f2&page=2&page_size=20&sort_by=revenue&sort_dir=desc"
```

---

### Export
| Method | Endpoint | Output |
|--------|----------|--------|
| GET | `/api/export/csv` | `.csv` file download |
| GET | `/api/export/xlsx` | `.xlsx` file download |
| GET | `/api/export/json` | `.json` file download |
| GET | `/api/export/tsv` | `.tsv` file download |
| GET | `/api/export/summary` | KPI summary `.csv` |

All exports respect active filters:
```bash
curl "http://localhost:5000/api/export/xlsx?session_id=a3b1c9f2&region=North" -o north_sales.xlsx
```

---

## 📐 DAX Measures Reference

The `/api/analytics/dax` endpoint returns Power BI-equivalent formulas:

| Measure | DAX Formula |
|---------|-------------|
| Total Revenue | `SUM(Sales[Revenue])` |
| Total Profit | `SUM(Sales[Profit])` |
| Profit Margin % | `DIVIDE(SUM(Profit), SUM(Revenue)) * 100` |
| Avg Order Value | `DIVIDE(SUM(Revenue), COUNTROWS())` |
| Cost Ratio % | `DIVIDE(SUM(Cost), SUM(Revenue)) * 100` |
| Revenue per Unit | `DIVIDE(SUM(Revenue), SUM(Units))` |
| Profit per Order | `DIVIDE(SUM(Profit), COUNTROWS())` |
| Running Total | `CALCULATE(SUM(Revenue), DATESYTD(...))` |
| MoM Growth % | `DIVIDE([Revenue] - [PrevMonthRevenue], [PrevMonthRevenue])` |

---

## 🧪 Running Tests

```bash
# Run all 45 tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_api.py::TestAnalytics -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=term-missing
```

**Test coverage:**
- ✅ Upload: CSV, JSON, bad extensions, session management
- ✅ Analytics: all 8 endpoints, filters, edge cases
- ✅ Data explorer: pagination, sorting, filtering
- ✅ Export: all 5 formats, with filters
- ✅ DAX Engine: 12 unit tests

---

## 🌐 Supported Upload Formats

| Format | Extension | Auto-detected fields |
|--------|-----------|----------------------|
| CSV | `.csv` | All standard column names |
| Excel | `.xlsx`, `.xls` | First sheet |
| JSON | `.json` | Array, `{sales:[...]}`, `{data:[...]}` |
| TSV | `.tsv` | Tab-separated |

### Auto Field Name Detection
The backend automatically maps these column name variations:

```
Revenue  → Revenue, revenue, Sales, sales, Amount
Profit   → Profit, profit, Net Profit, net_profit
Category → Category, category, ProductCategory
Rep      → Sales Rep, sales_rep, SalesRep, Salesperson
...etc
```

---

## 🚢 Production Deployment

### Linux / Mac — Gunicorn
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secure-key-here
gunicorn app:app --bind 0.0.0.0:5000 --workers 4 --timeout 120
```

### Windows PowerShell — Waitress
> ⚠️ Gunicorn does NOT work on Windows. Use Waitress instead.
> ❌ Do NOT use `export` in PowerShell — use `$env:VAR = "value"` syntax.
```powershell
$env:FLASK_ENV = "production"
$env:SECRET_KEY = "your-secure-key-here"
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

### All Platforms — .env file (recommended)
```
# Copy .env.example to .env and fill in your values
# The app reads it automatically on startup
```

---

## 🔧 Connecting Frontend to Backend

Update the frontend `index.html` to call the API instead of parsing files in-browser:

```javascript
// Replace local file parsing with:
async function uploadToBackend(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch('http://localhost:5000/api/upload/file', {
    method: 'POST', body: formData
  });
  const { session_id, rows } = await res.json();
  
  // Then fetch analytics:
  const kpis = await fetch(`http://localhost:5000/api/analytics/summary?session_id=${session_id}`);
  const data = await kpis.json();
  // ... render dashboard
}
```

---

*Built with Flask · Pandas · NumPy · OpenPyXL*
