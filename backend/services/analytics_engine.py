"""
Enterprise Analytics Engine.
Performs schema detection, descriptive statistics, KPI extraction,
and automated business insight detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import structlog
from scipy import stats as scipy_stats

logger = structlog.get_logger()


# ──────────────────────────────────────────────
# SCHEMA DETECTION
# ──────────────────────────────────────────────

def detect_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Identify column types, nulls, cardinality, and outliers.
    Returns structured schema metadata.
    """
    schema = {
        "columns": {},
        "numeric_columns": [],
        "categorical_columns": [],
        "datetime_columns": [],
        "identifier_columns": [],
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }

    for col in df.columns:
        col_info: Dict[str, Any] = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "null_pct": round(df[col].isnull().mean() * 100, 2),
            "unique_count": int(df[col].nunique()),
        }

        # Try datetime detection
        if df[col].dtype == object:
            try:
                parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                if parsed.notna().mean() > 0.8:
                    col_info["detected_type"] = "datetime"
                    schema["datetime_columns"].append(col)
                    col_info["min_date"] = str(parsed.min())
                    col_info["max_date"] = str(parsed.max())
                    schema["columns"][col] = col_info
                    continue
            except Exception:
                pass

        # Numeric columns
        if pd.api.types.is_numeric_dtype(df[col]):
            # Outlier detection via IQR
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outlier_count = int(((df[col] < lower_fence) | (df[col] > upper_fence)).sum())

            col_info.update({
                "detected_type": "numeric",
                "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                "outlier_count": outlier_count,
                "outlier_pct": round(outlier_count / max(len(df), 1) * 100, 2),
            })
            schema["numeric_columns"].append(col)

        else:
            # High-cardinality = likely ID
            if col_info["unique_count"] == len(df) or col.lower() in ("id", "uuid", "key", "code"):
                col_info["detected_type"] = "identifier"
                schema["identifier_columns"].append(col)
            else:
                col_info["detected_type"] = "categorical"
                col_info["top_values"] = df[col].value_counts().head(5).to_dict()
                schema["categorical_columns"].append(col)

        schema["columns"][col] = col_info

    return schema


# ──────────────────────────────────────────────
# DESCRIPTIVE STATISTICS
# ──────────────────────────────────────────────

