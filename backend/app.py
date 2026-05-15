"""
SalesIQ BI Dashboard — Flask Backend v2
========================================
- Serves frontend (index.html) at /   ← fixes "only JSON shown" issue
- REST API at /api/...
- Neon PostgreSQL via SQLAlchemy
- Vercel-compatible

Run locally:  python app.py
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Paths
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND_DIR, "..")   # bi-dashboard/ root


def create_app():
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path=""
    )
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.config["UPLOAD_FOLDER"]      = os.path.join(BACKEND_DIR, "uploads")
    app.config["EXPORT_FOLDER"]      = os.path.join(BACKEND_DIR, "exports")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["ALLOWED_EXTENSIONS"] = {"csv", "xlsx", "xls", "json", "tsv"}

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    # ── API Blueprints ─────────────────────────────────────────────────────────
    from routes.upload    import upload_bp
    from routes.analytics import analytics_bp
    from routes.export    import export_bp
    from routes.data      import data_bp

    app.register_blueprint(upload_bp,    url_prefix="/api/upload")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(export_bp,    url_prefix="/api/export")
    app.register_blueprint(data_bp,      url_prefix="/api/data")

    # ── Frontend — serve index.html at / ──────────────────────────────────────
    @app.route("/")
    def index():
        """Serve the dashboard frontend. Fixes the 'only JSON at /' issue."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/sample-data/<path:filename>")
    def sample_data(filename):
        """Serve sample data files for download."""
        sample_dir = os.path.join(FRONTEND_DIR, "sample-data")
        return send_from_directory(sample_dir, filename)

    # ── API Info ───────────────────────────────────────────────────────────────
    @app.route("/api")
    @app.route("/api/")
    def api_root():
        db_url = os.getenv("DATABASE_URL", "")
        db_status = "not configured"
        if db_url:
            try:
                from db.database import test_connection
                db_status = "connected" if test_connection() else "connection failed"
            except Exception as e:
                db_status = f"error: {e}"

        return jsonify({
            "app":      "SalesIQ BI Dashboard API",
            "version":  "2.0.0",
            "status":   "running",
            "database": db_status,
            "frontend": "Open http://localhost:5000 in your browser",
            "docs":     "http://localhost:5000/api/docs",
        })

    @app.route("/api/health")
    def health():
        db_url = os.getenv("DATABASE_URL", "")
        db_ok, db_msg = False, "DATABASE_URL not set in .env"
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
        """Create DB tables. Call once after deploy: POST /api/db/init"""
        try:
            from db.database import init_db
            init_db()
            return jsonify({"success": True, "message": "Tables created"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/docs")
    def docs():
        return jsonify({
            "title": "SalesIQ API v2 — Neon DB Edition",
            "open_browser": "http://localhost:5000",
            "endpoints": [
                "GET  /              → Dashboard UI (your browser)",
                "GET  /api/health    → Health + DB check",
                "POST /api/db/init   → Create DB tables (once)",
                "POST /api/upload/file         → Upload data file",
                "GET  /api/upload/sessions     → All sessions",
                "GET  /api/analytics/summary   → KPIs",
                "GET  /api/analytics/revenue   → Revenue chart data",
                "GET  /api/analytics/categories",
                "GET  /api/analytics/regions",
                "GET  /api/analytics/reps",
                "GET  /api/analytics/products",
                "GET  /api/analytics/dax       → DAX measures",
                "GET  /api/data/records        → Paginated table",
                "GET  /api/export/csv|xlsx|json|tsv|summary",
            ]
        })

    # ── Error Handlers ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not Found", "tip": "Open http://localhost:5000 for the dashboard"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large. Max 50 MB."}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "")

    print("\n" + "="*55)
    print("  SalesIQ BI Dashboard v2")
    print("  ► Open browser:  http://localhost:5000")
    print("  ► API root:      http://localhost:5000/api")
    print("  ► API docs:      http://localhost:5000/api/docs")
    print(f"  ► Database:      {'✅ Neon PostgreSQL configured' if db_url else '⚠️  Add DATABASE_URL to .env'}")
    print("="*55 + "\n")

    if db_url:
        try:
            from db.database import init_db
            init_db()
        except Exception as e:
            print(f"⚠️  DB init: {e}\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
