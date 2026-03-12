# Database & System Improvements Guide

## 1. DATABASE ENHANCEMENTS

### 1.1 Audit Logging (GDPR Compliance)

**Purpose:** Track all changes for compliance, security investigations, and data recovery.

**Implementation:**

```python
# models/audit.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from datetime import datetime, timezone
import enum

class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(50))  # "Dataset", "User", "Model"
    resource_id = Column(Integer)
    old_values = Column(JSON, nullable=True)  # Before change
    new_values = Column(JSON, nullable=True)  # After change
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_action_timestamp', 'action', 'timestamp'),
        Index('idx_resource', 'resource_type', 'resource_id'),
    )

# Usage in service
async def log_action(
    db: AsyncSession,
    user_id: int,
    action: AuditAction,
    resource_type: str,
    resource_id: int,
    old_values: dict = None,
    new_values: dict = None,
    ip_address: str = None,
    request: Request = None
):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address or request.client.host,
        user_agent=request.headers.get("User-Agent") if request else None
    )
    db.add(audit)
    await db.commit()
```

**Benefits:**
- Compliance with GDPR, HIPAA, SOC2
- Security incident investigation
- User activity tracking
- Change history for datasets
- Revenue attribution (who modified what)

---

### 1.2 Soft Deletes (Data Recovery)

**Purpose:** Never permanently delete data; allow recovery and maintain referential integrity.

**Implementation:**

```python
# core/database.py - Add to Base class
from sqlalchemy import DateTime
from datetime import datetime, timezone

class TimestampMixin:
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete marker

# Update all models
class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # ... other columns

# Create deletion methods
async def soft_delete(db: AsyncSession, model_instance):
    model_instance.deleted_at = datetime.now(timezone.utc)
    db.add(model_instance)
    await db.commit()

async def restore(db: AsyncSession, model_instance):
    model_instance.deleted_at = None
    db.add(model_instance)
    await db.commit()

# Query filters
async def get_active_datasets(db: AsyncSession):
    stmt = select(Dataset).where(Dataset.deleted_at.is_(None))
    return await db.scalars(stmt)

async def get_deleted_datasets(db: AsyncSession):
    stmt = select(Dataset).where(Dataset.deleted_at.isnot(None))
    return await db.scalars(stmt)
```

**Benefits:**
- Accidental deletion recovery (7-day recovery window)
- GDPR compliance (keep deletion records)
- Maintain foreign key relationships
- Track deletion patterns
- Rollback capability

---

### 1.3 Version Control (Dataset Change History)

**Purpose:** Track dataset modifications, enable rollback, support compliance.

**Implementation:**

```python
# models/dataset_version.py
class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    version_number = Column(Integer)  # 1, 2, 3...
    rows_count = Column(Integer)
    columns_info = Column(JSON)  # {col_name: {type, nulls, cardinality}}
    file_hash = Column(String(64))  # SHA256
    file_size = Column(Integer)
    file_url = Column(String(500))  # S3 location
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"))
    change_description = Column(String(500))  # "Updated Q3 sales data"
    metadata = Column(JSON)  # Data quality metrics, schema changes
    
    __table_args__ = (
        Index('idx_dataset_version', 'dataset_id', 'version_number', unique=True),
    )

# Usage
async def create_dataset_version(
    db: AsyncSession,
    dataset_id: int,
    file_path: str,
    file_hash: str,
    change_description: str,
    current_user: User
):
    # Get next version number
    last_version = await db.execute(
        select(func.max(DatasetVersion.version_number))
        .where(DatasetVersion.dataset_id == dataset_id)
    )
    next_version = (last_version.scalar() or 0) + 1
    
    version = DatasetVersion(
        dataset_id=dataset_id,
        version_number=next_version,
        file_hash=file_hash,
        file_url=f"s3://bucket/datasets/{dataset_id}/v{next_version}/data.csv",
        created_by=current_user.id,
        change_description=change_description,
        metadata={"status": "active"}
    )
    db.add(version)
    await db.commit()
```

**Benefits:**
- Complete change history
- Rollback to previous versions
- Compliance audit trail
- Data lineage tracking
- Performance metrics over time

---

### 1.4 Multi-Tenant Quotas

**Purpose:** Enforce SaaS limits per tenant (users, datasets, storage, API calls).

**Implementation:**

