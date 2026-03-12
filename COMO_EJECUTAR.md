# Cómo Ejecutar Enterprise Analytics Platform

## 🚀 Guía Rápida de Inicio

### Requisitos Previos
- Docker y Docker Compose instalados
- Python 3.14.2 (para desarrollo sin Docker)
- Node.js 18+ (para frontend)
- Git

---

## Opción 1: Con Docker Compose (Recomendado) ⭐

### Paso 1: Iniciar Servicios
```bash
cd C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics

# Inicia PostgreSQL, Redis y backend
docker-compose up -d
```

### Paso 2: Verificar que todo esté corriendo
```bash
# Espera 30 segundos a que la BD inicie
docker-compose ps

# Deberías ver:
# postgres    running
# redis       running
```

### Paso 3: Inicializar Base de Datos
```bash
# Entrar al contenedor del backend
docker-compose exec backend alembic upgrade head

# O si no tienes migraciones:
docker-compose exec backend python -c "from core.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Paso 4: Crear Usuario de Prueba
```bash
# Conectar a PostgreSQL
docker exec -it enterprise-analytics-postgres psql -U analytics -d analyticsdb

# En psql, ejecutar:
INSERT INTO users (email, hashed_password, full_name, role, created_at) 
VALUES ('admin@example.com', '$argon2id$v=19$m=65540,t=3,p=4$...', 'Admin User', 'ADMIN', NOW());

# O usar el script Python:
docker-compose exec backend python scripts/create_default_user.py
```

### Paso 5: Acceder a la Aplicación

**Backend (API):**
- URL: `http://localhost:8000`
- Docs: `http://localhost:8000/api/docs` (Swagger UI)
- ReDoc: `http://localhost:8000/api/redoc`

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
- URL: `http://localhost:3000`

---

## Opción 2: Ejecución Manual (Desarrollo)

### Paso 1: Instalar Dependencias Backend

```bash
cd backend

# Crear virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 2: Configurar Variables de Entorno

Crear archivo `.env` en `backend/`:

```bash
# .env
DATABASE_URL=postgresql+asyncpg://analytics:analytics_pass@localhost:5432/analyticsdb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here-minimum-32-chars
DEBUG=true
ENVIRONMENT=development
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Paso 3: Iniciar Base de Datos (si no usas Docker)

```bash
# PostgreSQL debe estar ejecutándose localmente
# Mac: brew services start postgresql
# Windows: usar PostgreSQL installer o WSL

# Crear base de datos
psql -U postgres
CREATE DATABASE analyticsdb;
CREATE USER analytics WITH PASSWORD 'analytics_pass';
GRANT ALL PRIVILEGES ON DATABASE analyticsdb TO analytics;
\q
```

### Paso 4: Ejecutar Backend

```bash
cd backend

# Aplicar migraciones (si existen)
alembic upgrade head

# O crear tablas directamente
python -c "from core.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Iniciar servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Output esperado:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Paso 5: Ejecutar Frontend

```bash
cd frontend
npm install
npm run dev
```

**Output esperado:**
```
  ▲ Next.js 14.0.0
  - Local: http://localhost:3000
```

---

## 🔐 Credenciales por Defecto

### Opción A: Crear Usuario Manualmente

```bash
# 1. Ir a http://localhost:3000/register
# 2. Rellenar el formulario:
#    - Email: admin@example.com
#    - Contraseña: Admin@12345 (mín 12 caracteres, mayús, minús, número, especial)
#    - Nombre: Admin User
# 3. Dar clic en "Register"
```

### Opción B: Usuario Demo (Si está en seed)

**Email:** `demo@example.com`
**Contraseña:** `Demo@12345`
**Rol:** ANALYST

### Opción C: Usar Script de Creación

```bash
# Crear archivo scripts/create_default_user.py

from core.database import AsyncSession, get_db
from core.security import hash_password
from models.user import User
from datetime import datetime, timezone

