# SalesIQ — Business Intelligence Dashboard

A fully functional, interactive Sales Analytics BI Dashboard built with pure HTML, CSS, and JavaScript. No backend required — runs entirely in the browser.

---

## 🚀 Quick Start

1. **Unzip** the downloaded file
2. **Double-click** `index.html` to open in your browser
3. Click **"Load Demo Data"** to instantly see the dashboard with 120 sample records
4. Or click **"Upload Data"** to load your own file

> ✅ No installation, no server, no dependencies to install — works offline!

---

## 📁 Project Structure

```
bi-dashboard/
├── index.html              ← Main dashboard (entire app)
├── README.md               ← This file
└── sample-data/
    ├── sales_data.csv      ← 120 sample sales records (CSV)
    ├── sales_data.xlsx     ← Same data in Excel format
    └── sales_data.json     ← 10 records in JSON format
```

---

## 📂 Supported File Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| CSV | `.csv` | Most common, Excel exports, universal |
| Excel | `.xlsx`, `.xls` | Microsoft Excel files |
| JSON | `.json` | API responses, system integrations |
| TSV | `.tsv` | Tab-separated, database exports |

### Required Columns (flexible naming)

The dashboard auto-detects these field names:

| Field | Accepted Column Names |
|-------|-----------------------|
| Order ID | `Order ID`, `order_id`, `OrderID`, `id` |
| Date | `Date`, `date`, `OrderDate`, `order_date` |
| Category | `Category`, `category`, `ProductCategory` |
| Product | `Product`, `product`, `ProductName` |
| Region | `Region`, `region` |
| Sales Rep | `Sales Rep`, `sales_rep`, `SalesRep`, `Rep` |
| Units | `Units`, `units`, `Quantity`, `quantity` |
| Revenue | `Revenue`, `revenue`, `Sales`, `sales` |
| Cost | `Cost`, `cost` |
| Profit | `Profit`, `profit` (auto-calculated if missing) |
| Customer | `Customer`, `customer`, `CustomerName` |

---

## 📊 Dashboard Features

### KPI Cards (5 live metrics)
- **Total Revenue** — SUM of all revenue
- **Total Profit** — SUM of all profit
- **Total Orders** — COUNT of records
- **Units Sold** — SUM of units
- **Profit Margin %** — Profit ÷ Revenue × 100

### Charts
| Chart | Type | Description |
|-------|------|-------------|
| Revenue & Profit Over Time | Bar / Line | Monthly, Quarterly, Yearly toggle |
| Revenue by Category | Donut / Bar | Category breakdown |
| Revenue by Region | Horizontal bars | Geographic performance |
| Sales by Rep | Horizontal bar | Individual rep comparison |
| Top 5 Products | Ranked list | By revenue with margin % |

### Advanced Analytics Page
- Profit Margin by Category
- Units Sold by Month
- Revenue vs Cost Comparison
- Sales Rep Performance
- **DAX-Style Measures** (8 live calculations)

### Data Explorer Page
- Full sortable table
- Search across all fields
- Pagination (20 rows/page)
- Filters: Region, Category, Rep, Date range

---

## 🔽 Filter / Slicer Controls

Available on every page:
- **Region** — North, South, East, West (or your regions)
- **Category** — Electronics, Clothing, etc.
- **Sales Rep** — Individual rep filter
- **Date Range** — From / To date picker

All charts and KPIs update instantly when filters change.

---

## 📐 DAX-Style Measures Reference

These are the Power BI equivalent DAX formulas computed live:

```
Total Revenue     = SUM(Revenue)
Total Profit      = SUM(Profit)
Profit Margin %   = DIVIDE(SUM(Profit), SUM(Revenue)) * 100
Avg Order Value   = DIVIDE(SUM(Revenue), COUNTROWS())
Cost Ratio        = DIVIDE(SUM(Cost), SUM(Revenue)) * 100
Units per Order   = DIVIDE(SUM(Units), COUNTROWS())
Revenue per Unit  = DIVIDE(SUM(Revenue), SUM(Units))
Total Orders      = COUNTROWS(Sales)
```

---

## ⬇️ Export Options

| Format | Use Case |
|--------|----------|
| CSV | Universal — open in Excel, Google Sheets |
| Excel (.xlsx) | Formatted spreadsheet with headers |
| JSON | Developer/API integrations |
| TSV | Database imports, BI tools |
| Summary Report | CSV with KPIs + category/region breakdown |

All exports respect active filters — export only what you see.

---

## 🖥️ Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome | ✅ Full |
| Edge | ✅ Full |
| Firefox | ✅ Full |
| Safari | ✅ Full |
| Opera | ✅ Full |

---

## 📋 Sample Data Format (CSV)

```csv
Order ID,Date,Category,Product,Region,Sales Rep,Units,Unit Price,Revenue,Cost,Profit,Customer
1001,2024-01-05,Electronics,Laptop Pro,North,Alice Johnson,2,1299.99,2599.98,1800.00,799.98,TechCorp
1002,2024-01-07,Clothing,Winter Jacket,South,Bob Smith,5,89.99,449.95,225.00,224.95,FashionHub
```

---

## 🎨 Portfolio Notes

This dashboard demonstrates:
- **Data visualization** with Chart.js (bar, line, donut charts)
- **Multi-format file parsing** (CSV, Excel, JSON, TSV)
- **Interactive filtering** with live chart updates
- **Responsive design** for desktop and mobile
- **Export functionality** in 5 formats
- **DAX-equivalent measures** (Power BI concepts in JS)
- **Dark theme UI** with professional design

---

## 🔧 Customization

To add your own branding, edit these lines in `index.html`:

```html
<!-- Change the brand name -->
<div class="brand-name">SalesIQ</div>

<!-- Change the color scheme (CSS variables at top of <style>) -->
--accent: #4f7eff;      /* Primary blue */
--accent2: #00d4aa;     /* Green */
--accent3: #ff6b6b;     /* Red */
--accent4: #ffd166;     /* Yellow */
```

---

*Built with Chart.js · PapaParse · SheetJS · Pure CSS*
