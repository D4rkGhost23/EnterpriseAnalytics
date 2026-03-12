from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np
import pandas as pd

from core.database import get_db
from core.security import get_current_user
from models.dataset import Dataset, DatasetStatus
from schemas.analytics import QueryRequest, QueryResponse
from services.query_engine import execute_query, QueryError

router = APIRouter(prefix="/api/v1/query", tags=["Query Engine"])


@router.post("/", response_model=QueryResponse)
async def run_query(
    req: QueryRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a secure SQL-like query against a dataset's schema."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == req.dataset_id,
            Dataset.tenant_id == current_user.tenant_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    if dataset.status != DatasetStatus.READY:
        raise HTTPException(400, detail="Dataset not ready")

    # Build demo DataFrame from schema for query demo
    schema = dataset.schema_json or {}
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    datetime_cols = schema.get("datetime_columns", [])
    n_rows = min(dataset.row_count or 100, 1000)

    rng = np.random.default_rng(42)
    data = {}
    for col in num_cols:
        col_info = schema.get("columns", {}).get(col, {})
        lo = col_info.get("min", 0) or 0
        hi = col_info.get("max", 10000) or 10000
        data[col] = rng.uniform(lo, hi, n_rows)
    for col in cat_cols:
        top_vals = schema.get("columns", {}).get(col, {}).get("top_values", {})
        choices = list(top_vals.keys()) if top_vals else ["A", "B", "C"]
        data[col] = rng.choice(choices, n_rows)
    for col in datetime_cols:
        dates = pd.date_range("2023-01-01", periods=n_rows, freq="D")
        data[col] = dates.strftime("%Y-%m-%d")

    df = pd.DataFrame(data)

    try:
        query_result = execute_query(df, req.query)
    except QueryError as e:
        raise HTTPException(400, detail=str(e))

    return QueryResponse(
        columns=query_result["columns"],
        rows=query_result["rows"],
        row_count=query_result["row_count"],
    )
