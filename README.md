### Opción A: Con Docker
```bash
# 1. Iniciar servicios
cd C:.....\EnterpriseAnalytics
docker-compose up -d

# 2. Esperar 30 segundos a que la BD inicie
# (Verifica que postgres esté listo)

# 3. Crear usuarios por defecto
docker-compose exec backend python scripts/create_default_users.py

# 4. Abrir en navegador
# Frontend: http://localhost:3000
# Backend API Docs: http://localhost:8000/api/docs
```

### Opción B: Sin Docker 

```bash
# TERMINAL 1: Backend
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# TERMINAL 2: Frontend
cd frontend
npm install
npm run dev

# Luego crear usuario (en navegador ir a /register)
```

---

## Credenciales por Defecto

```
 ADMIN
   Email:      admin@example.com
   Contraseña: Admin@12345

ANALYST
   Email:      analyst@example.com
   Contraseña: Analyst@12345

VIEWER
   Email:      viewer@example.com
   Contraseña: Viewer@12345

DEMO
   Email:      demo@example.com
   Contraseña: Demo@12345
```

---

##  Acceder a la Aplicación

| Componente | URL | Descripción |
|-----------|-----|------------|
| **Frontend** | http://localhost:3000 | Aplicación web |
| **Login** | http://localhost:3000/login | Página de login |
| **Dashboard** | http://localhost:3000/dashboard | Área principal |
| **API Docs (Swagger)** | http://localhost:8000/api/docs | Probar API interactivamente |
| **API ReDoc** | http://localhost:8000/api/redoc | Documentación de API |
| **Database** | localhost:5432 | PostgreSQL |
| **Cache** | localhost:6379 | Redis |

---

## Documentación Disponible

| Archivo | Contenido |
|---------|----------|
| **CHEAT_SHEET.md** | ← Estás aquí (resumen rápido) |
| **COMO_EJECUTAR.md** | Guía completa y detallada |
| **backend/QUICK_REFERENCE.md** | Resumen ejecutivo de mejoras |
| **backend/TEST_SUMMARY.md** | 83 tests documentados |
| **backend/DATABASE_IMPROVEMENTS.md** | Mejoras de base de datos |
| **backend/SYSTEM_IMPROVEMENTS.md** | Mejoras de arquitectura |
| **frontend/README_EJECUCION.md** | Instrucciones del frontend |

---

## Verificar que Todo Funciona

```bash
# Check 1: ¿Servicios están corriendo?
docker-compose ps
# Deberías ver: postgres (running), redis (running)

# Check 2: ¿Frontend carga?
curl http://localhost:3000
# Debe retornar HTML

# Check 3: ¿API funciona?
curl http://localhost:8000/api/docs
# Debe retornar Swagger UI

# Check 4: ¿BD responde?
docker-compose exec postgres pg_isready -U analytics
# Debe decir: "accepting connections"

# Check 5: ¿Redis funciona?
docker-compose exec redis redis-cli ping
# Debe responder: PONG
```

---

##  Primeros Pasos Después de Iniciar

### 1. Login
```
1. Ir a http://localhost:3000
2. Click en "Login"
3. Email: admin@example.com
4. Contraseña: Admin@12345
5. Click en "Sign In"
```

### 2. Explorar Dashboard
```
- Overview: Ver resumen general
- Datasets: Subir archivos CSV, XLSX, JSON
- Query: Ejecutar queries SQL
- Predictions: Usar modelos ML
- Visualizations: Ver gráficos
```

### 3. Probar API
```
1. Ir a http://localhost:8000/api/docs
2. Click en "Authorize" (arriba derecha)
3. En el POST /api/auth/login:
   - Email: admin@example.com
   - Contraseña: Admin@12345
4. Copiar el "access_token"
5. Pegar en "Authorize": Bearer <token>
6. Ahora probar otros endpoints
```

---

##  Problemas Comunes y Soluciones

###  "Connection refused"
```bash
# La BD aún está iniciando
# Solución: Esperar 30 segundos más
docker-compose logs postgres | grep ready
```

### "Docker not install"
```bash
# Descargar de: https://www.docker.com/products/docker-desktop
# Instalar y reiniciar tu computadora
```

### "Port 3000/8000 already in use"
```bash
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -i :3000
kill -9 <PID>
```

### "Login falla - Invalid credentials"
```bash
# Asegúrate de estar usando:
# Email:      admin@example.com (exactamente así)
# Contraseña: Admin@12345 (con mayúscula y número)
```

---

## Ejecutar Tests

```bash
# Todos los tests (83 tests)
cd backend
pytest tests/ -v

# Tests específicos
pytest tests/test_security_v2.py -v          # 18 tests de seguridad
pytest tests/test_auth_service_v2.py -v      # 20 tests de auth
pytest tests/test_ingestion_service_v2.py -v # 33 tests de archivos
pytest tests/test_prediction_engine_v2.py -v # 12 tests de ML

# Con cobertura
pytest tests/ --cov=. --cov-report=html
# Abrir: htmlcov/index.html
```

---

## Estructura Clave

