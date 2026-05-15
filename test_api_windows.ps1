# ============================================================
#  SalesIQ API Tester — Windows PowerShell
#  Tests all API endpoints using Invoke-RestMethod (native PS)
#
#  Usage:
#    1. Start the server first: python app.py
#    2. Run this script:        .\test_api_windows.ps1
# ============================================================

$BASE = "http://localhost:5000"

# Colour helpers
function OK   { param($m) Write-Host "  ✅ $m" -ForegroundColor Green }
function FAIL { param($m) Write-Host "  ❌ $m" -ForegroundColor Red }
function HEAD { param($m) Write-Host "`n── $m ──" -ForegroundColor Cyan }
function INFO { param($m) Write-Host "     $m"   -ForegroundColor Gray }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SalesIQ API Tester (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── Health check ──────────────────────────────────────────────────────────────
HEAD "Health Check"
try {
    $r = Invoke-RestMethod "$BASE/api/health"
    if ($r.status -eq "ok") { OK "Server is running" }
    else                     { FAIL "Unexpected status: $($r.status)" }
} catch {
    FAIL "Cannot reach server. Is 'python app.py' running?"
    Write-Host "`nStart the server first: python app.py" -ForegroundColor Yellow
    exit 1
}

# ── Upload CSV ────────────────────────────────────────────────────────────────
HEAD "Upload CSV File"

# Find the sample CSV — look relative to script location OR common paths
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$CsvOptions = @(
    (Join-Path $ScriptDir "sample-data\sales_data.csv"),
    (Join-Path $ScriptDir "..\sample-data\sales_data.csv"),
    (Join-Path $ScriptDir "backend\..\sample-data\sales_data.csv")
)
$CSV = $CsvOptions | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $CSV) {
    FAIL "sample-data\sales_data.csv not found. Run: python seed_data.py"
    exit 1
}
INFO "Using file: $CSV"

# Upload using multipart form — correct PowerShell way (no curl -F)
try {
    $FileBytes  = [System.IO.File]::ReadAllBytes($CSV)
    $FileEnc    = [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($FileBytes)
    $Boundary   = [System.Guid]::NewGuid().ToString()
    $FileName   = [System.IO.Path]::GetFileName($CSV)

    $Body  = "--$Boundary`r`n"
    $Body += "Content-Disposition: form-data; name=`"file`"; filename=`"$FileName`"`r`n"
    $Body += "Content-Type: text/csv`r`n`r`n"
    $Body += $FileEnc
    $Body += "`r`n--$Boundary--`r`n"

    $BodyBytes = [System.Text.Encoding]::GetEncoding('iso-8859-1').GetBytes($Body)

    $Upload = Invoke-RestMethod `
        -Uri "$BASE/api/upload/file" `
        -Method POST `
        -ContentType "multipart/form-data; boundary=$Boundary" `
        -Body $BodyBytes

    $SESSION = $Upload.session_id
    OK "Uploaded '$FileName' → session_id: $SESSION"
    INFO "Rows parsed: $($Upload.rows)"
    INFO "Columns: $($Upload.columns -join ', ')"
} catch {
    FAIL "Upload failed: $_"
    exit 1
}

# ── Analytics Endpoints ───────────────────────────────────────────────────────
HEAD "Analytics — KPI Summary"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/summary?session_id=$SESSION"
    OK "Total Revenue : `$$($r.kpis.total_revenue)"
    OK "Total Profit  : `$$($r.kpis.total_profit)"
    OK "Orders        : $($r.kpis.total_orders)"
    OK "Margin        : $($r.kpis.profit_margin_pct)%"
} catch { FAIL $_ }

HEAD "Analytics — Revenue (Monthly)"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/revenue?session_id=$SESSION&period=monthly"
    OK "Monthly periods returned: $($r.data.Count)"
    if ($r.data.Count -gt 0) {
        INFO "First period: $($r.data[0].period) → Revenue: `$$($r.data[0].revenue)"
    }
} catch { FAIL $_ }

HEAD "Analytics — Revenue with Region Filter"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/revenue?session_id=$SESSION&period=monthly&region=North"
    OK "North-only periods: $($r.data.Count)"
} catch { FAIL $_ }

HEAD "Analytics — Categories"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/categories?session_id=$SESSION"
    OK "Categories returned: $($r.data.Count)"
    $r.data | ForEach-Object { INFO "$($_.category): `$$($_.revenue) (margin: $($_.margin_pct)%)" }
} catch { FAIL $_ }

HEAD "Analytics — Regions"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/regions?session_id=$SESSION"
    OK "Regions returned: $($r.data.Count)"
    $r.data | ForEach-Object { INFO "$($_.region): `$$($_.revenue) ($($_.pct_of_total)% of total)" }
} catch { FAIL $_ }

