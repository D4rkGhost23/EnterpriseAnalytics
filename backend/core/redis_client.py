import redis.asyncio as aioredis
from core.config import settings
import structlog
import json
from typing import Optional, Any

logger = structlog.get_logger()
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
    return None


async def cache_set(key: str, value: Any, ttl: int = None) -> None:
    try:
        redis = await get_redis()
        ttl = ttl or settings.CACHE_TTL_SECONDS
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception as e:
        logger.warning("cache_delete_failed", key=key, error=str(e))


async def ping_redis() -> bool:
    try:
        redis = await get_redis()
        return await redis.ping()
    except Exception:
        return False
