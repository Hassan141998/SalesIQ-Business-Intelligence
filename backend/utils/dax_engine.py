"""
utils/dax_engine.py
====================
Extended Power BI DAX-equivalent calculations in Python/Pandas.
These mirror real DAX formulas used in Power BI Desktop.

Usage:
    from utils.dax_engine import DAXEngine
    engine = DAXEngine(df)
    results = engine.all_measures()
"""

import pandas as pd
import numpy as np
from typing import Union


class DAXEngine:
    """
    Computes DAX-equivalent measures from a Pandas DataFrame.
    Each method mirrors a real Power BI DAX formula.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._revenue = float(df["revenue"].sum()) if "revenue" in df.columns else 0
        self._profit  = float(df["profit"].sum())  if "profit"  in df.columns else 0
        self._cost    = float(df["cost"].sum())    if "cost"    in df.columns else 0
        self._units   = float(df["units"].sum())   if "units"   in df.columns else 0
        self._orders  = len(df)

    def _safe_div(self, numerator: float, denominator: float) -> float:
        """Equivalent to DAX DIVIDE() — returns 0 on division by zero."""
        return round(numerator / denominator, 4) if denominator != 0 else 0

    # ── Basic Aggregations ─────────────────────────────────────────────────────

    def total_revenue(self) -> float:
        """DAX: Total Revenue = SUM(Sales[Revenue])"""
        return round(self._revenue, 2)

    def total_profit(self) -> float:
        """DAX: Total Profit = SUM(Sales[Profit])"""
        return round(self._profit, 2)

    def total_cost(self) -> float:
        """DAX: Total Cost = SUM(Sales[Cost])"""
        return round(self._cost, 2)

    def total_units(self) -> int:
        """DAX: Total Units = SUM(Sales[Units])"""
        return int(self._units)

    def total_orders(self) -> int:
        """DAX: Order Count = COUNTROWS(Sales)"""
        return self._orders

    # ── Ratio Measures ─────────────────────────────────────────────────────────

    def profit_margin_pct(self) -> float:
        """DAX: Profit Margin % = DIVIDE(SUM(Sales[Profit]), SUM(Sales[Revenue])) * 100"""
        return round(self._safe_div(self._profit, self._revenue) * 100, 2)

    def cost_ratio_pct(self) -> float:
        """DAX: Cost Ratio % = DIVIDE(SUM(Sales[Cost]), SUM(Sales[Revenue])) * 100"""
        return round(self._safe_div(self._cost, self._revenue) * 100, 2)

    def gross_margin_pct(self) -> float:
        """DAX: Gross Margin % = DIVIDE(SUM(Revenue) - SUM(Cost), SUM(Revenue)) * 100"""
        gross = self._revenue - self._cost
        return round(self._safe_div(gross, self._revenue) * 100, 2)

    # ── Per-Unit / Per-Order ───────────────────────────────────────────────────

    def avg_order_value(self) -> float:
        """DAX: AOV = DIVIDE(SUM(Sales[Revenue]), COUNTROWS(Sales))"""
        return round(self._safe_div(self._revenue, self._orders), 2)

    def revenue_per_unit(self) -> float:
        """DAX: Revenue per Unit = DIVIDE(SUM(Sales[Revenue]), SUM(Sales[Units]))"""
        return round(self._safe_div(self._revenue, self._units), 2)

    def profit_per_order(self) -> float:
        """DAX: Profit per Order = DIVIDE(SUM(Sales[Profit]), COUNTROWS(Sales))"""
        return round(self._safe_div(self._profit, self._orders), 2)

    def units_per_order(self) -> float:
        """DAX: Units per Order = DIVIDE(SUM(Sales[Units]), COUNTROWS(Sales))"""
        return round(self._safe_div(self._units, self._orders), 2)

    # ── Time Intelligence ──────────────────────────────────────────────────────

    def mom_revenue_growth(self) -> dict:
        """
        DAX equivalent: Month-over-Month Revenue Growth %
        = DIVIDE([Revenue] - [Revenue PreviousMonth], [Revenue PreviousMonth]) * 100
        """
        if "date" not in self.df.columns:
            return {}
        tmp = self.df.dropna(subset=["date"]).copy()
        tmp["month"] = tmp["date"].dt.to_period("M")
        monthly = tmp.groupby("month")["revenue"].sum().sort_index()
        pct_change = monthly.pct_change() * 100
        return {
            str(k): round(float(v), 2)
            for k, v in pct_change.dropna().items()
        }

    def yoy_revenue_growth(self) -> dict:
        """Year-over-Year Revenue Growth %"""
        if "date" not in self.df.columns:
            return {}
        tmp = self.df.dropna(subset=["date"]).copy()
        tmp["year"] = tmp["date"].dt.year
        annual = tmp.groupby("year")["revenue"].sum().sort_index()
        pct_change = annual.pct_change() * 100
        return {
            str(k): round(float(v), 2)
            for k, v in pct_change.dropna().items()
        }

    def running_total_revenue(self) -> list:
        """
        DAX: Running Total = CALCULATE(SUM(Revenue), DATESYTD(Calendar[Date]))
        Returns monthly cumulative revenue.
        """
        if "date" not in self.df.columns:
            return []
        tmp = self.df.dropna(subset=["date"]).copy()
        tmp["month"] = tmp["date"].dt.to_period("M")
        monthly = tmp.groupby("month")["revenue"].sum().sort_index()
        cumulative = monthly.cumsum()
        return [
            {"period": str(k), "revenue": round(float(v), 2)}
            for k, v in cumulative.items()
        ]

    # ── Category Measures ──────────────────────────────────────────────────────

    def category_revenue_share(self) -> list:
        """
        DAX: Category Share % = DIVIDE([Category Revenue], [Total Revenue]) * 100
        """
        if "category" not in self.df.columns:
            return []
        grp = self.df.groupby("category")["revenue"].sum()
        total = grp.sum()
        return [
            {
                "category": cat,
                "revenue":  round(float(rev), 2),
                "share_pct": round(float(rev / total * 100), 2) if total > 0 else 0,
            }
            for cat, rev in grp.sort_values(ascending=False).items()
        ]

    def top_category(self) -> str:
        """DAX: Top Category = TOPN(1, VALUES(Category), [Total Revenue])"""
        if "category" not in self.df.columns:
            return ""
        grp = self.df.groupby("category")["revenue"].sum()
        return grp.idxmax() if not grp.empty else ""

    def top_product(self) -> str:
        """DAX: Top Product by Revenue"""
        if "product" not in self.df.columns:
            return ""
        grp = self.df.groupby("product")["revenue"].sum()
        return grp.idxmax() if not grp.empty else ""

    def top_rep(self) -> str:
        """DAX: Top Sales Rep by Revenue"""
        if "rep" not in self.df.columns:
            return ""
        grp = self.df.groupby("rep")["revenue"].sum()
        return grp.idxmax() if not grp.empty else ""

    # ── Statistical Measures ───────────────────────────────────────────────────

    def revenue_std_dev(self) -> float:
        """DAX: Revenue StdDev = STDEV.P(Sales[Revenue])"""
        return round(float(self.df["revenue"].std()), 2) if "revenue" in self.df.columns else 0

    def revenue_median(self) -> float:
        """DAX: Revenue Median = MEDIAN(Sales[Revenue])"""
        return round(float(self.df["revenue"].median()), 2) if "revenue" in self.df.columns else 0

    def revenue_max(self) -> float:
        """DAX: Max Revenue = MAX(Sales[Revenue])"""
        return round(float(self.df["revenue"].max()), 2) if "revenue" in self.df.columns else 0

    def revenue_min(self) -> float:
        """DAX: Min Revenue = MIN(Sales[Revenue])"""
        return round(float(self.df["revenue"].min()), 2) if "revenue" in self.df.columns else 0

    # ── All Measures (for API endpoint) ───────────────────────────────────────

    def all_measures(self) -> list:
        """Return all measures as a serializable list."""
        return [
            {"name": "Total Revenue",         "dax": "SUM(Sales[Revenue])",                              "value": self.total_revenue(),        "unit": "$"},
            {"name": "Total Profit",          "dax": "SUM(Sales[Profit])",                               "value": self.total_profit(),         "unit": "$"},
            {"name": "Total Cost",            "dax": "SUM(Sales[Cost])",                                 "value": self.total_cost(),           "unit": "$"},
            {"name": "Total Units",           "dax": "SUM(Sales[Units])",                                "value": self.total_units(),          "unit": "units"},
            {"name": "Total Orders",          "dax": "COUNTROWS(Sales)",                                 "value": self.total_orders(),         "unit": ""},
            {"name": "Profit Margin %",       "dax": "DIVIDE(SUM(Profit), SUM(Revenue)) * 100",          "value": self.profit_margin_pct(),    "unit": "%"},
            {"name": "Cost Ratio %",          "dax": "DIVIDE(SUM(Cost), SUM(Revenue)) * 100",            "value": self.cost_ratio_pct(),       "unit": "%"},
            {"name": "Gross Margin %",        "dax": "DIVIDE(Revenue - Cost, Revenue) * 100",            "value": self.gross_margin_pct(),     "unit": "%"},
            {"name": "Avg Order Value",       "dax": "DIVIDE(SUM(Revenue), COUNTROWS())",                "value": self.avg_order_value(),      "unit": "$"},
            {"name": "Revenue per Unit",      "dax": "DIVIDE(SUM(Revenue), SUM(Units))",                 "value": self.revenue_per_unit(),     "unit": "$"},
            {"name": "Profit per Order",      "dax": "DIVIDE(SUM(Profit), COUNTROWS())",                 "value": self.profit_per_order(),     "unit": "$"},
            {"name": "Units per Order",       "dax": "DIVIDE(SUM(Units), COUNTROWS())",                  "value": self.units_per_order(),      "unit": "units"},
            {"name": "Revenue Std Dev",       "dax": "STDEV.P(Sales[Revenue])",                          "value": self.revenue_std_dev(),      "unit": "$"},
            {"name": "Median Order Revenue",  "dax": "MEDIAN(Sales[Revenue])",                           "value": self.revenue_median(),       "unit": "$"},
            {"name": "Max Order Revenue",     "dax": "MAX(Sales[Revenue])",                              "value": self.revenue_max(),          "unit": "$"},
            {"name": "Min Order Revenue",     "dax": "MIN(Sales[Revenue])",                              "value": self.revenue_min(),          "unit": "$"},
            {"name": "Top Category",          "dax": "TOPN(1, VALUES(Category), [Total Revenue])",       "value": self.top_category(),         "unit": ""},
            {"name": "Top Product",           "dax": "TOPN(1, VALUES(Product), [Total Revenue])",        "value": self.top_product(),          "unit": ""},
            {"name": "Top Sales Rep",         "dax": "TOPN(1, VALUES(Rep), [Total Revenue])",            "value": self.top_rep(),              "unit": ""},
        ]