async def create_default_user():
    db = AsyncSession()
    
    hashed = hash_password("Admin@12345")
    user = User(
        email="admin@example.com",
        hashed_password=hashed,
        full_name="Admin User",
        role="ADMIN",
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    await db.commit()
    print("✅ Usuario creado: admin@example.com / Admin@12345")

# Ejecutar
python -c "import asyncio; from scripts.create_default_user import create_default_user; asyncio.run(create_default_user())"
```

---

## 🧪 Probar la API

### Con Swagger UI (Interfaz Gráfica)
```
Ir a: http://localhost:8000/api/docs
```

### Con cURL (Terminal)

```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'

# Respuesta:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "user": {
#     "id": 1,
#     "email": "test@example.com",
#     "full_name": "Test User"
#   }
# }

# 2. Login (si ya existe)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# 3. Usar token en siguientes requests
curl -X GET http://localhost:8000/api/datasets \
  -H "Authorization: Bearer <tu_access_token>"
```

### Con Postman
1. Descargar Postman
2. Crear colección "Enterprise Analytics"
3. Configurar variable: `{{base_url}}` = `http://localhost:8000`
4. Agregar requests:
   - POST `/api/auth/register`
   - POST `/api/auth/login`
   - GET `/api/datasets`

---

## 📊 Acceder a Interfaces Web

### Dashboard Frontend
```
URL: http://localhost:3000
Ruta de login: http://localhost:3000/login
Ruta de registro: http://localhost:3000/register
```

### API Documentation (Swagger)
```
URL: http://localhost:8000/api/docs
Permite ejecutar todas las API requests directamente
```

### Database Management (pgAdmin) - Opcional
```bash
# Agregar a docker-compose.yml:
pgadmin:
  image: dpage/pgadmin4
  environment:
    PGADMIN_DEFAULT_EMAIL: admin@example.com
    PGADMIN_DEFAULT_PASSWORD: admin
  ports:
    - "5050:80"

# Acceder a http://localhost:5050
```

---

## 🐛 Solución de Problemas

### Error: "Connection refused" (Base de datos)
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Si usa Docker, reiniciar:
docker-compose down
docker-compose up -d
docker-compose logs postgres

# Si es local, iniciar PostgreSQL:
# Windows: net start PostgreSQL-15
# Mac: brew services start postgresql
```

### Error: "Redis connection failed"
```bash
# Verificar Redis
docker ps | grep redis

# Reiniciar si necesario
docker-compose restart redis

# Verificar conexión
redis-cli ping  # Debería responder PONG
```

### Error: "Module not found"
```bash
# Asegurarse que Python venv está activado
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Reinstalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -c "import fastapi; print(fastapi.__version__)"
```

### Error: "CORS - Origin not allowed"
Editar `backend/core/config.py`:
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000"
]
```

### Error: "JWT token invalid"
```bash
# Asegurarse que SECRET_KEY es consistente en .env
# Generar nuevo SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Actualizar en .env y reiniciar backend
```

---

## 📋 Flujo Completo (Paso a Paso)

### 1️⃣ Iniciar Servicios
```bash
docker-compose up -d
docker-compose ps  # Verificar que todo está running
```

### 2️⃣ Esperar que BD esté lista
```bash
# Esperar 30 segundos
docker-compose logs postgres | grep "database system is ready to accept connections"
```

### 3️⃣ Crear tablas
```bash
docker-compose exec backend python -c "from core.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 4️⃣ Crear usuario por defecto
```bash
# Via pgAdmin web (http://localhost:5050)
# O via script Python
```

### 5️⃣ Iniciar frontend
```bash
cd frontend
npm install
npm run dev
```

### 6️⃣ Acceder a aplicación
```
Frontend: http://localhost:3000
API Docs: http://localhost:8000/api/docs
```

### 7️⃣ Login
```
Email: admin@example.com
Password: Admin@12345
```

---

## 🔄 Ciclo de Desarrollo

### Backend - Desarrollo con Auto-reload
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Los cambios se reflejan automáticamente
```

### Frontend - Desarrollo con Hot Reload
```bash
cd frontend
npm run dev
# Los cambios se reflejan en tiempo real en el navegador
```

### Ejecutar Tests
```bash
cd backend

# Todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_security_v2.py -v
pytest tests/test_auth_service_v2.py -v

# Con cobertura
pytest tests/ --cov=. --cov-report=html
```

---

## 📦 Variables de Entorno (.env)

```bash
# Backend Configuration
DEBUG=true
ENVIRONMENT=development
APP_NAME=EnterpriseAnalytics
APP_VERSION=1.0.0

# Database
DATABASE_URL=postgresql+asyncpg://analytics:analytics_pass@localhost:5432/analyticsdb

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=300

# Security
SECRET_KEY=your-minimum-32-character-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# File Upload
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=.csv,.xlsx,.json

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Background Tasks
MAX_WORKERS=4
```

---

## 🎯 Resumen Rápido

| Componente | URL | Puerto | Usuario | Contraseña |
|-----------|-----|--------|---------|-----------|
| **Frontend** | http://localhost:3000 | 3000 | - | - |
| **Backend API** | http://localhost:8000 | 8000 | - | - |
| **API Docs** | http://localhost:8000/api/docs | 8000 | - | - |
| **PostgreSQL** | localhost | 5432 | analytics | analytics_pass |
| **Redis** | localhost | 6379 | - | - |
| **pgAdmin** | http://localhost:5050 | 5050 | admin@example.com | admin |

---

## ✅ Checklist de Verificación

- [ ] Docker Compose está ejecutándose
- [ ] PostgreSQL está en estado "ready"
- [ ] Redis está respondiendo a PING
- [ ] Tablas de base de datos están creadas
- [ ] Backend está en http://localhost:8000
- [ ] Frontend está en http://localhost:3000
- [ ] Puedo acceder a API Docs (Swagger)
- [ ] Puedo hacer login con credenciales
- [ ] Puedo ver el dashboard

Si todos los checks ✅, ¡la aplicación está lista! 🎉

---

## 📞 Siguientes Pasos

1. **Crear usuario:** Ir a http://localhost:3000/register
2. **Login:** Ir a http://localhost:3000/login
3. **Explorar API:** http://localhost:8000/api/docs
4. **Ver tests:** `pytest tests/ -v`
5. **Leer documentación:** `backend/QUICK_REFERENCE.md`

---

¡Listo para empezar! Si tienes problemas, revisa la sección "Solución de Problemas" arriba. 🚀
