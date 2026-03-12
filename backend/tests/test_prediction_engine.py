"""
Unit Tests for Machine Learning / Prediction Engine
Tests: Linear Regression, Random Forest, K-Means, Isolation Forest, Decision Trees
"""
import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from services.prediction_engine import (
    run_linear_regression, run_random_forest_classifier,
    run_decision_tree_classifier, run_kmeans_clustering,
    run_isolation_forest_anomaly, PredictionError
)


# ─────────────────────────────────────────────────────────────
# FIXTURES: Sample DataFrames
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def sales_data():
    """Time series sales data for forecasting."""
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=24, freq="MS"),
        "sales": [10000, 11000, 12500, 13000, 12000, 14000, 15000, 16000,
                  17000, 18000, 19000, 20000, 21000, 22000, 23000, 24000,
                  25000, 26000, 27000, 28000, 29000, 30000, 31000, 32000]
    })


@pytest.fixture
def customer_segmentation_data():
    """Customer data for clustering."""
    np.random.seed(42)
    return pd.DataFrame({
        "age": np.random.randint(18, 80, 100),
        "income": np.random.randint(20000, 150000, 100),
        "spending": np.random.randint(1000, 50000, 100),
        "visits": np.random.randint(1, 50, 100)
    })


@pytest.fixture
def classification_data():
    """Customer data for churn prediction."""
    np.random.seed(42)
    return pd.DataFrame({
        "age": np.random.randint(18, 80, 100),
        "monthly_charges": np.random.randint(20, 120, 100),
        "contract_length_months": np.random.choice([1, 12, 24], 100),
        "churn": np.random.choice([0, 1], 100)
    })


@pytest.fixture
def anomaly_data():
    """Normal data with anomalies for detection."""
    np.random.seed(42)
    data = {
        "transaction_amount": list(np.random.normal(100, 20, 95)) + [5000, 6000, 7000, 8000, 9000],  # 5 anomalies
        "transaction_time": list(range(100))
    }
    return pd.DataFrame(data)


# ─────────────────────────────────────────────────────────────
# TESTS: Linear Regression (Sales Forecast)
# ─────────────────────────────────────────────────────────────

def test_linear_regression_time_series(sales_data):
    """Verify linear regression forecast with time series."""
    result = run_linear_regression(
        df=sales_data,
        target_col="sales",
        datetime_col="date",
        forecast_periods=6
    )

    assert isinstance(result, dict)
    assert "model_type" in result
    assert result["model_type"] == "linear_regression"
    assert "forecast" in result
    assert "confidence_interval" in result
    assert len(result["forecast"]) == 6


def test_linear_regression_returns_metrics(sales_data):
    """Verify regression returns evaluation metrics."""
    result = run_linear_regression(
        df=sales_data,
        target_col="sales",
        datetime_col="date",
    )

    assert "mae" in result
    assert "rmse" in result
    assert "r2_score" in result
    assert isinstance(result["mae"], (int, float))
    assert isinstance(result["rmse"], (int, float))
    assert -1 <= result["r2_score"] <= 1


def test_linear_regression_forecast_increasing_trend(sales_data):
    """Verify forecast follows increasing trend."""
    result = run_linear_regression(
        df=sales_data,
        target_col="sales",
        datetime_col="date",
        forecast_periods=6
    )

    forecast_values = result["forecast"]
    # With increasing sales trend, forecast should be increasing
    for i in range(len(forecast_values) - 1):
        assert forecast_values[i] <= forecast_values[i + 1]


def test_linear_regression_insufficient_data():
    """Verify error when insufficient data points."""
    small_data = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=3, freq="MS"),
        "sales": [100, 110, 120]
    })

    with pytest.raises(PredictionError):
        run_linear_regression(
            df=small_data,
            target_col="sales",
            datetime_col="date"
        )


def test_linear_regression_null_handling(sales_data):
    """Verify null values are handled gracefully."""
    sales_with_nulls = sales_data.copy()
    sales_with_nulls.loc[5, "sales"] = None
    
    # Should not raise exception
    result = run_linear_regression(
        df=sales_with_nulls,
        target_col="sales",
        datetime_col="date"
    )
    assert "forecast" in result