def compute_descriptive_stats(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    numeric_cols = schema["numeric_columns"]
    if not numeric_cols:
        return {"message": "No numeric columns found"}

    num_df = df[numeric_cols].copy()

    stats: Dict[str, Any] = {}

    # Per-column stats
    desc = num_df.describe().T
    for col in numeric_cols:
        col_stats = {
            "mean": round(float(desc.loc[col, "mean"]), 4) if col in desc.index else None,
            "median": round(float(num_df[col].median()), 4),
            "std": round(float(desc.loc[col, "std"]), 4) if col in desc.index else None,
            "variance": round(float(num_df[col].var()), 4),
            "min": round(float(desc.loc[col, "min"]), 4) if col in desc.index else None,
            "max": round(float(desc.loc[col, "max"]), 4) if col in desc.index else None,
            "q1": round(float(num_df[col].quantile(0.25)), 4),
            "q3": round(float(num_df[col].quantile(0.75)), 4),
            "skewness": round(float(num_df[col].skew()), 4),
            "kurtosis": round(float(num_df[col].kurtosis()), 4),
        }
        # Mode (handle multi-mode)
        mode_vals = num_df[col].mode()
        col_stats["mode"] = float(mode_vals.iloc[0]) if len(mode_vals) > 0 else None
        stats[col] = col_stats

    # Correlation matrix
    if len(numeric_cols) > 1:
        corr = num_df.corr().round(4)
        stats["correlation_matrix"] = corr.where(~corr.isna(), other=None).to_dict()

    # Null distribution
    stats["null_distribution"] = {
        col: int(df[col].isnull().sum()) for col in df.columns if df[col].isnull().any()
    }

    return stats


# ──────────────────────────────────────────────
# KPI EXTRACTION
# ──────────────────────────────────────────────

def extract_kpis(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    kpis: Dict[str, Any] = {}
    numeric_cols = schema["numeric_columns"]
    datetime_cols = schema["datetime_columns"]
    categorical_cols = schema["categorical_columns"]

    # Revenue/sales column detection
    revenue_keywords = ["revenue", "sales", "amount", "total", "price", "income", "profit", "value"]
    revenue_cols = [c for c in numeric_cols if any(kw in c.lower() for kw in revenue_keywords)]
    region_keywords = ["region", "country", "city", "state", "territory", "location", "area"]
    region_cols = [c for c in categorical_cols if any(kw in c.lower() for kw in region_keywords)]

    if revenue_cols:
        main_rev = revenue_cols[0]
        kpis["total_revenue"] = round(float(df[main_rev].sum()), 2)
        kpis["average_revenue"] = round(float(df[main_rev].mean()), 2)
        kpis["revenue_column"] = main_rev

        # Month-over-month if datetime present
        if datetime_cols:
            date_col = datetime_cols[0]
            try:
                temp = df[[date_col, main_rev]].copy()
                temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
                temp = temp.dropna(subset=[date_col])
                temp["month"] = temp[date_col].dt.to_period("M")
                monthly = temp.groupby("month")[main_rev].sum().sort_index()
                if len(monthly) >= 2:
                    mom_change = ((monthly.iloc[-1] - monthly.iloc[-2]) / abs(monthly.iloc[-2])) * 100
                    kpis["mom_change_pct"] = round(float(mom_change), 2)
                    kpis["monthly_revenue"] = {str(k): round(float(v), 2) for k, v in monthly.items()}
                # Growth rate (first vs last available period)
                if len(monthly) >= 2:
                    growth = ((monthly.iloc[-1] - monthly.iloc[0]) / abs(monthly.iloc[0])) * 100
                    kpis["total_growth_pct"] = round(float(growth), 2)
            except Exception as e:
                logger.debug("mom_calc_failed", error=str(e))

        # Regional performance
        if region_cols:
            region_col = region_cols[0]
            regional = df.groupby(region_col)[main_rev].sum().sort_values(ascending=False)
            kpis["regional_performance"] = {
                str(k): round(float(v), 2) for k, v in regional.head(10).items()
            }
            kpis["top_region"] = str(regional.index[0]) if len(regional) > 0 else None
            kpis["bottom_region"] = str(regional.index[-1]) if len(regional) > 0 else None

    # General numeric KPIs
    kpis["numeric_summary"] = {}
    for col in numeric_cols[:5]:  # top 5 numeric columns
        kpis["numeric_summary"][col] = {
            "sum": round(float(df[col].sum()), 2),
            "mean": round(float(df[col].mean()), 2),
        }

    return kpis


# ──────────────────────────────────────────────
# AUTOMATED INSIGHT DETECTION
# ──────────────────────────────────────────────

def detect_insights(df: pd.DataFrame, schema: Dict[str, Any], kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights = []
    numeric_cols = schema["numeric_columns"]
    datetime_cols = schema["datetime_columns"]

    # 1. Declining trend detection
    if datetime_cols and "monthly_revenue" in kpis:
        monthly = kpis["monthly_revenue"]
        values = list(monthly.values())
        if len(values) >= 3:
            last_3 = values[-3:]
            if all(last_3[i] > last_3[i + 1] for i in range(len(last_3) - 1)):
                insights.append({
                    "type": "warning",
                    "category": "trend",
                    "title": "Declining Revenue Trend",
                    "description": f"Revenue has declined for 3 consecutive periods. Last period: {last_3[-1]:,.2f}",
                    "severity": "high",
                })

    # 2. MoM drop alert
    if "mom_change_pct" in kpis and kpis["mom_change_pct"] < -10:
        insights.append({
            "type": "warning",
            "category": "revenue",
            "title": "Significant Month-over-Month Revenue Drop",
            "description": f"Revenue dropped {abs(kpis['mom_change_pct']):.1f}% vs. previous month.",
            "severity": "high",
        })
    elif "mom_change_pct" in kpis and kpis["mom_change_pct"] > 15:
        insights.append({
            "type": "success",
            "category": "revenue",
            "title": "Strong Month-over-Month Growth",
            "description": f"Revenue grew {kpis['mom_change_pct']:.1f}% vs. previous month.",
            "severity": "low",
        })

    # 3. High null percentage columns
    for col, info in schema["columns"].items():
        if info.get("null_pct", 0) > 20:
            insights.append({
                "type": "warning",
                "category": "data_quality",
                "title": f"High Missing Values: {col}",
                "description": f"Column '{col}' has {info['null_pct']:.1f}% missing values which may affect analysis accuracy.",
                "severity": "medium",
            })

    # 4. Outlier detection
    for col in numeric_cols:
        info = schema["columns"].get(col, {})
        if info.get("outlier_pct", 0) > 5:
            insights.append({
                "type": "info",
                "category": "anomaly",
                "title": f"Outliers Detected: {col}",
                "description": f"{info['outlier_pct']:.1f}% of '{col}' values are statistical outliers (IQR method).",
                "severity": "medium",
            })

    # 5. Top/bottom regional performance
    if "top_region" in kpis and kpis.get("top_region"):
        insights.append({
            "type": "success",
            "category": "regional",
            "title": f"Top Performing Region: {kpis['top_region']}",
            "description": f"Highest revenue generated from {kpis['top_region']}.",
            "severity": "low",
        })

    if len(insights) == 0:
        insights.append({
            "type": "info",
            "category": "general",
            "title": "Data Looks Healthy",
            "description": "No significant anomalies or trends detected. Data quality appears good.",
            "severity": "low",
        })

    return insights


# ──────────────────────────────────────────────
# FULL ANALYTICS PIPELINE
# ──────────────────────────────────────────────

def run_full_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Run the complete analytics pipeline and return all results."""
    schema = detect_schema(df)
    stats = compute_descriptive_stats(df, schema)
    kpis = extract_kpis(df, schema)
    insights = detect_insights(df, schema, kpis)

    return {
        "schema": schema,
        "stats": stats,
        "kpis": kpis,
        "insights": insights,
    }
