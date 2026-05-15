"""
routes/analytics.py — KPI & chart endpoints, DB-backed or in-memory fallback
"""
import os
from flask import Blueprint, request, jsonify

USE_DB = bool(os.getenv("DATABASE_URL", ""))

analytics_bp = Blueprint("analytics", __name__)


def _resolve(request):
    """Get session_id and filter params from request."""
    from db.operations import get_latest_session_id as db_latest
    from utils.data_processor import get_latest_session_id as mem_latest
    session_id = request.args.get("session_id") or (db_latest() if USE_DB else mem_latest())
    params = {
        "region":    request.args.get("region", ""),
        "category":  request.args.get("category", ""),
        "rep":       request.args.get("rep", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to":   request.args.get("date_to", ""),
        "search":    request.args.get("search", ""),
    }
    return session_id, params


def _no_session():
    return jsonify({"error": "No data loaded. Upload a file first via POST /api/upload/file"}), 400


@analytics_bp.route("/summary", methods=["GET"])
def summary():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import compute_kpis, get_session_info
            info = get_session_info(session_id)
            if not info:
                return jsonify({"error": f"Session '{session_id}' not found"}), 404
            kpis = compute_kpis(session_id, params)
        else:
            from utils.data_processor import get_session_df, apply_filters, compute_kpis
            df = get_session_df(session_id)
            if df is None:
                return jsonify({"error": f"Session '{session_id}' not found"}), 404
            kpis = compute_kpis(apply_filters(df, params))

        return jsonify({"session_id": session_id, "filters": {k: v for k, v in params.items() if v}, "kpis": kpis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/revenue", methods=["GET"])
def revenue():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    period = request.args.get("period", "monthly")
    if period not in ("monthly", "quarterly", "yearly"):
        return jsonify({"error": "period must be monthly, quarterly, or yearly"}), 400
    try:
        if USE_DB:
            from db.operations import revenue_over_time
            data = revenue_over_time(session_id, params, period)
        else:
            from utils.data_processor import get_session_df, apply_filters, revenue_over_time
            df = get_session_df(session_id)
            data = revenue_over_time(apply_filters(df, params), period)
        return jsonify({"period": period, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/categories", methods=["GET"])
def categories():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import by_category
            data = by_category(session_id, params)
        else:
            from utils.data_processor import get_session_df, apply_filters, by_category
            data = by_category(apply_filters(get_session_df(session_id), params))
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/regions", methods=["GET"])
def regions():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import by_region
            data = by_region(session_id, params)
        else:
            from utils.data_processor import get_session_df, apply_filters, by_region
            data = by_region(apply_filters(get_session_df(session_id), params))
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/reps", methods=["GET"])
def reps():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import by_rep
            data = by_rep(session_id, params)
        else:
            from utils.data_processor import get_session_df, apply_filters, by_rep
            data = by_rep(apply_filters(get_session_df(session_id), params))
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/products", methods=["GET"])
def products():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        n = int(request.args.get("n", 10))
        if USE_DB:
            from db.operations import top_products
            data = top_products(session_id, params, n)
        else:
            from utils.data_processor import get_session_df, apply_filters, top_products
            data = top_products(apply_filters(get_session_df(session_id), params), n)
        return jsonify({"data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/dax", methods=["GET"])
def dax():
    session_id, params = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import compute_kpis
            from utils.data_processor import dax_measures
            kpis = compute_kpis(session_id, params)
            import pandas as pd
            dummy_df = pd.DataFrame([{
                "revenue": kpis["total_revenue"], "profit": kpis["total_profit"],
                "cost": kpis["total_cost"], "units": kpis["total_units"],
            }] * kpis["total_orders"])
            measures = dax_measures(dummy_df)
        else:
            from utils.data_processor import get_session_df, apply_filters, dax_measures
            df = get_session_df(session_id)
            measures = dax_measures(apply_filters(df, params))
        return jsonify({"measures": measures})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/filters", methods=["GET"])
def filters():
    session_id, _ = _resolve(request)
    if not session_id:
        return _no_session()
    try:
        if USE_DB:
            from db.operations import get_filter_options, get_session_info
            opts = get_filter_options(session_id)
            info = get_session_info(session_id)
        else:
            from utils.data_processor import get_session_df, get_filter_options
            df  = get_session_df(session_id)
            opts = get_filter_options(df)
            info = {}
        return jsonify({"filter_options": opts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