# ─────────────────────────────────────────────────────────────
# TESTS: Random Forest Classifier
# ─────────────────────────────────────────────────────────────

def test_random_forest_classification(classification_data):
    """Verify random forest classifier works."""
    result = run_random_forest_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"]
    )

    assert isinstance(result, dict)
    assert result["model_type"] == "random_forest_classifier"
    assert "feature_importances" in result
    assert "accuracy" in result
    assert "precision" in result
    assert "recall" in result


def test_random_forest_feature_importance(classification_data):
    """Verify feature importances are calculated."""
    result = run_random_forest_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"]
    )

    importances = result["feature_importances"]
    assert len(importances) == 3
    assert sum(importances) <= 1.0 + 1e-6  # Sum of importances ≤ 1


def test_random_forest_metrics_valid_range(classification_data):
    """Verify metrics are in valid ranges."""
    result = run_random_forest_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"]
    )

    assert 0 <= result["accuracy"] <= 1
    assert 0 <= result["precision"] <= 1
    assert 0 <= result["recall"] <= 1


def test_random_forest_predictions_binary(classification_data):
    """Verify predictions are binary (0 or 1)."""
    result = run_random_forest_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"],
        return_predictions=True
    )

    if "predictions" in result:
        predictions = result["predictions"]
        assert all(p in [0, 1] for p in predictions)


# ─────────────────────────────────────────────────────────────
# TESTS: Decision Tree Classifier
# ─────────────────────────────────────────────────────────────

def test_decision_tree_classification(classification_data):
    """Verify decision tree classifier works."""
    result = run_decision_tree_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"]
    )

    assert isinstance(result, dict)
    assert result["model_type"] == "decision_tree_classifier"
    assert "rules" in result or "tree_depth" in result


def test_decision_tree_rule_extraction(classification_data):
    """Verify rules are extracted from tree."""
    result = run_decision_tree_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges"],
        max_depth=3
    )

    assert "rules" in result
    assert isinstance(result["rules"], str)
    assert len(result["rules"]) > 0


def test_decision_tree_metrics(classification_data):
    """Verify decision tree provides metrics."""
    result = run_decision_tree_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges", "contract_length_months"]
    )

    assert "accuracy" in result
    assert 0 <= result["accuracy"] <= 1


# ─────────────────────────────────────────────────────────────
# TESTS: K-Means Clustering (Customer Segmentation)
# ─────────────────────────────────────────────────────────────

def test_kmeans_clustering(customer_segmentation_data):
    """Verify K-Means clustering works."""
    result = run_kmeans_clustering(
        df=customer_segmentation_data,
        feature_cols=["age", "income", "spending"],
        n_clusters=3
    )

    assert isinstance(result, dict)
    assert result["model_type"] == "kmeans"
    assert "clusters" in result
    assert "silhouette_score" in result


def test_kmeans_cluster_assignment(customer_segmentation_data):
    """Verify all points are assigned to clusters."""
    result = run_kmeans_clustering(
        df=customer_segmentation_data,
        feature_cols=["age", "income", "spending"],
        n_clusters=3
    )

    clusters = result["clusters"]
    assert len(clusters) == len(customer_segmentation_data)
    assert set(clusters) == {0, 1, 2}


def test_kmeans_silhouette_score(customer_segmentation_data):
    """Verify silhouette score is in valid range."""
    result = run_kmeans_clustering(
        df=customer_segmentation_data,
        feature_cols=["age", "income", "spending"],
        n_clusters=3
    )

    silhouette = result["silhouette_score"]
    assert -1 <= silhouette <= 1


def test_kmeans_cluster_centers(customer_segmentation_data):
    """Verify cluster centers are returned."""
    result = run_kmeans_clustering(
        df=customer_segmentation_data,
        feature_cols=["age", "income", "spending"],
        n_clusters=3
    )

    if "cluster_centers" in result:
        assert len(result["cluster_centers"]) == 3


def test_kmeans_invalid_cluster_count(customer_segmentation_data):
    """Verify error when cluster count exceeds data size."""
    with pytest.raises((PredictionError, ValueError)):
        run_kmeans_clustering(
            df=customer_segmentation_data,
            feature_cols=["age", "income"],
            n_clusters=200  # More than 100 data points
        )