```python
# models/tenant.py
class TenantQuota(Base):
    __tablename__ = "tenant_quotas"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True)
    max_users = Column(Integer, default=10)
    max_datasets = Column(Integer, default=50)
    max_storage_gb = Column(Integer, default=100)
    max_api_calls_per_month = Column(Integer, default=100000)
    max_concurrent_jobs = Column(Integer, default=5)
    features = Column(JSON)  # {"advanced_ml": true, "webhooks": true}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

class TenantUsage(Base):
    __tablename__ = "tenant_usage"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    current_users = Column(Integer, default=0)
    current_datasets = Column(Integer, default=0)
    current_storage_gb = Column(Float, default=0.0)
    api_calls_this_month = Column(Integer, default=0)
    concurrent_jobs = Column(Integer, default=0)
    last_reset_date = Column(DateTime)
    
    __table_args__ = (
        Index('idx_tenant_usage', 'tenant_id', unique=True),
    )

# Usage - Middleware
@app.middleware("http")
async def check_quota(request: Request, call_next):
    if request.url.path.startswith("/api"):
        tenant_id = request.headers.get("X-Tenant-ID")
        usage = await db.execute(
            select(TenantUsage).where(TenantUsage.tenant_id == tenant_id)
        )
        usage = usage.scalar()
        
        if usage.api_calls_this_month >= quota.max_api_calls_per_month:
            return JSONResponse(
                status_code=429,
                content={"detail": "Monthly API quota exceeded"}
            )
    
    return await call_next(request)
```

**Benefits:**
- SaaS revenue enforcement
- Resource allocation fairness
- Cost predictability
- Feature gating
- Load balancing

---

### 1.5 Session Management

**Purpose:** Track user sessions, enable secure logout, prevent token reuse.

**Implementation:**

```python
# models/user_session.py
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token_jti = Column(String(500), unique=True)  # JWT ID
    refresh_token_jti = Column(String(500), unique=True)
    device_info = Column(JSON)  # {browser, os, device_type}
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    login_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)  # When tokens expire
    is_active = Column(Boolean, default=True)
    logout_timestamp = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_user_active', 'user_id', 'is_active'),
        Index('idx_token_jti', 'access_token_jti'),
    )

# Usage in JWT
async def create_session(
    db: AsyncSession,
    user_id: int,
    request: Request,
    access_token: str,
    refresh_token: str
):
    # Decode tokens to get JTI claim
    from jose import jwt
    access_jti = jwt.decode(access_token, settings.SECRET_KEY).get("jti")
    refresh_jti = jwt.decode(refresh_token, settings.SECRET_KEY).get("jti")
    
    session = UserSession(
        user_id=user_id,
        access_token_jti=access_jti,
        refresh_token_jti=refresh_jti,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        device_info={"browser": "Chrome", "os": "Windows"}
    )
    db.add(session)
    await db.commit()
    return session

async def logout(db: AsyncSession, user_id: int, token_jti: str):
    stmt = update(UserSession).where(
        (UserSession.user_id == user_id) & 
        (UserSession.access_token_jti == token_jti)
    ).values(is_active=False, logout_timestamp=datetime.now(timezone.utc))
    await db.execute(stmt)
    await db.commit()
```

**Benefits:**
- Session timeout enforcement
- Concurrent login limits
- Device tracking
- Security breach isolation (logout all devices)
- Activity monitoring

---

## 2. SYSTEM IMPROVEMENTS

### 2.1 Centralized Error Handling

**Purpose:** Consistent error responses, better debugging, user-friendly messages.

**Implementation:**

```python
# core/exceptions.py
from fastapi import HTTPException, status
from typing import Any, Optional

class APIException(Exception):
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "UNKNOWN_ERROR",
        context: dict = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.context = context or {}

class ValidationError(APIException):
    def __init__(self, detail: str, context: dict = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            context=context
        )

class UnauthorizedException(APIException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED"
        )

# main.py - Exception handler
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": exc.context if settings.DEBUG else {}
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )

# Usage
if not user:
    raise UnauthorizedException("Invalid email or password")

if invalid_data:
    raise ValidationError(
        detail="Dataset must have at least 10 rows",
        context={"provided": len(data), "minimum": 10}
    )
```

---

### 2.2 Structured JSON Logging

**Purpose:** Machine-readable logs for debugging, monitoring, compliance.

**Implementation:**

```python
# core/logging.py
import structlog
import json
from datetime import datetime, timezone

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage in services
logger = structlog.get_logger()

async def process_dataset(dataset_id: int, user_id: int):
    logger.info(
        "dataset.processing.started",
        dataset_id=dataset_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    try:
        result = await ml_engine.train(dataset_id)
        logger.info(
            "dataset.processing.completed",
            dataset_id=dataset_id,
            accuracy=result.accuracy,
            duration_seconds=result.duration
        )
    except Exception as e:
        logger.error(
            "dataset.processing.failed",
            dataset_id=dataset_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise

# Log output (JSON format)
# {"event": "dataset.processing.started", "dataset_id": 1, "user_id": 5, "timestamp": "2024-01-15T10:30:00Z"}
# {"event": "dataset.processing.completed", "dataset_id": 1, "accuracy": 0.92, "duration_seconds": 45}
```

