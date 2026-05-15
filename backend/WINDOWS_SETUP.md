# SalesIQ — Windows PowerShell Complete Guide
# All commands verified on Windows 11, Python 3.11, PowerShell 5+

---

## ✅ Everything Working — Quick Summary

Your server IS running correctly (you can see the JSON at localhost:5000).
These are the only things left to fix:

| Problem seen | Root cause | Fix |
|---|---|---|
| `cd backend` fails | Already inside `backend\` | Don't run it — check `pwd` first |
| `curl -F` not recognized | PowerShell curl ≠ Linux curl | Use `Invoke-RestMethod` instead |
| `gunicorn` crashes (`fcntl`) | Gunicorn is Linux-only | Use `waitress-serve` instead |
| `export VAR=value` fails | Linux syntax | Use `$env:VAR = "value"` |
| `.env.example not found` | Wrong directory | `cd` to `backend\` first |

---

## 🚀 One-Command Setup (Recommended)

From the **project root** (`E:\pycharm\bi dashboard\`):

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser   # one time only
.\setup_windows.ps1
```

This handles everything: venv, install, .env, sample data, tests, and server start.

---

## 📁 Directory Map — Know Where You Are

```
E:\pycharm\bi dashboard\              <- PROJECT ROOT
├── setup_windows.ps1                 <- Run this first
├── test_api_windows.ps1              <- API tester
├── index.html
├── sample-data\
│   ├── sales_data.csv
│   ├── sales_data.xlsx
│   └── sales_data.json
└── backend\                          <- cd here for python commands
    ├── app.py
    ├── .env
    ├── .env.example
    └── ...
```

**Most common mistake:** running `cd backend` when already inside `backend\`.

```powershell
pwd    # check where you are before cd-ing
```

---

## 🔧 Manual Step-by-Step Setup

```powershell
# Step 1 — Go to backend (from project root)
cd "E:\pycharm\bi dashboard\backend"

# Step 2 — Activate venv
..\.venv\Scripts\Activate.ps1

# Step 3 — Install packages
pip install -r requirements.txt

# Step 4 — Create .env  (run from backend\ folder)
copy .env.example .env
notepad .env

# Step 5 — Generate sample data
python seed_data.py

# Step 6 — Start server
python app.py
# -> http://localhost:5000
```

---

## 🌐 Environment Variables — PowerShell Syntax

> `export KEY=value` is Linux/Mac only and will always fail in PowerShell.

```powershell
# Set for current session
$env:FLASK_ENV = "development"
$env:SECRET_KEY = "your-secure-key-here"

# Verify
echo $env:FLASK_ENV

# Set permanently
[System.Environment]::SetEnvironmentVariable("FLASK_ENV", "development", "User")
```

Easiest option — edit `.env` file and forget env vars entirely:
```
FLASK_ENV=development
SECRET_KEY=salesiq-change-this
HOST=0.0.0.0
PORT=5000
```

---

## 📡 API Calls — Correct PowerShell Syntax

PowerShell `curl` is really `Invoke-WebRequest`. It does NOT support `-X`, `-F`, or `@file`.

### Upload a file

```powershell
# Easiest — use the provided test script:
.\test_api_windows.ps1