# ─────────────────────────────────────────────────────────────
# TESTS: Isolation Forest (Anomaly Detection)
# ─────────────────────────────────────────────────────────────

def test_isolation_forest_anomaly_detection(anomaly_data):
    """Verify anomaly detection works."""
    result = run_isolation_forest_anomaly(
        df=anomaly_data,
        feature_cols=["transaction_amount"],
        contamination=0.05
    )

    assert isinstance(result, dict)
    assert result["model_type"] == "isolation_forest"
    assert "anomalies" in result
    assert "normal_count" in result
    assert "anomaly_count" in result


def test_isolation_forest_detects_outliers(anomaly_data):
    """Verify outliers are correctly detected."""
    result = run_isolation_forest_anomaly(
        df=anomaly_data,
        feature_cols=["transaction_amount"],
        contamination=0.05
    )

    anomalies = result["anomalies"]
    # With 5% contamination on 100 points, expect ~5 anomalies
    assert 3 <= result["anomaly_count"] <= 7


def test_isolation_forest_normal_vs_anomaly(anomaly_data):
    """Verify normal count + anomaly count = total."""
    result = run_isolation_forest_anomaly(
        df=anomaly_data,
        feature_cols=["transaction_amount"],
        contamination=0.05
    )

    total = result["normal_count"] + result["anomaly_count"]
    assert total == len(anomaly_data)


def test_isolation_forest_anomaly_scores(anomaly_data):
    """Verify anomaly scores are provided."""
    result = run_isolation_forest_anomaly(
        df=anomaly_data,
        feature_cols=["transaction_amount"],
        contamination=0.05,
        return_scores=True
    )

    if "scores" in result:
        assert len(result["scores"]) == len(anomaly_data)


# ─────────────────────────────────────────────────────────────
# INTEGRATION TESTS: ML Pipeline
# ─────────────────────────────────────────────────────────────

def test_complete_ml_pipeline(sales_data, classification_data, customer_segmentation_data):
    """Verify multiple models can be run in sequence."""
    # Forecast
    forecast_result = run_linear_regression(
        df=sales_data,
        target_col="sales",
        datetime_col="date",
        forecast_periods=6
    )
    assert "forecast" in forecast_result

    # Classify
    classification_result = run_random_forest_classifier(
        df=classification_data,
        target_col="churn",
        feature_cols=["age", "monthly_charges"]
    )
    assert "accuracy" in classification_result

    # Segment
    clustering_result = run_kmeans_clustering(
        df=customer_segmentation_data,
        feature_cols=["age", "income"],
        n_clusters=3
    )
    assert "clusters" in clustering_result


# ─────────────────────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────────────────────

def test_linear_regression_constant_values():
    """Verify handling of constant target values."""
    constant_data = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=12, freq="MS"),
        "sales": [100] * 12  # All same value
    })

    result = run_linear_regression(
        df=constant_data,
        target_col="sales",
        datetime_col="date"
    )
    # Should handle gracefully
    assert "forecast" in result


def test_clustering_with_missing_values(customer_segmentation_data):
    """Verify clustering handles null values."""
    data_with_nulls = customer_segmentation_data.copy()
    data_with_nulls.loc[0, "income"] = None
    
    result = run_kmeans_clustering(
        df=data_with_nulls,
        feature_cols=["age", "income"],
        n_clusters=3
    )
    assert "clusters" in result


def test_classification_imbalanced_classes(classification_data):
    """Verify classification with imbalanced classes."""
    imbalanced = classification_data.copy()
    imbalanced["churn"] = 0  # All class 0
    imbalanced.loc[0:5, "churn"] = 1  # Only 6 class 1
    
    result = run_random_forest_classifier(
        df=imbalanced,
        target_col="churn",
        feature_cols=["age", "monthly_charges"]
    )
    assert "accuracy" in result


def test_anomaly_detection_all_normal():
    """Verify anomaly detection with all normal data."""
    normal_data = pd.DataFrame({
        "amount": np.random.normal(100, 10, 100)
    })

    result = run_isolation_forest_anomaly(
        df=normal_data,
        feature_cols=["amount"],
        contamination=0.05
    )
    # Should still work, detecting some as outliers due to contamination param
    assert result["anomaly_count"] <= 10  # At most 10% anomalies