```
EnterpriseAnalytics/
├── docker-compose.yml          ← Inicia BD, Redis, etc
├── CHEAT_SHEET.md             ← Este archivo
├── COMO_EJECUTAR.md           ← Guía detallada
│
├── backend/
│   ├── main.py                ← Punto de entrada FastAPI
│   ├── core/
│   │   ├── config.py          ← Configuración
│   │   ├── database.py        ← Conexión BD
│   │   └── security.py        ← Auth & JWT
│   ├── models/                ← Esquemas BD
│   ├── routers/               ← Endpoints API
│   ├── services/              ← Lógica de negocio
│   ├── tests/                 ← 83 tests ✅
│   └── scripts/
│       └── create_default_users.py
│
└── frontend/
    ├── package.json
    ├── src/app/               ← Páginas
    ├── src/components/        ← Componentes React
    └── src/lib/api.ts         ← Cliente HTTP
```

---

## Ciclo de Desarrollo (Con Auto-reload)

```bash
# TERMINAL 1: Backend (reloads automáticamente)
cd backend
uvicorn main:app --reload

# TERMINAL 2: Frontend (hot reload automático)
cd frontend
npm run dev

# Cambios se reflejan en tiempo real al guardar archivos!
```

---

## API Endpoints Principales

```
AUTH
  POST   /api/auth/register              Crear usuario
  POST   /api/auth/login                 Login
  POST   /api/auth/refresh               Renovar token

DATASETS
  GET    /api/datasets                   Listar mis datasets
  POST   /api/datasets                   Subir dataset
  GET    /api/datasets/:id               Ver detalles
  DELETE /api/datasets/:id               Eliminar

ANALYTICS
  POST   /api/analytics/query            Ejecutar query
  GET    /api/analytics/summary          Resumen datos
  POST   /api/analytics/predict          Predicción ML
```

**Documentación completa:** http://localhost:8000/api/docs

---

## Tecnologías Usadas

**Backend:**
- FastAPI (Python 3.14)
- PostgreSQL (BD)
- Redis (Cache)
- SQLAlchemy (ORM)
- Pytest (Testing)

**Frontend:**
- Next.js 14 (React)
- TypeScript
- Tailwind CSS
- Zustand (Estado)
- Recharts (Gráficos)

---

## Tips Útiles

### Ver logs en tiempo real
```bash
docker-compose logs -f backend    # Backend logs
docker-compose logs -f postgres   # Database logs
docker-compose logs -f redis      # Cache logs
```

### Limpiar datos (si necesitas empezar de cero)
```bash
docker-compose down
docker volume rm enterpriseanalytics_pgdata  # Borra BD
docker volume rm enterpriseanalytics_redisdata
docker-compose up -d  # Reinicia
```

### Entrar a la BD directamente
```bash
docker-compose exec postgres psql -U analytics -d analyticsdb
# Luego ejecutar SQL: SELECT * FROM users;
```

### Ver variables de entorno
```bash
docker-compose exec backend python -c "from core.config import settings; print(settings.DATABASE_URL)"
```

---

## Tiempo Estimado

| Tarea | Tiempo |
|-------|--------|
| Iniciar Docker Compose | 1 min |
| Crear usuarios por defecto | 1 min |
| Frontend npm install | 2 min |
| npm run dev | 1 min |
| **Total** | **~5 minutos** |

---

## Checklist Final

Antes de reportar problemas, verificar:

- [ ] Docker Desktop está abierto y ejecutándose
- [ ] `docker-compose ps` muestra "running" para postgres y redis
- [ ] Base de datos PostgreSQL está lista
- [ ] Esperaste 30+ segundos después de `docker-compose up -d`
- [ ] Usuarios fueron creados con el script
- [ ] Contraseña es exactamente: `Admin@12345` (con mayúscula A)
- [ ] Frontend npm run dev está ejecutándose
- [ ] Abres http://localhost:3000 (no 0.0.0.0:3000)
- [ ] Limpias caché del navegador (Ctrl+Shift+R)


---

## Ahora Qué?

1. **Leer documentación:** COMO_EJECUTAR.md (guía completa)
2. **Probar API:** http://localhost:8000/api/docs (Swagger)
3. **Explorar dashboard:** http://localhost:3000/dashboard
4. **Ver tests:** `pytest tests/ -v`
5. **Revisar código:** backend/main.py, frontend/src/app/page.tsx

---

## Para Más Información

Ver estos archivos:
- `COMO_EJECUTAR.md` - Guía completa y detallada
- `backend/TEST_SUMMARY.md` - 83 tests documentados
- `backend/QUICK_REFERENCE.md` - Resumen de mejoras
- `backend/SYSTEM_IMPROVEMENTS.md` - Arquitectura

---

**¡Éxito! La aplicación está lista para usar.** 🎊

**Próximos pasos recomendados:**
1. Familiarizarse con el dashboard
2. Subir un archivo CSV de ejemplo
3. Crear una query
4. Ejecutar predicción ML
5. Leer las guías de mejoras propuestas

---

*Documento actualizado: Febrero 2026*
*Versión: 1.0 | Python 3.14.2 | Next.js 14*
