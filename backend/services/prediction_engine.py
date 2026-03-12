"""
Predictive Intelligence Module.
Supports: Linear Regression (sales forecast), Random Forest (prediction),
Decision Trees (rule extraction), K-Means (segmentation), Isolation Forest (anomaly).
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import structlog
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, IsolationForest
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer

logger = structlog.get_logger()


class PredictionError(Exception):
    pass


def _normalize_result(res: Dict[str, Any]) -> Dict[str, Any]:
    """Transform internal result dicts into the format expected by routers/tests.

    - rename ``model`` → ``model_type``
    - flatten metrics dict into top-level keys (convert ``r2`` to ``r2_score``)
    """
    if not isinstance(res, dict):
        return res
    # rename model key
    if "model" in res:
        res["model_type"] = res.pop("model")
    # flatten metrics entries
    metrics = res.pop("metrics", None)
    if isinstance(metrics, dict):
        for k, v in metrics.items():
            if k == "r2":
                res["r2_score"] = v
            else:
                res[k] = v
    return res


def _prepare_features(df: pd.DataFrame, feature_cols: List[str]) -> np.ndarray:
    """Encode categoricals, impute nulls, return numpy array."""
    X = df[feature_cols].copy()
    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    imputer = SimpleImputer(strategy="mean")
    return imputer.fit_transform(X)


def _prepare_target(df: pd.DataFrame, target_col: str) -> np.ndarray:
    """Encode target column, impute nulls."""
    y = df[target_col].copy()
    if y.dtype == object or str(y.dtype) == "category":
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))
    else:
        y = y.fillna(y.mean())
    return np.array(y)


# ──────────────────────────────────────────────
# LINEAR REGRESSION – SALES FORECAST
# ──────────────────────────────────────────────

def run_linear_regression(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: Optional[List[str]] = None,
    forecast_periods: int = 12,
    datetime_col: Optional[str] = None,
) -> Dict[str, Any]:
    """Linear regression / forecasting helper.

    This routine supports both standard regression (when ``feature_cols`` is
    provided) and simple time-series forecasting when ``datetime_col`` is set.
    Returned dictionaries conform to API/tests by including ``model_type`` and
    placing evaluation metrics at the top level.  A ``confidence_interval``
    field is added for time-series forecasts.
    """
    if datetime_col and datetime_col in df.columns:
        # Time-series forecast mode
        temp = df[[datetime_col, target_col]].copy()
        temp[datetime_col] = pd.to_datetime(temp[datetime_col], errors="coerce")
        temp = temp.dropna().sort_values(datetime_col)
        temp["period_idx"] = range(len(temp))
        X = temp[["period_idx"]].values
        y = temp[target_col].values
        if len(X) < 6:
            raise PredictionError("Need at least 6 data points for time-series forecast")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        # Future forecast
        max_idx = len(temp)
        future_idx = np.array([[max_idx + i] for i in range(1, forecast_periods + 1)])
        future_preds = model.predict(future_idx)
        # Confidence band (simple ± 1 std of residuals)
        residual_std = float(np.std(y_pred - y_test))
        forecast_data = []
        for i, pred in enumerate(future_preds):
            forecast_data.append({
                "period": f"Forecast +{i+1}",
                "predicted": round(float(pred), 2),
                "lower": round(float(pred - 1.96 * residual_std), 2),
                "upper": round(float(pred + 1.96 * residual_std), 2),
            })
        # Historical with fitted values
        historical = []
        all_preds = model.predict(X)
        for i, row in temp.iterrows():
            historical.append({
                "period": str(row[datetime_col])[:10],
                "actual": round(float(row[target_col]), 2),
                "fitted": round(float(all_preds[temp.index.get_loc(i)]), 2),
            })
        # assemble result and normalize
        result = {
            "model": "linear_regression",
            "metrics": {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)},
            "historical": historical[-24:],
            # for tests we return simple list of predicted values
            "forecast": [entry["predicted"] for entry in forecast_data],
            "forecast_details": forecast_data,
            "viz_metadata": {
                "type": "forecast_chart",
                "title": f"{target_col} Forecast",
                "series": [
                    {"name": "Actual", "data_key": "actual", "type": "line", "color": "#3B82F6"},
                    {"name": "Fitted", "data_key": "fitted", "type": "line", "color": "#10B981", "strokeDasharray": "4 4"},
                    {"name": "Forecast", "data_key": "predicted", "type": "line", "color": "#F59E0B"},
                ],
                "forecast_band": {"upper_key": "upper", "lower_key": "lower", "color": "rgba(245,158,11,0.15)"},
            },
        }
        # overall confidence interval for forecast (mean ±1.96 std)
        mean_pred = float(np.mean(future_preds)) if len(future_preds) > 0 else 0.0
        result["confidence_interval"] = {
            "lower": round(mean_pred - 1.96 * residual_std, 4),
            "upper": round(mean_pred + 1.96 * residual_std, 4),
        }
        return _normalize_result(result)
    else:
        if not feature_cols:
            raise PredictionError("feature_cols required for non time-series regression")
        X = _prepare_features(df, feature_cols)
        y = _prepare_target(df, target_col)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        result = {
            "model": "linear_regression",
            "metrics": {
                "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
                "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
                "r2": round(float(r2_score(y_test, y_pred)), 4),
            },
            "coefficients": {f: round(float(c), 4) for f, c in zip(feature_cols, model.coef_)},
        }
        return _normalize_result(result)


# ──────────────────────────────────────────────
# RANDOM FOREST
# ──────────────────────────────────────────────

def run_random_forest(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    task: str = "auto",  # "classification" | "regression" | "auto"
    n_estimators: int = 100,
    return_predictions: bool = False,
) -> Dict[str, Any]:
    """Generic random forest that can act as classifier or regressor.

    ``return_predictions`` is only meaningful for classification tasks.
    """
    X = _prepare_features(df, feature_cols)
    y_raw = df[target_col]
    is_classification = task == "classification" or (task == "auto" and (y_raw.dtype == object or y_raw.nunique() < 15))

    if is_classification:
        y = _prepare_target(df, target_col)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42, max_depth=10)
        model.fit(X_train, y_train)
        from sklearn.metrics import accuracy_score, precision_score, recall_score
        y_pred = model.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        # normalize importances to exactly sum to 1.0 before rounding
        raw_imp = np.array(model.feature_importances_)
        normalized_imp = raw_imp / raw_imp.sum()
        importances = dict(zip(feature_cols, [round(float(x), 4) for x in normalized_imp]))
        # flatten importances to list for tests and adjust largest to ensure sum=1.0
        sorted_items = sorted(importances.items(), key=lambda x: -x[1])
        sorted_imp = [v for _, v in sorted_items]
        # Ensure sum == 1.0 by adjusting the largest value
        current_sum = sum(sorted_imp)
        if current_sum != 1.0:
            adjustment = 1.0 - current_sum
            sorted_imp[0] = round(sorted_imp[0] + adjustment, 4)
        result = {
            "model": "random_forest_classifier",
            "task": "classification",
            "metrics": {"accuracy": round(acc, 4), "precision": round(prec, 4), "recall": round(rec, 4)},
            "feature_importances": sorted_imp,
            "feature_importances_dict": dict(sorted(importances.items(), key=lambda x: -x[1])),
        }
        if return_predictions:
            result["predictions"] = [int(x) for x in y_pred.tolist()]
        return _normalize_result(result)
    else:
        y = _prepare_target(df, target_col)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, max_depth=10)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        # normalize importances to exactly sum to 1.0 before rounding
        raw_imp = np.array(model.feature_importances_)
        normalized_imp = raw_imp / raw_imp.sum()
        importances = dict(zip(feature_cols, [round(float(x), 4) for x in normalized_imp]))
        # Ensure sum == 1.0 by adjusting the largest value
        sorted_items = sorted(importances.items(), key=lambda x: -x[1])
        sorted_imp = [v for _, v in sorted_items]
        current_sum = sum(sorted_imp)
        if current_sum != 1.0:
            adjustment = 1.0 - current_sum
            sorted_imp[0] = round(sorted_imp[0] + adjustment, 4)
        result = {
            "model": "random_forest_regressor",
            "task": "regression",
            "metrics": {
                "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
                "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
                "r2": round(float(r2_score(y_test, y_pred)), 4),
            },
            "feature_importances": dict(sorted(importances.items(), key=lambda x: -x[1])),
        }
        return _normalize_result(result)


# ──────────────────────────────────────────────
# DECISION TREE – RULE EXTRACTION
# ──────────────────────────────────────────────

def run_decision_tree(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    max_depth: int = 4,
) -> Dict[str, Any]:
    """Decision tree classifier with rule extraction."""
    X = _prepare_features(df, feature_cols)
    y = _prepare_target(df, target_col)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
    model.fit(X_train, y_train)
    rules_text = export_text(model, feature_names=feature_cols)
    # rules_text is a readable string; keep as rules for tests
    from sklearn.metrics import accuracy_score
    acc = float(accuracy_score(y_test, model.predict(X_test)))
    result = {
        "model": "decision_tree_classifier",
        "metrics": {"accuracy": round(acc, 4)},
        "rules": rules_text,
        "rules_list": [line.strip() for line in rules_text.split("\n") if line.strip() and "|" in line][:30],
    }
    return _normalize_result(result)


# ──────────────────────────────────────────────
# K-MEANS – CUSTOMER SEGMENTATION
# ──────────────────────────────────────────────

def run_kmeans(
    df: pd.DataFrame,
    feature_cols: List[str],
    n_clusters: int = 3,
) -> Dict[str, Any]:
    if n_clusters < 2 or n_clusters > len(df):
        raise ValueError("n_clusters must be between 2 and number of samples in df")
    X_raw = _prepare_features(df, feature_cols)
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = model.fit_predict(X)
    centroids = scaler.inverse_transform(model.cluster_centers_)
    centroid_list = [
        {"cluster": i, **{f: round(float(centroids[i, j]), 3) for j, f in enumerate(feature_cols)}}
        for i in range(n_clusters)
    ]
    # Cluster distribution
    cluster_counts = {str(i): int((labels == i).sum()) for i in range(n_clusters)}
    # sample per-row cluster assignments
    clusters_list = [int(l) for l in labels.tolist()]
    # Sample data for scatter viz (2D projection using first 2 features)
    scatter_data = []
    for idx in range(min(500, len(df))):
        row = {"cluster": int(labels[idx])}
        for i, col in enumerate(feature_cols[:2]):
            row[col] = round(float(X_raw[idx, i]), 3)
        scatter_data.append(row)
    cluster_colors = ["#3B82F6", "#7C3AED", "#10B981", "#F59E0B", "#EF4444",
                      "#06B6D4", "#F97316", "#8B5CF6", "#EC4899", "#14B8A6"]
    from sklearn.metrics import silhouette_score
    sil_score = float(silhouette_score(X, labels)) if len(df) > 1 else 0.0
    result = {
        "model": "kmeans",
        "n_clusters": n_clusters,
        "clusters": clusters_list,
        "silhouette_score": sil_score,
        "cluster_centers": centroid_list,
        "cluster_distribution": cluster_counts,
        "scatter_data": scatter_data,
        "viz_metadata": {
            "type": "cluster_scatter",
            "title": f"Customer Segmentation ({n_clusters} Clusters)",
            "x_axis": {"key": feature_cols[0] if feature_cols else "x", "label": feature_cols[0] if feature_cols else "X"},
            "y_axis": {"key": feature_cols[1] if len(feature_cols) > 1 else "y", "label": feature_cols[1] if len(feature_cols) > 1 else "Y"},
            "cluster_key": "cluster",
            "cluster_colors": cluster_colors[:n_clusters],
            "data": scatter_data,
        },
        "inertia": round(float(model.inertia_), 2),
    }
    return _normalize_result(result)


# ──────────────────────────────────────────────
# ISOLATION FOREST – ANOMALY DETECTION
# ──────────────────────────────────────────────

def run_isolation_forest(
    df: pd.DataFrame,
    feature_cols: List[str],
    contamination: float = 0.05,
    return_scores: bool = False,
) -> Dict[str, Any]:
    """Perform isolation forest anomaly detection.

    ``return_scores`` will add a ``scores`` list of float anomaly scores.
    """
    X = _prepare_features(df, feature_cols)
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    scores = model.fit_predict(X)
    anomaly_scores = model.score_samples(X)  # Lower = more anomalous
    is_anomaly = scores == -1
    anomaly_df = df[is_anomaly].head(100).copy()
    anomaly_df["anomaly_score"] = anomaly_scores[is_anomaly][:100]
    anomaly_list = anomaly_df.to_dict(orient="records")
    # Replace NaN for JSON
    import math
    def clean(v):
        if isinstance(v, float) and math.isnan(v): return None
        return v
    anomaly_list = [{k: clean(v) for k, v in row.items()} for row in anomaly_list]
    normal_count = int((~is_anomaly).sum())
    result = {
        "model": "isolation_forest",
        "total_records": len(df),
        "anomaly_count": int(is_anomaly.sum()),
        "normal_count": normal_count,
        "anomaly_pct": round(float(is_anomaly.mean() * 100), 2),
        "anomalies": anomaly_list,
        "viz_metadata": {
            "type": "anomaly_scatter",
            "title": "Anomaly Detection Results",
            "annotation": f"{int(is_anomaly.sum())} anomalies detected ({is_anomaly.mean()*100:.1f}%)",
        },
    }
    if return_scores:
        result["scores"] = [float(x) for x in anomaly_scores.tolist()]
    return _normalize_result(result)


# compatibility wrappers expected by unit tests --------------------------------------------------

def run_random_forest_classifier(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    **kwargs,
) -> Dict[str, Any]:
    """Wrapper that forces classification mode for backwards compatibility."""
    return run_random_forest(df, target_col, feature_cols, task="classification", **kwargs)


def run_decision_tree_classifier(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    max_depth: int = 4,
    **kwargs,
) -> Dict[str, Any]:
    return run_decision_tree(df, target_col, feature_cols, max_depth=max_depth)


def run_kmeans_clustering(
    df: pd.DataFrame,
    feature_cols: List[str],
    n_clusters: int = 3,
    **kwargs,
) -> Dict[str, Any]:
    return run_kmeans(df, feature_cols, n_clusters=n_clusters)


def run_isolation_forest_anomaly(
    df: pd.DataFrame,
    feature_cols: List[str],
    contamination: float = 0.05,
    **kwargs,
) -> Dict[str, Any]:
    return run_isolation_forest(df, feature_cols, contamination=contamination, **kwargs)
