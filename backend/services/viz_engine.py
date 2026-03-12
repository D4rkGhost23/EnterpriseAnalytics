"""
Advanced Visualization Metadata Engine.
Determines optimal chart types and returns structured rendering metadata
that the frontend uses to render charts dynamically.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()

# ──────────────────────────────────────────────
# CHART TYPE RECOMMENDATION RULES
# ──────────────────────────────────────────────

def recommend_charts(schema: Dict[str, Any], kpis: Dict[str, Any], stats: Dict[str, Any]) -> List[str]:
    """Rule-based chart type recommendations."""
    recommendations = []
    numeric_cols = schema["numeric_columns"]
    datetime_cols = schema["datetime_columns"]
    categorical_cols = schema["categorical_columns"]

    if datetime_cols and numeric_cols:
        recommendations.append("line_chart")        # Time-series
        recommendations.append("forecast_chart")    # If time series exists, offer forecast

    if categorical_cols and numeric_cols:
        recommendations.append("bar_chart")         # Category vs. metric
        if "regional_performance" in kpis:
            recommendations.append("heatmap")       # Regional heatmap

    if len(numeric_cols) >= 2:
        recommendations.append("scatter_regression")  # Correlation scatter
        recommendations.append("boxplot")             # Distribution comparison
        if "correlation_matrix" in stats:
            recommendations.append("heatmap")

    if numeric_cols:
        recommendations.append("histogram")          # Distribution of numeric col

    if categorical_cols and numeric_cols:
        recommendations.append("bar_line_combo")     # Revenue + trend combined

    return list(dict.fromkeys(recommendations))  # Deduplicate preserving order


# ──────────────────────────────────────────────
# METADATA BUILDERS PER CHART TYPE
# ──────────────────────────────────────────────

def _build_line_chart(df: pd.DataFrame, schema: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    date_col = schema["datetime_columns"][0]
    rev_col = kpis.get("revenue_column") or schema["numeric_columns"][0]
    temp = df[[date_col, rev_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col]).sort_values(date_col)
    # Aggregate by month
    temp["period"] = temp[date_col].dt.to_period("M").astype(str)
    agg = temp.groupby("period")[rev_col].sum().reset_index()
    return {
        "type": "line_chart",
        "title": f"Trend Analysis: {rev_col} Over Time",
        "x_axis": {"key": "period", "label": "Period"},
        "y_axis": {"label": rev_col, "format": "currency"},
        "series": [{"name": rev_col, "data_key": rev_col, "color": "#3B82F6"}],
        "data": agg.to_dict(orient="records"),
        "insight": kpis.get("mom_change_pct") and f"MoM Change: {kpis['mom_change_pct']:+.1f}%",
    }


def _build_bar_chart(df: pd.DataFrame, schema: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    cat_col = schema["categorical_columns"][0]
    rev_col = kpis.get("revenue_column") or schema["numeric_columns"][0]
    agg = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False).head(15).reset_index()
    return {
        "type": "bar_chart",
        "title": f"Top Items: {rev_col} Breakdown by {cat_col}",
        "x_axis": {"key": cat_col, "label": cat_col},
        "y_axis": {"label": rev_col, "format": "number"},
        "series": [{"name": rev_col, "data_key": rev_col, "color": "#7C3AED"}],
        "data": agg.to_dict(orient="records"),
        "insight": f"Top: {agg.iloc[0][cat_col]} with {agg.iloc[0][rev_col]:,.0f}" if len(agg) > 0 else None,
    }


def _build_bar_line_combo(df: pd.DataFrame, schema: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    """Bar for revenue + line for growth rate."""
    if not schema["datetime_columns"]:
        return _build_bar_chart(df, schema, kpis)
    date_col = schema["datetime_columns"][0]
    rev_col = kpis.get("revenue_column") or schema["numeric_columns"][0]
    temp = df[[date_col, rev_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp["period"] = temp[date_col].dt.to_period("M").astype(str)
    agg = temp.groupby("period")[rev_col].sum().reset_index()
    agg["growth_pct"] = agg[rev_col].pct_change() * 100
    agg = agg.fillna(0)
    return {
        "type": "bar_line_combo",
        "title": f"Performance & Growth: {rev_col} with Growth Rate Trend",
        "x_axis": {"key": "period", "label": "Period"},
        "y_axis": {"label": rev_col, "format": "currency"},
        "y2_axis": {"label": "Growth %", "format": "percent"},
        "series": [
            {"name": rev_col, "data_key": rev_col, "type": "bar", "color": "#3B82F6"},
            {"name": "Growth %", "data_key": "growth_pct", "type": "line", "y_axis": "y2", "color": "#10B981"},
        ],
        "data": agg.to_dict(orient="records"),
    }


def _build_heatmap(df: pd.DataFrame, schema: Dict[str, Any], stats: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    # If correlation matrix available, use it
    if "correlation_matrix" in stats and len(schema["numeric_columns"]) > 1:
        corr = stats["correlation_matrix"]
        cells = []
        for row_col, row_data in corr.items():
            if isinstance(row_data, dict):
                for col_col, val in row_data.items():
                    cells.append({"x": col_col, "y": row_col, "value": round(val, 3) if val is not None else 0})
        return {
            "type": "heatmap",
            "title": "Correlation Heatmap",
            "data": cells,
            "x_axis": {"label": "Column"},
            "y_axis": {"label": "Column"},
            "insight": "Values near +1 or -1 indicate strong correlation",
        }
    # Regional heatmap
    if "regional_performance" in kpis:
        regional = kpis["regional_performance"]
        data = [{"region": k, "value": v} for k, v in regional.items()]
        return {
            "type": "heatmap",
            "title": "Regional Revenue Heatmap",
            "data": data,
            "insight": f"Top region: {kpis.get('top_region')}",
        }
    return {}


def _build_scatter(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    num_cols = schema["numeric_columns"]
    if len(num_cols) < 2:
        return {}
    x_col, y_col = num_cols[0], num_cols[1]
    sample = df[[x_col, y_col]].dropna().sample(min(500, len(df))).reset_index(drop=True)
    # Linear regression line
    from numpy.polynomial import polynomial as P
    x_vals = sample[x_col].values
    y_vals = sample[y_col].values
    if len(x_vals) >= 2:
        coeffs = np.polyfit(x_vals, y_vals, 1)
        reg_line = [{"x": float(x), "y": float(coeffs[0] * x + coeffs[1])} for x in [x_vals.min(), x_vals.max()]]
        r2 = float(np.corrcoef(x_vals, y_vals)[0, 1] ** 2)
    else:
        reg_line = []
        r2 = 0

    return {
        "type": "scatter_regression",
        "title": f"Correlation Analysis: {y_col} vs {x_col}",
        "x_axis": {"key": x_col, "label": x_col},
        "y_axis": {"key": y_col, "label": y_col},
        "data": sample.to_dict(orient="records"),
        "regression_line": reg_line,
        "annotations": [{"text": f"R² = {r2:.3f}", "type": "stat"}],
        "insight": f"Correlation R² = {r2:.3f}",
    }


def _build_boxplot(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    num_cols = schema["numeric_columns"][:5]  # top 5
    box_data = []
    series_list = []
    
    for idx, col in enumerate(num_cols):
        series = df[col].dropna()
        q1 = float(series.quantile(0.25))
        med = float(series.median())
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        min_val = float(max(series.min(), q1 - 1.5 * iqr))
        max_val = float(min(series.max(), q3 + 1.5 * iqr))
        
        # Create box data entry
        box_data.append({
            "variable": col,
            "min": min_val,
            "q1": q1,
            "median": med,
            "q3": q3,
            "max": max_val,
        })
        
        # Add to series for visualization
        series_list.append({
            "name": col,
            "data_key": "median",
            "color": ["#3B82F6", "#7C3AED", "#10B981", "#F59E0B", "#EF4444"][idx % 5]
        })
    
    return {
        "type": "boxplot",
        "title": "Statistical Distribution Analysis",
        "x_axis": {"key": "variable", "label": "Variable"},
        "y_axis": {"label": "Value"},
        "data": box_data,
        "series": series_list,
        "insight": "Shows median, quartiles (Q1-Q3), min/max range, and outliers for each variable",
    }


def _build_histogram(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    col = schema["numeric_columns"][0]
    series = df[col].dropna()
    counts, edges = np.histogram(series, bins=20)
    hist_data = [
        {"bin_start": round(float(edges[i]), 2), "bin_end": round(float(edges[i + 1]), 2), "count": int(counts[i])}
        for i in range(len(counts))
    ]
    return {
        "type": "histogram",
        "title": f"Frequency Distribution: {col}",
        "x_axis": {"label": col},
        "y_axis": {"label": "Frequency"},
        "data": hist_data,
        "insight": f"Mean: {series.mean():.2f}, Std Dev: {series.std():.2f}",
    }


# ──────────────────────────────────────────────
# MAIN VIZ METADATA BUILDER
# ──────────────────────────────────────────────

def build_viz_metadata(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    stats: Dict[str, Any],
    kpis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build all recommended visualization metadata objects.
    Frontend renders charts purely from this metadata.
    """
    chart_types = recommend_charts(schema, kpis, stats)
    charts = []

    dispatch = {
        "line_chart": lambda: _build_line_chart(df, schema, kpis),
        "bar_chart": lambda: _build_bar_chart(df, schema, kpis),
        "bar_line_combo": lambda: _build_bar_line_combo(df, schema, kpis),
        "heatmap": lambda: _build_heatmap(df, schema, stats, kpis),
        "scatter_regression": lambda: _build_scatter(df, schema),
        "boxplot": lambda: _build_boxplot(df, schema),
        "histogram": lambda: _build_histogram(df, schema),
    }

    for chart_type in chart_types:
        if chart_type == "forecast_chart":
            continue  # Built by prediction engine
        builder = dispatch.get(chart_type)
        if builder:
            try:
                meta = builder()
                if meta:
                    charts.append(meta)
            except Exception as e:
                logger.warning("chart_build_failed", chart_type=chart_type, error=str(e))

    return charts
