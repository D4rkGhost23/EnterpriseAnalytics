# 🧪 Guía de Pruebas - Enterprise Analytics Platform

## ✅ Resumen de lo Implementado

Se han creado **4 suites de pruebas completas** con un total de **100+ casos de prueba**:

### 1️⃣ Pruebas Unitarias de Autenticación (`test_auth_service.py`)
- ✓ Hash y verificación de contraseñas (bcrypt)
- ✓ Creación y validación de tokens JWT
- ✓ Registro de usuarios
- ✓ Login y manejo de credenciales inválidas
- ✓ Refresco de tokens
- ✓ Control de acceso basado en roles (RBAC)
- **13 tests**

### 2️⃣ Pruebas de Validación de Archivos (`test_ingestion_service.py`)
- ✓ Validación de extensiones permitidas (CSV, XLSX, JSON)
- ✓ Detección de magic bytes
- ✓ Escaneo de contenido malicioso (code injection, XSS, payloads)
- ✓ Verificación de encoding UTF-8
- ✓ Checksums SHA256
- ✓ Tests de integración multi-capa
- **30+ tests**

### 3️⃣ Pruebas de Machine Learning (`test_prediction_engine.py`)
- ✓ Regresión Lineal (pronósticos de ventas)
- ✓ Random Forest (clasificación)
- ✓ Árboles de Decisión (extracción de reglas)
- ✓ K-Means (segmentación de clientes)
- ✓ Isolation Forest (detección de anomalías)
- ✓ Manejo de datos nulos e imbalanceados
- **25+ tests**

### 4️⃣ Smoke Tests / Flujos Completos (`test_smoke_integration.py`)
- ✓ Registro → Login → Refresh tokens
- ✓ Upload de archivos → Análisis → Predicción
- ✓ Ejecución de queries sandboxed
- ✓ Validación de acceso sin autorización
- ✓ Rate limiting
- ✓ Rechazo de archivos maliciosos
- **13 smoke tests**

### 5️⃣ Pruebas de Seguridad (`test_security.py`)
- ✓ Whitelist de extensiones
- ✓ Inyección de código
- ✓ SQL injection protection
- ✓ RBAC enforcement
- ✓ Multi-tenant isolation
- ✓ Rate limiting / DDoS protection
- ✓ Validación de tokens JWT
- ✓ Límites de tamaño de archivo
- **20+ tests**

---

## 🚀 Cómo Ejecutar las Pruebas

### Prerequisitos
```bash
# Windows: Activar ambiente virtual
.\venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

### Instalar dependencias de testing (si no están ya instaladas)
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### Ejecutar todas las pruebas
```bash
# Ejecutar con reporte de cobertura
pytest backend/tests/ -v --cov=backend --cov-report=html

# Solo mostrar resumen
pytest backend/tests/ -v
```

### Ejecutar pruebas específicas
```bash
# Solo pruebas de autenticación
pytest backend/tests/test_auth_service.py -v

# Solo pruebas de validación de archivos
pytest backend/tests/test_ingestion_service.py -v

# Solo pruebas de ML
pytest backend/tests/test_prediction_engine.py -v

# Solo smoke tests
pytest backend/tests/test_smoke_integration.py -v

# Solo pruebas de seguridad
pytest backend/tests/test_security.py -v
```

### Ejecutar con opciones avanzadas
```bash
# Modo verbose con output detallado
pytest backend/tests/ -vv -s

# Parar en primer error
pytest backend/tests/ -x

# Mostrar los 10 tests más lentos
pytest backend/tests/ --durations=10

# Ejecutar solo tests que contengan "auth"
pytest backend/tests/ -k "auth" -v

# Generar reporte de cobertura HTML
pytest backend/tests/ --cov=backend --cov-report=html
# Abre htmlcov/index.html en el navegador
```

---

## 📊 Base de Datos - Situación Actual vs Mejoras

### 🔵 Base de Datos Actual (PostgreSQL)
**¿Ya está implementada?** ✅ **SÍ**

Tu proyecto ya utiliza **PostgreSQL** como base de datos relacional:

```python
# backend/core/database.py
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/analytics_db"
```

**Modelos actualmente almacenados:**
- 👤 `User` - Usuarios con roles (OWNER, ADMIN, ANALYST, VIEWER)
- 🏢 `Tenant` - Empresas (multi-tenant)
- 📊 `Dataset` - Archivos subidos
- 📈 `Insight` - Resultados de análisis
- 🤖 `Prediction` - Resultados de modelos ML

**Características de seguridad:**
- ✓ SQLAlchemy ORM (previene SQL injection)
- ✓ Async queries (uvloop)
- ✓ Transacciones ACID
- ✓ Foreign keys para integridad referencial

---

### 🟢 Mejoras Sugeridas para la Base de Datos

#### 1. **Auditoría y Logging (CRITICAL)**
**¿Es necesario?** ✅ **SÍ - URGENTE**

Implementar tabla de auditoría para cumplimiento empresarial:

```python
# backend/models/audit.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    action = Column(String)  # "upload", "delete", "download"
    resource_type = Column(String)  # "dataset", "prediction"
    resource_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    changes = Column(JSON)  # Track what changed