HEAD "Analytics — Sales Reps"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/reps?session_id=$SESSION"
    OK "Reps returned: $($r.data.Count)"
    $r.data | ForEach-Object { INFO "$($_.rep): `$$($_.revenue)" }
} catch { FAIL $_ }

HEAD "Analytics — Top 5 Products"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/products?session_id=$SESSION&n=5"
    OK "Top products returned: $($r.data.Count)"
    $r.data | ForEach-Object { INFO "#$($r.data.IndexOf($_)+1) $($_.product): `$$($_.revenue)" }
} catch { FAIL $_ }

HEAD "Analytics — DAX Measures"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/dax?session_id=$SESSION"
    OK "DAX measures returned: $($r.measures.Count)"
    $r.measures | Select-Object -First 4 | ForEach-Object {
        Info "$($_.name): $($_.value) $($_.unit)"
    }
} catch { FAIL $_ }

HEAD "Analytics — Filter Options"
try {
    $r = Invoke-RestMethod "$BASE/api/analytics/filters?session_id=$SESSION"
    OK "Regions available: $($r.filter_options.region -join ', ')"
    OK "Categories available: $($r.filter_options.category -join ', ')"
} catch { FAIL $_ }

# ── Data Explorer ─────────────────────────────────────────────────────────────
HEAD "Data — Records (Page 1, sorted by revenue desc)"
try {
    $r = Invoke-RestMethod "$BASE/api/data/records?session_id=$SESSION&page=1&page_size=5&sort_by=revenue&sort_dir=desc"
    OK "Total records: $($r.total)  |  Pages: $($r.pages)"
    $r.records | Select-Object -First 3 | ForEach-Object {
        Info "Order #$($_.id) — $($_.product): `$$($_.revenue)"
    }
} catch { FAIL $_ }

HEAD "Data — Filter by Category"
try {
    $r = Invoke-RestMethod "$BASE/api/data/records?session_id=$SESSION&category=Electronics"
    OK "Electronics records: $($r.total)"
} catch { FAIL $_ }

HEAD "Data — Column Info"
try {
    $r = Invoke-RestMethod "$BASE/api/data/columns?session_id=$SESSION"
    OK "Columns: $($r.columns.Count)"
    $r.columns | ForEach-Object { Info "$($_.name) [$($_.dtype)]" }
} catch { FAIL $_ }

HEAD "Data — Sample (3 rows)"
try {
    $r = Invoke-RestMethod "$BASE/api/data/sample?session_id=$SESSION&n=3"
    OK "Sample rows: $($r.records.Count)"
} catch { FAIL $_ }

# ── Export Downloads ──────────────────────────────────────────────────────────
HEAD "Export — CSV Download"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_export.csv"
    Invoke-WebRequest "$BASE/api/export/csv?session_id=$SESSION" -OutFile $OutFile
    $Lines = (Get-Content $OutFile).Count
    OK "CSV saved: $OutFile ($Lines lines)"
} catch { FAIL $_ }

HEAD "Export — Excel Download"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_export.xlsx"
    Invoke-WebRequest "$BASE/api/export/xlsx?session_id=$SESSION" -OutFile $OutFile
    $Size = (Get-Item $OutFile).Length
    OK "Excel saved: $OutFile ($Size bytes)"
} catch { FAIL $_ }

HEAD "Export — JSON Download"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_export.json"
    Invoke-WebRequest "$BASE/api/export/json?session_id=$SESSION" -OutFile $OutFile
    $Content = Get-Content $OutFile | ConvertFrom-Json
    OK "JSON saved: $OutFile ($($Content.records) records)"
} catch { FAIL $_ }

HEAD "Export — TSV Download"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_export.tsv"
    Invoke-WebRequest "$BASE/api/export/tsv?session_id=$SESSION" -OutFile $OutFile
    OK "TSV saved: $OutFile"
} catch { FAIL $_ }

HEAD "Export — Summary Report"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_summary.csv"
    Invoke-WebRequest "$BASE/api/export/summary?session_id=$SESSION" -OutFile $OutFile
    OK "Summary saved: $OutFile"
    Get-Content $OutFile | Select-Object -First 6 | ForEach-Object { Info $_ }
} catch { FAIL $_ }

HEAD "Export — Filtered (North region only)"
try {
    $OutFile = Join-Path $env:TEMP "salesiq_north.xlsx"
    Invoke-WebRequest "$BASE/api/export/xlsx?session_id=$SESSION&region=North" -OutFile $OutFile
    $Size = (Get-Item $OutFile).Length
    OK "North-filtered Excel: $OutFile ($Size bytes)"
} catch { FAIL $_ }

# ── Session Management ────────────────────────────────────────────────────────
HEAD "Session Management"
try {
    $r = Invoke-RestMethod "$BASE/api/upload/sessions"
    OK "Active sessions: $($r.sessions.Count)"
} catch { FAIL $_ }

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All API tests complete!" -ForegroundColor Green
Write-Host "  Exported files saved to: $env:TEMP" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
