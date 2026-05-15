# Fixing Vercel 404: NOT_FOUND

Your build log shows:
```
Build Completed in 61ms   ← way too fast = nothing built
404: NOT_FOUND            ← Vercel found no entry point
```

**Root cause:** Vercel Python requires the entry file at `api/index.py` in the repo root.
Your `vercel.json` was pointing to `backend/app.py` which Vercel ignored.

---

## ✅ The Fix (do all 5 steps)

### Step 1 — Pull the latest code from this ZIP

Extract the ZIP. Your project should now have this layout:
```
salesiq-bi-dashboard/         ← repo root
├── api/
│   └── index.py              ← NEW: Vercel entry point
├── vercel.json               ← UPDATED: points to api/index.py
├── requirements.txt          ← at ROOT (Vercel reads this)
├── index.html
├── sample-data/
├── backend/
│   ├── app.py
│   ├── db/
│   ├── routes/
│   └── utils/
└── .gitignore
```

### Step 2 — Verify these 3 files exist

**`api/index.py`** (new file):
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app import app
```

**`vercel.json`** (updated):
```json
{
  "version": 2,
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
}
```

**`requirements.txt`** (at ROOT, not inside backend/):
```
flask==3.0.3
flask-cors==4.0.1
pandas==2.2.2
...
```

### Step 3 — Push to GitHub

```powershell
cd "E:\pycharm\bi dashboard"

# Check what changed
git status

# Add everything
git add .
git commit -m "Fix: add api/index.py Vercel entry point"
git push
```

### Step 4 — Add DATABASE_URL to Vercel

1. Go to **vercel.com** → your project → **Settings** tab
2. Click **Environment Variables** in left sidebar
3. Click **Add New**:
   - Key: `DATABASE_URL`
   - Value: `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
   - Check all 3 environments: ✅ Production ✅ Preview ✅ Development
4. Click **Save**

### Step 5 — Trigger a new deployment

Vercel auto-deploys when you push to GitHub (Step 3 already did this).

Or manually: **Vercel dashboard → Deployments → Redeploy** (top right button).

---

## ✅ How to verify it worked

```powershell
# Replace with your actual Vercel URL
$URL = "https://salesiq-bi-dashboard.vercel.app"

# 1. Health check
Invoke-RestMethod "$URL/api/health"
# Expected: {"status":"ok","database":"connected","db_ok":true}

# 2. Open dashboard in browser
Start-Process $URL
# Expected: the full SalesIQ dashboard loads

# 3. Initialize DB tables (first time only)
Invoke-RestMethod -Method POST "$URL/api/db/init"
# Expected: {"success":true,"message":"Database tables created successfully"}
```

---

## 🔍 Reading Vercel Build Logs

Go to Vercel → your project → **Deployments** tab → click the latest deployment → **Build Logs**

| What you see | What it means |
|---|---|
| `Build Completed in 61ms` | Nothing was built — wrong entry point |
| `pip install flask pandas...` | ✅ Python packages installing correctly |
| `Build Completed in 45s` | ✅ Real build happened |
| `404 NOT_FOUND` on deploy | Entry point wrong |
| `500 Internal Server Error` | App crashes — check Function Logs |

**Function Logs** (runtime errors after deploy):
Vercel dashboard → your project → **Logs** tab — shows live request logs and Python errors.

---

## 🌐 Final URLs after deploy

| URL | What it shows |
|---|---|
| `https://your-app.vercel.app/` | ✅ Dashboard UI |
| `https://your-app.vercel.app/api/health` | ✅ Health check JSON |
| `https://your-app.vercel.app/api/docs` | ✅ API documentation |
| `https://your-app.vercel.app/api/upload/file` | ✅ File upload endpoint |

---

## 🐛 Still getting 404?

Check these in order:

**1. Is `api/index.py` committed?**
```powershell
git ls-files | findstr "api"
# Should show: api/index.py
```

**2. Is `vercel.json` correct?**
```powershell
type vercel.json
# Should show: "src": "api/index.py"
```

**3. Did the build actually run Python?**
→ Vercel build logs should show `pip install flask...`
→ If it still says "61ms" — Vercel is using cached broken config, click **"Redeploy without cache"**

**4. CORS or 500 error instead of 404?**
→ App is running but DATABASE_URL is wrong
→ Check Vercel → Settings → Environment Variables
→ Make sure DATABASE_URL has `?sslmode=require` at the end

**5. Still stuck?**
→ Vercel → your project → **Logs** tab → share the error message
