from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Dict

from core.database import get_db
from core.security import get_current_user
from core.redis_client import cache_get, cache_set
from models.dataset import Dataset, DatasetStatus
from schemas.analytics import AnalyticsRequest, AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.post("/", response_model=AnalyticsResponse)
async def get_analytics(
    req: AnalyticsRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pre-computed analytics for a dataset (cached)."""
    cache_key = f"analytics:dataset:{req.dataset_id}:tenant:{current_user.tenant_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

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
        raise HTTPException(400, detail=f"Dataset not ready. Status: {dataset.status}")

    response = AnalyticsResponse(
        dataset_id=dataset.id,
        schema=dataset.schema_json or {},
        stats=dataset.stats_json or {},
        kpis=dataset.schema_json.get("kpis", {}) if dataset.schema_json else {},
        insights=dataset.insights_json or [],
        viz_metadata=dataset.viz_metadata_json or [],
    )
    await cache_set(cache_key, response.model_dump(), ttl=300)
    return response


@router.get("/{dataset_id}/kpis")
async def get_kpis(
    dataset_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.tenant_id == current_user.tenant_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    if dataset.status != DatasetStatus.READY:
        raise HTTPException(400, detail="Dataset not ready")
    return dataset.schema_json.get("kpis", {}) if dataset.schema_json else {}


@router.get("/{dataset_id}/insights")
async def get_insights(
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
    return {"insights": dataset.insights_json or []}


@router.get("/{dataset_id}/visualizations")
async def get_visualizations(
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
    return {"visualizations": dataset.viz_metadata_json or []}
