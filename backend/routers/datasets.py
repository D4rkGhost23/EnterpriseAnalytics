import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone
import structlog

from core.database import get_db
from core.security import get_current_user
from core.redis_client import cache_get, cache_set, cache_delete
from models.dataset import Dataset, DatasetStatus
from schemas.analytics import DatasetUploadResponse, DatasetOut
from services.ingestion_service import ingest_file, IngestionError
from services.analytics_engine import run_full_analytics
from services.viz_engine import build_viz_metadata

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/datasets", tags=["Datasets"])


async def _process_dataset(dataset_id: int, file_data: bytes, filename: str, content_type: str):
    """Background task: run analytics pipeline and update dataset record."""
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            if not dataset:
                return

            dataset.status = DatasetStatus.PROCESSING
            await db.commit()

            df, audit = await ingest_file(filename, file_data, content_type)

            loop = asyncio.get_event_loop()
            analytics = await loop.run_in_executor(None, run_full_analytics, df)
            viz_meta = await loop.run_in_executor(
                None, build_viz_metadata,
                df, analytics["schema"], analytics["stats"], analytics["kpis"],
            )

            dataset.status = DatasetStatus.READY
            dataset.row_count = len(df)
            dataset.column_count = len(df.columns)
            dataset.file_hash = audit["file_hash"]
            dataset.schema_json = analytics["schema"]
            dataset.stats_json = analytics["stats"]
            dataset.insights_json = analytics["insights"]
            dataset.viz_metadata_json = viz_meta
            # Store data as JSON for predictions
            dataset.data_json = df.to_dict(orient="records")
            dataset.processed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("dataset_processed", dataset_id=dataset_id)

        except IngestionError as e:
            async with AsyncSessionLocal() as err_db:
                r = await err_db.execute(select(Dataset).where(Dataset.id == dataset_id))
                ds = r.scalar_one_or_none()
                if ds:
                    ds.status = DatasetStatus.ERROR
                    ds.error_message = str(e)
                    await err_db.commit()
        except Exception as e:
            async with AsyncSessionLocal() as err_db:
                r = await err_db.execute(select(Dataset).where(Dataset.id == dataset_id))
                ds = r.scalar_one_or_none()
                if ds:
                    ds.status = DatasetStatus.ERROR
                    ds.error_message = f"Processing error: {str(e)}"
                    await err_db.commit()
            logger.exception("dataset_processing_error", dataset_id=dataset_id, error=str(e))


@router.post("/upload", response_model=DatasetUploadResponse, status_code=201)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from core.config import settings
    file_data = await file.read()
    if len(file_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, detail="File too large")

    dataset = Dataset(
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
        name=file.filename or "Unnamed Dataset",
        original_filename=file.filename or "upload",
        file_type=file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "unknown",
        file_size_bytes=len(file_data),
        status=DatasetStatus.UPLOADING,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    background_tasks.add_task(
        _process_dataset,
        dataset.id,
        file_data,
        file.filename or "upload",
        file.content_type or "application/octet-stream",
    )
    await cache_delete(f"datasets:tenant:{current_user.tenant_id}")
    return DatasetUploadResponse.model_validate(dataset)


@router.get("/", response_model=List[DatasetOut])
async def list_datasets(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset)
        .where(Dataset.tenant_id == current_user.tenant_id)
        .order_by(Dataset.created_at.desc())
    )
    datasets = result.scalars().all()
    return [DatasetOut.model_validate(d) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.tenant_id == current_user.tenant_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    return DatasetOut.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.tenant_id == current_user.tenant_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    await db.delete(dataset)
    await cache_delete(f"datasets:tenant:{current_user.tenant_id}")