# Or manually with Invoke-RestMethod:
$CSV       = "E:\pycharm\bi dashboard\sample-data\sales_data.csv"
$FileBytes = [System.IO.File]::ReadAllBytes($CSV)
$FileEnc   = [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($FileBytes)
$Boundary  = [System.Guid]::NewGuid().ToString()
$FileName  = [System.IO.Path]::GetFileName($CSV)

$Body  = "--$Boundary`r`n"
$Body += "Content-Disposition: form-data; name=`"file`"; filename=`"$FileName`"`r`n"
$Body += "Content-Type: text/csv`r`n`r`n"
$Body += $FileEnc
$Body += "`r`n--$Boundary--`r`n"

$Response = Invoke-RestMethod `
    -Uri "http://localhost:5000/api/upload/file" `
    -Method POST `
    -ContentType "multipart/form-data; boundary=$Boundary" `
    -Body ([System.Text.Encoding]::GetEncoding('iso-8859-1').GetBytes($Body))

$SESSION = $Response.session_id
echo "Session: $SESSION"
```

### GET requests

```powershell
Invoke-RestMethod "http://localhost:5000/api/health"
Invoke-RestMethod "http://localhost:5000/api/analytics/summary?session_id=$SESSION"
Invoke-RestMethod "http://localhost:5000/api/analytics/revenue?session_id=$SESSION&period=monthly"
Invoke-RestMethod "http://localhost:5000/api/analytics/dax?session_id=$SESSION"
Invoke-RestMethod "http://localhost:5000/api/data/records?session_id=$SESSION&page=1&page_size=20&sort_by=revenue&sort_dir=desc"
```

### Download / Export

```powershell
Invoke-WebRequest "http://localhost:5000/api/export/csv?session_id=$SESSION"  -OutFile "sales.csv"
Invoke-WebRequest "http://localhost:5000/api/export/xlsx?session_id=$SESSION" -OutFile "sales.xlsx"
Invoke-WebRequest "http://localhost:5000/api/export/json?session_id=$SESSION" -OutFile "sales.json"
Invoke-WebRequest "http://localhost:5000/api/export/xlsx?session_id=$SESSION&region=North" -OutFile "north.xlsx"
Invoke-WebRequest "http://localhost:5000/api/export/summary?session_id=$SESSION" -OutFile "summary.csv"
```

---

## 🏭 Production — Waitress (Windows)

> Gunicorn crashes with `ModuleNotFoundError: No module named 'fcntl'` on Windows.
> `fcntl` is a Linux kernel module — Gunicorn will never work on Windows.

```powershell
# Waitress is already installed via requirements.txt
waitress-serve --host=0.0.0.0 --port=5000 app:app

# With multiple threads
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app
```

---

## 🧪 Tests

```powershell
cd "E:\pycharm\bi dashboard\backend"
..\.venv\Scripts\Activate.ps1

python -m pytest tests/ -v                              # all 45 tests
python -m pytest tests/ --cov=. --cov-report=term-missing  # with coverage
python -m pytest tests/test_api.py::TestAnalytics -v   # one class
python -m pytest tests/test_api.py::TestDAXEngine -v
```

---

## 💡 Python requests (easier than PowerShell for API calls)

```powershell
pip install requests
```

```python
# test_manual.py
import requests

BASE = "http://localhost:5000"

# Upload
with open(r"E:\pycharm\bi dashboard\sample-data\sales_data.csv", "rb") as f:
    r = requests.post(f"{BASE}/api/upload/file", files={"file": f})
session = r.json()["session_id"]
print(f"Session: {session}, Rows: {r.json()['rows']}")

# KPIs
kpis = requests.get(f"{BASE}/api/analytics/summary?session_id={session}").json()
print(f"Revenue: ${kpis['kpis']['total_revenue']:,.2f}")
print(f"Margin:  {kpis['kpis']['profit_margin_pct']}%")

# Download Excel
xlsx = requests.get(f"{BASE}/api/export/xlsx?session_id={session}")
with open("sales_export.xlsx", "wb") as f:
    f.write(xlsx.content)
print("Saved: sales_export.xlsx")
```

```powershell
python test_manual.py
```

---

## 🐛 All Errors Fixed

| Error | Cause | Fix |
|---|---|---|
| `Cannot find path '...\backend\backend'` | `cd backend` run twice | Check `pwd`, don't double-cd |
| `'-F' is not recognized` | Linux curl syntax | Use `Invoke-RestMethod` |
| `Unable to connect to remote server` | Server not started | Run `python app.py` first |
| `ModuleNotFoundError: fcntl` | Gunicorn on Windows | Use `waitress-serve` |
| `'export' is not recognized` | Linux env syntax | Use `$env:VAR = "value"` |
| `.env.example not found` | Wrong directory | `cd backend\` first |
| `Activate.ps1 cannot be loaded` | Execution policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

*Windows 10/11 · PowerShell 5+ · Python 3.11 · Flask 3.0 · Waitress 3.0*
