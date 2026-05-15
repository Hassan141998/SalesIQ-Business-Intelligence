# SalesIQ — Deploy to GitHub + Vercel + Neon DB
## Complete Step-by-Step Guide (Windows + Mac/Linux)

---

## 🗺️ Overview

```
Your PC  →  GitHub repo  →  Vercel (auto-deploy)
                                ↕
                          Neon PostgreSQL
```

Everything is free tier:
- **GitHub** — free repo
- **Vercel** — free hobby plan (enough for portfolio)
- **Neon** — free tier (0.5 GB, perfect for this project)

---

## STEP 1 — Create Neon PostgreSQL Database

1. Go to **https://neon.tech** → Sign up (free)
2. Click **"New Project"**
3. Name it: `salesiq-dashboard`
4. Choose region closest to you
5. Click **"Create project"**
6. On the dashboard, click **"Connection string"**
7. Copy the full connection string — looks like:
   ```
   postgresql://username:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
8. **Save this — you'll need it twice** (local .env and Vercel)

---

## STEP 2 — Configure Local .env

Open `backend/.env` in Notepad and paste:

```env
FLASK_ENV=development
SECRET_KEY=salesiq-your-secret-key-change-this
DATABASE_URL=postgresql://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
HOST=0.0.0.0
PORT=5000
```

Replace the DATABASE_URL with your actual Neon connection string.

---

## STEP 3 — Initialize the Database Tables

```powershell
# Windows PowerShell — from backend\ folder
cd "E:\pycharm\bi dashboard\backend"
..\.venv\Scripts\Activate.ps1
python app.py
```

When the server starts, open a new PowerShell tab and run:

```powershell
# Initialize tables in Neon
Invoke-RestMethod -Method POST "http://localhost:5000/api/db/init"
```

You should see:
```json
{"success": true, "message": "Tables created"}
```

Check the health:
```powershell
Invoke-RestMethod "http://localhost:5000/api/health"
# Should show: "database": "connected"
```

**Now open http://localhost:5000 — you'll see the dashboard!**

---

## STEP 4 — Push to GitHub

### First time setup:

```powershell
# Install Git if not installed: https://git-scm.com
git --version

# Go to project ROOT (not backend)
cd "E:\pycharm\bi dashboard"

# Initialize git
git init
git add .
git commit -m "Initial commit: SalesIQ BI Dashboard"
```

### Create GitHub repo:

1. Go to **https://github.com** → Sign in
2. Click **"New repository"** (green button)
3. Name: `salesiq-bi-dashboard`
4. Keep it **Public** (required for free Vercel)
5. Do NOT check "Add README" (you already have one)
6. Click **"Create repository"**
7. Copy the repo URL: `https://github.com/YOUR_USERNAME/salesiq-bi-dashboard.git`

### Push your code:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/salesiq-bi-dashboard.git
git branch -M main
git push -u origin main
```

---

## STEP 5 — Deploy to Vercel

### Option A — Vercel CLI (recommended)

```powershell
# Install Vercel CLI
npm install -g vercel

# From project ROOT
cd "E:\pycharm\bi dashboard"
vercel

# Follow prompts:
#   Set up and deploy? Y
#   Which scope? (your account)
#   Link to existing project? N
#   Project name: salesiq-bi-dashboard
#   Directory: ./  (press Enter)
#   Override settings? N
```

### Option B — Vercel Website

1. Go to **https://vercel.com** → Sign in with GitHub
2. Click **"Add New Project"**
3. Import your `salesiq-bi-dashboard` repo
4. Framework Preset: **Other**
5. Root Directory: `.` (leave as is)
6. Click **"Deploy"** — first deploy will fail (no DATABASE_URL yet, that's ok)

### Add DATABASE_URL to Vercel:

1. In Vercel dashboard → your project → **Settings** tab
2. Click **"Environment Variables"**
3. Add:
   - Name: `DATABASE_URL`
   - Value: `postgresql://...your neon connection string...`
   - Environment: Production, Preview, Development (check all)
4. Click **"Save"**
5. Go to **Deployments** tab → click **"Redeploy"**

### Initialize Neon tables on Vercel:

After redeployment, run once:
```powershell
Invoke-RestMethod -Method POST "https://your-project.vercel.app/api/db/init"
```

---

## STEP 6 — Verify Live Deployment

```powershell
$LIVE = "https://your-project.vercel.app"

# Health check
Invoke-RestMethod "$LIVE/api/health"
# Expected: {"status":"ok","database":"connected","db_ok":true}

# API info
Invoke-RestMethod "$LIVE/api"

# Open in browser
Start-Process "$LIVE"
```

---

## 🔄 Future Updates (Push → Auto-Deploy)

Every time you push to GitHub, Vercel auto-deploys:

```powershell
cd "E:\pycharm\bi dashboard"
git add .
git commit -m "Update: describe your change"
git push
# Vercel detects the push and deploys automatically in ~60 seconds
```

---

## 📁 Final File Structure for Deployment

```
salesiq-bi-dashboard/          ← GitHub repo root
├── vercel.json                ← Vercel routing config
├── requirements.txt           ← Python deps for Vercel
├── .gitignore                 ← Excludes .env, uploads, __pycache__
├── index.html                 ← Frontend dashboard
├── sample-data/
│   ├── sales_data.csv
│   ├── sales_data.xlsx
│   └── sales_data.json
└── backend/
    ├── app.py                 ← Flask app (Vercel entry point)
    ├── .env                   ← LOCAL ONLY — never committed
    ├── .env.example           ← Template — committed
    ├── requirements.txt       ← Backend-specific deps
    ├── db/
    │   ├── database.py        ← Neon SQLAlchemy connection
    │   └── operations.py      ← All DB queries
    ├── routes/
    │   ├── upload.py
    │   ├── analytics.py
    │   ├── data.py
    │   └── export.py
    └── utils/
        ├── data_processor.py
        └── dax_engine.py
```

---

## 🐛 Troubleshooting

### "Dashboard not showing, only JSON at /"
→ You're opening `http://localhost:5000/api` instead of `http://localhost:5000`
→ Open exactly: **http://localhost:5000**

### "database: not configured" in health check
→ DATABASE_URL is missing from `.env`
→ Add it: `DATABASE_URL=postgresql://...` (your Neon connection string)

### "connection failed" in health check
→ Wrong Neon connection string — re-copy from Neon dashboard
→ Make sure `?sslmode=require` is at the end

### Vercel deploy shows 500 error
→ DATABASE_URL not added to Vercel environment variables
→ Go to Vercel → Settings → Environment Variables → add it → Redeploy

### Tables don't exist error
→ Run: `POST /api/db/init` to create tables
→ `Invoke-RestMethod -Method POST "https://your-app.vercel.app/api/db/init"`

### Git push rejected
```powershell
git pull origin main --rebase
git push
```

---

## 🔑 Security Checklist Before Making Repo Public

- [ ] `.env` is in `.gitignore` (check: `git status` should NOT show `.env`)
- [ ] `DATABASE_URL` is NOT hardcoded anywhere in Python files
- [ ] `SECRET_KEY` is set to something random (not the default)
- [ ] Run `git log --all -- .env` — should show nothing

---

*Flask · Neon PostgreSQL · Vercel · GitHub*
