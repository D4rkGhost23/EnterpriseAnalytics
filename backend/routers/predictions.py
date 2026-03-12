import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import pandas as pd
import io
import json
import structlog

from core.database import get_db
from core.security import get_current_user
from models.dataset import Dataset, DatasetStatus, AnalyticsJob, JobStatus
from schemas.analytics import PredictionRequest, PredictionResponse, JobStatusResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/predictions", tags=["Predictions"])


async def _rebuild_dataframe(dataset: Dataset) -> pd.DataFrame:
    """Reconstruct DataFrame from stored data_json in dataset."""
    if not dataset.data_json:
        raise ValueError("Dataset does not have stored data. Please re-upload.")
    
    # data_json is stored as list of dicts (orient='records')
    if isinstance(dataset.data_json, str):
        data = json.loads(dataset.data_json)
    else:
        data = dataset.data_json
    
    return pd.DataFrame(data)


async def _run_prediction_job(job_id: int, dataset_id: int, req_dict: dict, tenant_id: int):
    """Background task: run ML prediction using REAL dataset data and store result in job record."""
    from core.database import AsyncSessionLocal
    from services import prediction_engine as pe
    import asyncio

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AnalyticsJob).where(AnalyticsJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.RUNNING
            await db.commit()

            # Load dataset
            ds_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
            dataset = ds_result.scalar_one_or_none()
            if not dataset or not dataset.schema_json:
                raise ValueError("Dataset not found or not ready")

            # Parse schema JSON
            if isinstance(dataset.schema_json, str):
                schema = json.loads(dataset.schema_json)
            else:
                schema = dataset.schema_json

            # Read REAL data from dataset
            df = await _rebuild_dataframe(dataset)
            logger.info("dataset_loaded", dataset_id=dataset_id, rows=len(df), cols=len(df.columns))

            model_type = req_dict["model_type"]
            target_col = req_dict.get("target_column")
            feature_cols = req_dict.get("feature_columns") or schema.get("numeric_columns", [])[:4]
            result_data = {}

            # Run model based on type
            loop = asyncio.get_event_loop()

            if model_type == "linear_regression":
                # Auto-detect numeric columns for forecast
                num_cols = schema.get("numeric_columns", [])
                if not target_col and num_cols:
                    target_col = num_cols[0]
                if not target_col:
                    raise ValueError("Need numeric column for regression")
                
                forecast_periods = req_dict.get("forecast_periods", 12)
                result_data = await loop.run_in_executor(
                    None, pe.run_linear_regression, df, target_col, None, forecast_periods, None
                )

            elif model_type == "random_forest":
                num_cols = schema.get("numeric_columns", [])
                if not target_col and num_cols:
                    target_col = num_cols[0]
                if not target_col:
                    raise ValueError("Need numeric column for regression target")
                
                feat_cols = [c for c in num_cols if c != target_col][:4]
                result_data = await loop.run_in_executor(
                    None, pe.run_random_forest, df, target_col, feat_cols
                )

            elif model_type == "decision_tree":
                cat_cols = schema.get("categorical_columns", [])
                num_cols = schema.get("numeric_columns", [])
                if not target_col:
                    target_col = cat_cols[0] if cat_cols else (num_cols[0] if num_cols else None)
                if not target_col:
                    raise ValueError("Need target column")
                
                feat_cols = num_cols[:4] if num_cols else []
                result_data = await loop.run_in_executor(
                    None, pe.run_decision_tree, df, target_col, feat_cols
                )

            elif model_type == "kmeans":
                num_cols = schema.get("numeric_columns", [])
                if not num_cols:
                    raise ValueError("Need numeric columns for clustering")
                
                n_clusters = req_dict.get("n_clusters", 3)
                result_data = await loop.run_in_executor(
                    None, pe.run_kmeans, df, num_cols[:4], n_clusters
                )

            elif model_type == "isolation_forest":
                num_cols = schema.get("numeric_columns", [])
                if not num_cols:
                    raise ValueError("Need numeric columns for anomaly detection")
                
                result_data = await loop.run_in_executor(
                    None, pe.run_isolation_forest, df, num_cols[:4]
                )

            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Store result
            job.status = JobStatus.COMPLETED
            job.result_json = result_data
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("prediction_completed", job_id=job_id, model_type=model_type)

        except Exception as e:
            async with AsyncSessionLocal() as err_db:
                r = await err_db.execute(select(AnalyticsJob).where(AnalyticsJob.id == job_id))
                j = r.scalar_one_or_none()
                if j:
                    j.status = JobStatus.FAILED
                    j.error_message = str(e)
                    await err_db.commit()
            logger.exception("prediction_job_failed", job_id=job_id, error=str(e))


@router.post("/", response_model=JobStatusResponse, status_code=202)
async def run_prediction(
    req: PredictionRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify dataset ownership
    ds_result = await db.execute(
        select(Dataset).where(Dataset.id == req.dataset_id, Dataset.tenant_id == current_user.tenant_id)
    )
    dataset = ds_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    if dataset.status != DatasetStatus.READY:
        raise HTTPException(400, detail="Dataset not ready")

    job = AnalyticsJob(
        dataset_id=req.dataset_id,
        job_type="prediction",
        model_type=req.model_type,
        parameters=req.model_dump(),
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        _run_prediction_job,
        job.id,
        req.dataset_id,
        req.model_dump(),
        current_user.tenant_id,
    )
    return JobStatusResponse(job_id=job.id, status=JobStatus.PENDING)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnalyticsJob).where(AnalyticsJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, detail="Job not found")

    # Verify tenant access
    ds_result = await db.execute(
        select(Dataset).where(Dataset.id == job.dataset_id, Dataset.tenant_id == current_user.tenant_id)
    )
    if not ds_result.scalar_one_or_none():
        raise HTTPException(403, detail="Access denied")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result=job.result_json,
        error=job.error_message,
    )