---

### 2.3 Request/Response Tracing

**Purpose:** Track requests across services, debug distributed systems, performance monitoring.

**Implementation:**

```python
# core/tracing.py
import uuid
from fastapi import Request, Response
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar("request_id", default="")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_context.set(request_id)
    
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    logger.info(
        "http.request.completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_seconds=duration,
        user_agent=request.headers.get("User-Agent")
    )
    
    response.headers["X-Request-ID"] = request_id
    return response

# Get current request_id in any service
def get_current_request_id() -> str:
    return request_id_context.get()

# Usage
logger.info(
    "database.query.executed",
    request_id=get_current_request_id(),
    query="SELECT * FROM datasets",
    duration_ms=45
)
```

---

### 2.4 Performance Monitoring

**Purpose:** Identify bottlenecks, track SLAs, optimize resources.

**Implementation:**

```python
# core/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter(
    'requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'request_duration_seconds',
    'Request duration',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

db_query_duration = Histogram(
    'db_query_duration_ms',
    'Database query duration',
    ['operation'],  # SELECT, INSERT, UPDATE
    buckets=(10, 50, 100, 500, 1000)
)

active_connections = Gauge(
    'active_connections',
    'Active database connections'
)

ml_model_accuracy = Gauge(
    'ml_model_accuracy',
    'Latest model accuracy',
    ['model_type']  # linear_regression, random_forest
)

# Usage
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(endpoint=request.url.path).observe(duration)
    return response

# Expose metrics endpoint
from prometheus_client import generate_latest, REGISTRY
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )
```

---

### 2.5 Webhook System

**Purpose:** Real-time notifications for important events.

**Implementation:**

```python
# models/webhook.py
class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    url = Column(String(500), nullable=False)
    events = Column(JSON)  # ["dataset.created", "model.completed"]
    is_active = Column(Boolean, default=True)
    secret_key = Column(String(255))  # For HMAC signing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"))
    event_type = Column(String(100))
    payload = Column(JSON)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_attempt = Column(DateTime, nullable=True)

# Usage
async def trigger_webhook(db: AsyncSession, event_type: str, payload: dict):
    webhooks = await db.execute(
        select(Webhook).where(
            (Webhook.events.contains(event_type)) &
            (Webhook.is_active == True)
        )
    )
    
    for webhook in webhooks.scalars():
        # Sign payload with HMAC
        import hmac
        import hashlib
        signature = hmac.new(
            webhook.secret_key.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Queue async delivery
        background_tasks.add_task(
            send_webhook,
            webhook.url,
            payload,
            signature
        )
```

---

## 3. IMPLEMENTATION PRIORITY

### Phase 1 (Critical) - Week 1-2
- [ ] Audit logging
- [ ] Soft deletes
- [ ] Centralized error handling

### Phase 2 (Important) - Week 3-4
- [ ] Session management
- [ ] Version control
- [ ] Structured logging

### Phase 3 (Enhancement) - Week 5-6
- [ ] Multi-tenant quotas
- [ ] Request tracing
- [ ] Performance monitoring

### Phase 4 (Optional) - Week 7+
- [ ] Webhook system
- [ ] Advanced analytics
- [ ] ML model registry

---

## 4. TESTING IMPROVEMENTS

```python
# tests/test_audit.py
@pytest.mark.asyncio
async def test_audit_log_creation(test_db):
    await log_action(
        db=test_db,
        user_id=1,
        action=AuditAction.UPDATE,
        resource_type="Dataset",
        resource_id=5
    )
    
    audit = await test_db.execute(select(AuditLog))
    assert audit.scalar().action == AuditAction.UPDATE

# tests/test_soft_delete.py
@pytest.mark.asyncio
async def test_soft_delete(test_db):
    dataset = Dataset(name="Test")
    test_db.add(dataset)
    await test_db.commit()
    
    await soft_delete(test_db, dataset)
    
    active = await get_active_datasets(test_db)
    assert len(active) == 0
    
    deleted = await get_deleted_datasets(test_db)
    assert len(deleted) == 1
```

---

## Conclusion

These improvements will:
✅ Ensure compliance (GDPR, HIPAA, SOC2)
✅ Improve security and auditability
✅ Enable better debugging and monitoring
✅ Support multi-tenant SaaS requirements
✅ Provide data recovery capabilities
✅ Track performance and costs

Recommended: Start with Phase 1 improvements (audit logging, soft deletes, error handling) as they have the highest compliance and reliability impact.
