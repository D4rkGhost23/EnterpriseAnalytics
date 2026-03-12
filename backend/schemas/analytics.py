from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from models.dataset import DatasetStatus, JobStatus


class DatasetUploadResponse(BaseModel):
    id: int
    name: str
    status: DatasetStatus
    file_type: str
    file_size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    status: DatasetStatus
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema_json: Optional[Dict[str, Any]] = None
    insights_json: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnalyticsRequest(BaseModel):
    dataset_id: int


class AnalyticsResponse(BaseModel):
    dataset_id: int
    schema: Dict[str, Any]
    stats: Dict[str, Any]
    kpis: Dict[str, Any]
    insights: List[Dict[str, Any]]
    viz_metadata: List[Dict[str, Any]]


class PredictionRequest(BaseModel):
    dataset_id: int
    model_type: str  # linear_regression, random_forest, kmeans, isolation_forest, decision_tree
    target_column: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    n_clusters: Optional[int] = 3
    forecast_periods: Optional[int] = 12
    parameters: Optional[Dict[str, Any]] = {}


class PredictionResponse(BaseModel):
    job_id: int
    model_type: str
    metrics: Optional[Dict[str, float]] = None
    predictions: Optional[List[Any]] = None
    cluster_data: Optional[List[Dict[str, Any]]] = None
    anomalies: Optional[List[Dict[str, Any]]] = None
    rules: Optional[List[str]] = None
    feature_importances: Optional[Dict[str, float]] = None
    viz_metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    dataset_id: int
    query: str  # SQL-like syntax: SELECT col1, col2 FROM data WHERE col1 > 100 GROUP BY col2


class QueryResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    viz_metadata: Optional[Dict[str, Any]] = None


class JobStatusResponse(BaseModel):
    job_id: int
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
