"""
SalesIQ BI Dashboard — Flask App
==================================
Works in 3 environments:
  1. Local:  python backend/app.py  → http://localhost:5000
  2. Vercel: imported by api/index.py (entry point)
  3. Waitress (Windows prod): waitress-serve --call app:create_app

Frontend served at /
API served at /api/...
Database: Neon PostgreSQL (optional — falls back to in-memory)
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ── Resolve paths ──────────────────────────────────────────────────────────────
# backend/app.py can be called from different working dirs
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)   # the bi-dashboard/ root

# Add backend to sys.path so routes/utils imports always work
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def create_app():
    app = Flask(
        __name__,
        static_folder=PROJECT_ROOT,   # serve index.html and sample-data/ from here
        static_url_path=""
    )
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.config["UPLOAD_FOLDER"]      = os.path.join(BACKEND_DIR, "uploads")
    app.config["EXPORT_FOLDER"]      = os.path.join(BACKEND_DIR, "exports")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["ALLOWED_EXTENSIONS"] = {"csv", "xlsx", "xls", "json", "tsv"}

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    # ── Register API blueprints ────────────────────────────────────────────────
    from routes.upload    import upload_bp
    from routes.analytics import analytics_bp
    from routes.export    import export_bp
    from routes.data      import data_bp

    app.register_blueprint(upload_bp,    url_prefix="/api/upload")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(export_bp,    url_prefix="/api/export")
    app.register_blueprint(data_bp,      url_prefix="/api/data")

    # ── Frontend ───────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        """Serve the dashboard. This is what opens in the browser."""
        return send_from_directory(PROJECT_ROOT, "index.html")

    @app.route("/sample-data/<path:filename>")
    def serve_sample(filename):
        """Serve sample CSV/XLSX/JSON download files."""
        return send_from_directory(os.path.join(PROJECT_ROOT, "sample-data"), filename)

    # ── API info ───────────────────────────────────────────────────────────────
    @app.route("/api")
    @app.route("/api/")
    def api_root():
        db_url    = os.getenv("DATABASE_URL", "")
        db_status = "not configured — add DATABASE_URL to Vercel env vars"
        if db_url:
            try:
                from db.database import test_connection
                db_status = "connected ✅" if test_connection() else "connection failed ❌"
            except Exception as e:
                db_status = f"error: {e}"

        return jsonify({
            "app":      "SalesIQ BI Dashboard API",
            "version":  "2.0.0",
            "status":   "running",
            "database": db_status,
            "frontend": "Open the root URL in your browser (not /api)",
            "docs":     "/api/docs",
        })

    @app.route("/api/health")
    def health():
        db_url = os.getenv("DATABASE_URL", "")
        db_ok, db_msg = False, "DATABASE_URL not set"
        if db_url:
            try:
                from db.database import test_connection
                db_ok  = test_connection()
                db_msg = "connected" if db_ok else "connection failed"
            except Exception as e:
                db_msg = str(e)
        return jsonify({"status": "ok", "database": db_msg, "db_ok": db_ok})

    @app.route("/api/db/init", methods=["POST"])
    def db_init():
        """Create Neon DB tables. Call once: POST /api/db/init"""
        try:
            from db.database import init_db
            init_db()
            return jsonify({"success": True, "message": "Database tables created successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/docs")
    def docs():
        return jsonify({
            "title":    "SalesIQ BI Dashboard API v2",
            "database": "Neon PostgreSQL",
            "tip":      "Open the root URL (/) in a browser to see the dashboard",
            "endpoints": [
                "GET  /                         → Dashboard UI",
                "GET  /api/health               → Health + DB check",
                "POST /api/db/init              → Create DB tables (run once)",
                "POST /api/upload/file          → Upload CSV/XLSX/JSON/TSV",
                "GET  /api/upload/sessions      → List sessions",
                "DELETE /api/upload/session/<id>→ Delete session",
                "GET  /api/analytics/summary    → KPI metrics",
                "GET  /api/analytics/revenue    → Revenue over time",
                "GET  /api/analytics/categories → By category",
                "GET  /api/analytics/regions    → By region",
                "GET  /api/analytics/reps       → By sales rep",
                "GET  /api/analytics/products   → Top products",
                "GET  /api/analytics/dax        → DAX measures",
                "GET  /api/data/records         → Paginated records",
                "GET  /api/export/csv           → Download CSV",
                "GET  /api/export/xlsx          → Download Excel",
                "GET  /api/export/json          → Download JSON",
                "GET  /api/export/tsv           → Download TSV",
                "GET  /api/export/summary       → KPI report CSV",
            ]
        })

    # ── Error handlers ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "error": "Not Found",
            "tip":   "Open the root URL in your browser to see the dashboard",
        }), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large. Maximum is 50 MB."}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    return app


# Create the app instance (used by Vercel via api/index.py)
app = create_app()

# ── Local dev server ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "")

    print("\n" + "=" * 55)
    print("  SalesIQ BI Dashboard v2")
    print("  ► Dashboard:  http://localhost:5000       ← open this!")
    print("  ► API:        http://localhost:5000/api")
    print("  ► Docs:       http://localhost:5000/api/docs")
    print("  ► DB:        ", "✅ Neon configured" if db_url else "⚠️  Set DATABASE_URL in .env")
    print("=" * 55 + "\n")

    if db_url:
        try:
            from db.database import init_db
            init_db()
        except Exception as e:
            print(f"⚠️  DB init: {e}\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
