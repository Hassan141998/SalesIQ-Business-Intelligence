"""
routes/data.py
===============
Raw data browsing endpoints.

GET /api/data/records    — paginated, filtered, sorted records
GET /api/data/columns    — column list for active session
GET /api/data/sample     — first N rows (quick preview)
"""

from flask import Blueprint, request, jsonify
from utils.data_processor import (
    get_session_df, get_latest_session_id,
    apply_filters, paginate,
)
import numpy as np

data_bp = Blueprint("data", __name__)


def _get_df():
    session_id = request.args.get("session_id") or get_latest_session_id()
    if not session_id:
        return None, jsonify({"error": "No data loaded. Upload a file first."}), 400
    df = get_session_df(session_id)
    if df is None:
        return None, jsonify({"error": f"Session '{session_id}' not found"}), 404
    return df, None, None


@data_bp.route("/records", methods=["GET"])
def records():
    """
    Paginated, filtered, sorted data records.

    Query params:
      session_id  — (optional) defaults to latest
      page        — page number (default 1)
      page_size   — rows per page (default 20, max 500)
      sort_by     — column name to sort by
      sort_dir    — asc | desc (default asc)
      region, category, rep, date_from, date_to, search  — filters
    """
    df, err, code = _get_df()
    if err:
        return err, code

    # Filters
    params = {
        "region":    request.args.get("region", ""),
        "category":  request.args.get("category", ""),
        "rep":       request.args.get("rep", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to":   request.args.get("date_to", ""),
        "search":    request.args.get("search", ""),
    }
    filtered = apply_filters(df, params)

    # Pagination / sorting
    try:
        page      = max(1, int(request.args.get("page", 1)))
        page_size = min(500, max(1, int(request.args.get("page_size", 20))))
    except ValueError:
        return jsonify({"error": "page and page_size must be integers"}), 400

    sort_by  = request.args.get("sort_by", None)
    sort_dir = request.args.get("sort_dir", "asc")

    result = paginate(filtered, page=page, page_size=page_size,
                      sort_by=sort_by, sort_dir=sort_dir)

    result["filters_applied"] = {k: v for k, v in params.items() if v}
    return jsonify(result)


@data_bp.route("/columns", methods=["GET"])
def columns():
    """Return list of columns and their data types for the active session."""
    df, err, code = _get_df()
    if err:
        return err, code

    cols = [
        {"name": col, "dtype": str(df[col].dtype), "sample": str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else ""}
        for col in df.columns
    ]
    return jsonify({"columns": cols, "total_rows": len(df)})


@data_bp.route("/sample", methods=["GET"])
def sample():
    """
    Return first N rows as a quick preview.
    Query param: n=5 (default)
    """
    df, err, code = _get_df()
    if err:
        return err, code

    try:
        n = min(100, max(1, int(request.args.get("n", 5))))
    except ValueError:
        return jsonify({"error": "n must be an integer"}), 400

    preview = df.head(n).copy()
    if "date" in preview.columns:
        preview["date"] = preview["date"].dt.strftime("%Y-%m-%d").where(preview["date"].notna(), None)

    return jsonify({
        "n":       n,
        "records": preview.replace({np.nan: None}).to_dict(orient="records"),
    })
