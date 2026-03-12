"""
Enterprise Analytics Platform – FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

from core.config import settings
from core.database import init_db
from core.redis_client import ping_redis
from core.middleware import setup_middleware, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routers import auth, datasets, analytics, predictions, query

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("application_starting", version=settings.APP_VERSION)
    await init_db()
    redis_ok = await ping_redis()
    if not redis_ok:
        logger.warning("redis_connection_failed")
    else:
        logger.info("redis_connected")
    yield
    # Shutdown
    logger.info("application_shutting_down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Web Data Analytics Platform with Predictive Intelligence",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Middleware
setup_middleware(app)

# Exception handlers
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Routers
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(analytics.router)
app.include_router(predictions.router)
app.include_router(query.router)


@app.get("/api/health")
async def health_check():
    redis_ok = await ping_redis()
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "redis": "connected" if redis_ok else "disconnected",
    }
