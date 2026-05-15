"""
routes/upload.py — File upload, saves to Neon PostgreSQL
"""
import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from utils.data_processor import parse_file, get_filter_options_from_df
from db.operations import (
    save_upload_session, list_sessions,
    get_session_info, delete_session, get_latest_session_id, get_filter_options
)

upload_bp = Blueprint("upload", __name__)

USE_DB = bool(os.getenv("DATABASE_URL", ""))


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@upload_bp.route("/file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use key 'file' in form-data."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Unsupported format", "allowed": list(current_app.config["ALLOWED_EXTENSIONS"])}), 400

    filename  = secure_filename(f.filename)
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    f.save(save_path)

    try:
        df, session_id = parse_file(save_path, filename, use_db=USE_DB)
    except Exception as e:
        os.remove(save_path)
        return jsonify({"error": f"Parse error: {str(e)}"}), 422

    # If DB enabled, persist to Neon
    if USE_DB:
        try:
            session_id = save_upload_session(df, filename)
            filter_opts = get_filter_options(session_id)
        except Exception as e:
            # Fallback to in-memory if DB fails
            filter_opts = get_filter_options_from_df(df)
    else:
        filter_opts = get_filter_options_from_df(df)

    date_range = {}
    if "date" in df.columns:
        valid = df["date"].dropna()
        if not valid.empty:
            date_range = {
                "from": valid.min().strftime("%Y-%m-%d"),
                "to":   valid.max().strftime("%Y-%m-%d"),
            }

    return jsonify({
        "success":        True,
        "session_id":     session_id,
        "filename":       filename,
        "rows":           len(df),
        "columns":        list(df.columns),
        "filter_options": filter_opts,
        "date_range":     date_range,
        "storage":        "neon_db" if USE_DB else "in_memory",
        "message":        f"Loaded {len(df)} records from '{filename}'"
    }), 201


@upload_bp.route("/sessions", methods=["GET"])
def get_sessions():
    if USE_DB:
        return jsonify({"sessions": list_sessions()})
    from utils.data_processor import list_sessions as mem_sessions
    return jsonify({"sessions": mem_sessions()})


@upload_bp.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    if USE_DB:
        info = get_session_info(session_id)
    else:
        from utils.data_processor import get_session as mem_get
        s = mem_get(session_id)
        info = {"session_id": session_id, "filename": s["filename"], "rows": s["rows"]} if s else None

    if not info:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404
    return jsonify(info)


@upload_bp.route("/session/<session_id>", methods=["DELETE"])
def remove_session(session_id):
    if USE_DB:
        ok = delete_session(session_id)
    else:
        from utils.data_processor import delete_session as mem_del
        ok = mem_del(session_id)

    if ok:
        return jsonify({"success": True, "message": f"Session '{session_id}' deleted"})
    return jsonify({"error": f"Session '{session_id}' not found"}), 404