```

**Por qué:** Requisito legal para SaaS (GDPR, SOC 2). Debes saber quién accedió qué y cuándo.

#### 2. **Soft Deletes (IMPORTANT)**
**¿Es necesario?** ✅ **SÍ**

Nunca borrar datos permanentemente en prod:

```python
# En cada modelo (User, Dataset, etc.)
deleted_at = Column(DateTime, nullable=True)

# En consultas
@classmethod
async def get_active(cls, session, id):
    return await session.execute(
        select(cls).where(cls.id == id, cls.deleted_at == None)
    )
```

#### 3. **Índices de Base de Datos (PERFORMANCE)**
**¿Es necesario?** ✅ **SÍ**

Agregar índices para queries frecuentes:

```python
# backend/models/dataset.py
class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), index=True)  # ← Índice
    user_id = Column(Integer, ForeignKey("user.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, index=True)  # "processing", "ready", "error"
    
    __table_args__ = (
        Index("idx_tenant_created", "tenant_id", "created_at"),  # Índice compuesto
    )
```

#### 4. **Versionado de Datos (ANALYTICS)**
**¿Es necesario?** ⚠️ **OPCIONAL pero RECOMENDADO**

Guardar histórico de cambios en datasets:

```python
class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    version_number = Column(Integer)
    file_hash = Column(String)  # SHA256
    row_count = Column(Integer)
    column_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 5. **Quotas y Límites por Tenant (MULTI-TENANT)**
**¿Es necesario?** ✅ **SÍ**

Implementar límites SaaS (modelo de negocio):

```python
class TenantQuota(Base):
    __tablename__ = "tenant_quotas"
    
    tenant_id = Column(Integer, ForeignKey("tenant.id"), primary_key=True)
    max_datasets = Column(Integer, default=100)
    max_storage_gb = Column(Integer, default=10)
    max_predictions_per_month = Column(Integer, default=1000)
    current_storage_gb = Column(Float, default=0)
    current_predictions_month = Column(Integer, default=0)
```

#### 6. **Session Management (SECURITY)**
**¿Es necesario?** ✅ **SÍ**

Rastrear sesiones activas del usuario:

```python
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True)  # session_id
    user_id = Column(Integer, ForeignKey("user.id"))
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
```

---

## 🚨 Mejoras Generales al Sistema (Más allá de la BD)

### 🔴 **CRÍTICAS - Implementar Inmediatamente**

#### 1. **Validación de Datos en Entrada (Input Validation)**
```python
# backend/schemas/auth.py - MEJORADO
from pydantic import BaseModel, EmailStr, field_validator

class UserRegister(BaseModel):
    email: EmailStr  # Validado automáticamente
    password: str
    full_name: str
    tenant_name: str
    
    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 12:
            raise ValueError("Contraseña debe tener mín 12 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("Debe contener mayúsculas")
        if not any(c.isdigit() for c in v):
            raise ValueError("Debe contener números")
        if not any(c in "!@#$%^&*" for c in v):
            raise ValueError("Debe contener caracteres especiales")
        return v
```

#### 2. **Logging Estructurado Mejorado**
```python
# backend/core/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("user_login", user_id=123, ip="192.168.1.1", success=True)
# Salida: {"timestamp": "2026-02-25T...", "user_id": 123, "ip": "192.168.1.1", ...}
```

#### 3. **Error Handling Centralizado**
```python
# backend/core/exceptions.py
from fastapi import HTTPException, status

class DatasetNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

class InsufficientQuotaError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tenant quota exceeded"
        )
```

#### 4. **Caché Inteligente con Redis (PERFORMANCE)**
```python
# backend/services/cache_service.py
from core.redis_client import redis_client

async def get_insights_cached(dataset_id: int, tenant_id: int):
    cache_key = f"insights:{tenant_id}:{dataset_id}"
    
    # Intentar desde caché
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Calcular si no existe
    insights = await generate_insights(dataset_id)
    
    # Guardar en caché por 1 hora
    await redis_client.setex(cache_key, 3600, json.dumps(insights))
    return insights
```

#### 5. **Webhook System para Notificaciones**
```python
# backend/models/webhook.py
class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    url = Column(String)  # https://customer.com/analytics-hook
    events = Column(JSON)  # ["dataset_uploaded", "prediction_complete"]
    is_active = Column(Boolean, default=True)

# Uso:
await notify_webhooks(
    tenant_id=1,
    event="prediction_complete",
    data={"prediction_id": 123, "accuracy": 0.92}
)
```

### 🟡 **IMPORTANTES - Próximos 2-3 Sprints**

#### 6. **Exportación de Datos (CSV, Excel, PDF)**
```python
# backend/services/export_service.py
async def export_insights_to_pdf(dataset_id: int, format: str = "pdf"):
    insights = await get_insights(dataset_id)
    
    if format == "pdf":
        from reportlab.lib.pagesizes import letter
        # Generar PDF con charts
        return pdf_bytes
    elif format == "xlsx":
        # Generar Excel con múltiples hojas
        return excel_bytes
```

#### 7. **Integración con Data Warehouses**
```python
# Permitir conexión a BigQuery, Snowflake, Redshift
async def sync_with_warehouse(tenant_id: int, config: dict):
    # config = {
    #     "type": "bigquery",
    #     "project_id": "...",
    #     "credentials": {...}
    # }
    pass
```

#### 8. **Versionado de Modelos ML (Model Registry)**
```python
class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    model_type = Column(String)  # "linear_regression", "random_forest"
    version = Column(Integer)
    accuracy = Column(Float)
    trained_at = Column(DateTime)
    model_data = Column(LargeBinary)  # Pickle/joblib del modelo
    is_production = Column(Boolean, default=False)
```

#### 9. **A/B Testing Framework**
```python
class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    variant_a_name = Column(String)
    variant_b_name = Column(String)
    users = Column(JSON)  # {"variant_a": [user_ids], "variant_b": [user_ids]}
    metrics = Column(JSON)  # Resultados estadísticos
```

#### 10. **Alertas Inteligentes**
```python
class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    name = Column(String)  # "Sales drop alert"
    condition = Column(String)  # "sales < avg * 0.8"
    channels = Column(JSON)  # ["email", "slack", "sms"]
    is_active = Column(Boolean, default=True)
```

### 🔵 **NICE-TO-HAVE - Futura Evolución**

- 🔄 **Replicación y Backup automático** (PostgreSQL WAL)
- 📊 **Data Lineage tracking** (quién modificó qué, cuándo)
- 🤖 **Auto-scaling** (AWS RDS Aurora)
- 🔐 **Encryption at rest** (pgcrypto)
- 📡 **GraphQL API** (además de REST)
- 🧬 **Feature Store** para ML (similar a Feast)

---

## 📈 Plan de Implementación Recomendado

### **Semana 1:** Mejoras Críticas
```
✅ Pruebas (ya están hechas)
✅ Validación de entrada mejorada
✅ Logging estructurado
✅ Error handling centralizado
```

### **Semana 2:** Seguridad y Auditoría
```
✅ Auditoría de logs
✅ Soft deletes
✅ Session management
✅ Webhook system
```

### **Semana 3:** Performance y Escalabilidad
```
✅ Índices de BD
✅ Caché inteligente
✅ Quotas por tenant
✅ Versionado de datos
```

### **Semana 4:** Features Avanzadas
```
✅ Exportación (PDF, Excel)
✅ Model registry
✅ Alertas inteligentes
✅ Integración webhooks
```

---

## ✅ Checklist para Deploy a Producción

- [ ] Todas las pruebas pasando (100% cobertura de módulos críticos)
- [ ] Auditoría de seguridad completada
- [ ] Rate limiting configurado y testeado
- [ ] Validación de entrada en todos los endpoints
- [ ] Logging centralizado activo
- [ ] Backups de BD automáticos configurados
- [ ] SSL/TLS en todas las conexiones
- [ ] CORS correctamente configurado
- [ ] Variables de entorno (.env) no versionadas
- [ ] Secrets manager configurado (AWS Secrets, HashiCorp Vault)
- [ ] Monitoreo y alertas en place (Sentry, DataDog, etc.)
- [ ] Plan de disaster recovery documentado

---

## 🎯 Conclusión

Tu plataforma tiene una **base sólida**. Las pruebas que acabo de crear cubrirán los casos críticos. Las mejoras sugeridas la llevarán a **nivel Enterprise**:

1. **Ahora:** Ejecuta las pruebas, identifica fallos
2. **Semana 1:** Implementa validaciones y logging
3. **Semana 2-3:** Agrega auditoría y mejoras de BD
4. **Semana 4+:** Features avanzadas y optimización

¿Necesitas que profundice en alguna de estas mejoras específicas?
