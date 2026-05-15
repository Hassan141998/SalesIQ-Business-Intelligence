# ============================================================
#  SalesIQ BI Dashboard — Windows PowerShell Setup Script
#  Run from the PROJECT ROOT:  E:\pycharm\bi dashboard\
#  Usage:  .\setup_windows.ps1
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SalesIQ BI Dashboard — Windows Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Detect project root (where this script lives) ──────────────────────────
$ROOT    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BACKEND = Join-Path $ROOT "backend"

Write-Host "Project root : $ROOT" -ForegroundColor Gray
Write-Host "Backend path : $BACKEND" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $BACKEND)) {
    Write-Host "ERROR: backend\ folder not found at $BACKEND" -ForegroundColor Red
    Write-Host "Make sure you run this script from the bi-dashboard project root." -ForegroundColor Yellow
    exit 1
}

Set-Location $BACKEND

# ── 2. Create/activate virtual environment ────────────────────────────────────
$VENV = Join-Path $ROOT ".venv"
if (-not (Test-Path $VENV)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VENV
}

$ACTIVATE = Join-Path $VENV "Scripts\Activate.ps1"
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $ACTIVATE

# ── 3. Install dependencies ───────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

Write-Host "✅ Dependencies installed" -ForegroundColor Green

# ── 4. Copy .env if missing ───────────────────────────────────────────────────
$ENV_DEST   = Join-Path $BACKEND ".env"
$ENV_EXAMPLE = Join-Path $BACKEND ".env.example"

if (-not (Test-Path $ENV_DEST)) {
    if (Test-Path $ENV_EXAMPLE) {
        Copy-Item $ENV_EXAMPLE $ENV_DEST
        Write-Host "✅ Created .env from .env.example" -ForegroundColor Green
    } else {
        # Create minimal .env inline
        @"
FLASK_ENV=development
SECRET_KEY=salesiq-change-this-in-production
HOST=0.0.0.0
PORT=5000
"@ | Set-Content $ENV_DEST
        Write-Host "✅ Created default .env" -ForegroundColor Green
    }
} else {
    Write-Host "✅ .env already exists" -ForegroundColor Green
}

# ── 5. Generate sample data ───────────────────────────────────────────────────
$SAMPLE_DIR = Join-Path $ROOT "sample-data"
$SEED       = Join-Path $BACKEND "seed_data.py"

if (-not (Test-Path (Join-Path $SAMPLE_DIR "sales_data.csv"))) {
    Write-Host ""
    Write-Host "Generating sample data files..." -ForegroundColor Yellow
    python $SEED
} else {
    Write-Host "✅ Sample data already exists" -ForegroundColor Green
}

# ── 6. Run tests ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Running test suite..." -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
Write-Host ""

# ── 7. Start server ───────────────────────────────────────────────────────────
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starting SalesIQ Backend Server" -ForegroundColor Cyan
Write-Host "  URL : http://localhost:5000" -ForegroundColor Green
Write-Host "  Docs: http://localhost:5000/api/docs" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python app.py
