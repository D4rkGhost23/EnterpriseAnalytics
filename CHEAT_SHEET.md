# ⚡ Cheat Sheet - Cómo Ejecutar Enterprise Analytics

## 🎯 Opción 1: Docker (Más Rápido - Recomendado)

```bash
# 1. Iniciar todo
cd C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics
docker-compose up -d

# 2. Esperar ~30 segundos, luego crear usuario
# (Opción A: Por interfaz web)
# Ir a http://localhost:3000/register y crear usuario

# (Opción B: Por script)
docker-compose exec backend python scripts/create_default_users.py

# 3. Acceder a la app
Frontend: http://localhost:3000
API Docs: http://localhost:8000/api/docs
```

---

## 🎯 Opción 2: Manual (Más Control)

```bash
# TERMINAL 1 - Backend
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# TERMINAL 2 - Frontend
cd frontend
npm install
npm run dev

# TERMINAL 3 - Ver logs (opcional)
docker-compose logs -f postgres redis
```

---

## 🔐 Credenciales por Defecto

```
Email:      admin@example.com
Contraseña: Admin@12345
Rol:        ADMIN

Alternativas:
- analyst@example.com    / Analyst@12345   (ANALYST)
- viewer@example.com     / Viewer@12345    (VIEWER)
- demo@example.com       / Demo@12345      (ANALYST)
```

---

## 🌐 URLs Principales

| Aplicación | URL | Puerto |
|-----------|-----|--------|
| **Frontend** | http://localhost:3000 | 3000 |
| **Backend** | http://localhost:8000 | 8000 |
| **Swagger Docs** | http://localhost:8000/api/docs | 8000 |
| **ReDoc** | http://localhost:8000/api/redoc | 8000 |
| **PostgreSQL** | localhost:5432 | 5432 |
| **Redis** | localhost:6379 | 6379 |

---

## 🧪 Verificar que Todo Funciona

```bash
# Check 1: Servicios corriendo
docker-compose ps

# Check 2: PostgreSQL responde
docker-compose exec postgres pg_isready -U analytics

# Check 3: Redis responde
docker-compose exec redis redis-cli ping

# Check 4: Backend responde
curl http://localhost:8000/docs

# Check 5: Frontend carga
curl http://localhost:3000

# Check 6: API funciona
curl -X GET http://localhost:8000/api/docs
```

---

## 🚀 Comandos Útiles

### Docker Compose
```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Ver logs
docker-compose logs -f backend

# Reiniciar un servicio
docker-compose restart postgres

# Ejecutar comando en contenedor
docker-compose exec backend python scripts/create_default_users.py
```

### Backend (Python)
```bash
# Activar venv
source venv/Scripts/activate

# Ejecutar server
uvicorn main:app --reload

# Ejecutar tests
pytest tests/ -v

# Ver configuración
python -c "from core.config import settings; print(settings)"
```

### Frontend (Node.js)
```bash
# Desarrollo (hot reload)
npm run dev

# Build para producción
npm run build

# Ejecutar versión producción
npm start

# Linting
npm run lint
```

---

## ⚠️ Problemas Comunes

### ❌ "Connection refused" (PostgreSQL no responde)

```bash
# Solución
docker-compose down
docker volume rm enterpriseanalytics_pgdata  # Limpiar BD
docker-compose up -d
docker-compose logs postgres | grep "ready to accept"
```

### ❌ "Cannot connect to Docker daemon"

```bash
# Reiniciar Docker Desktop (Windows/Mac)
# O instalar Docker si no está: https://www.docker.com/products/docker-desktop
```

### ❌ "Port 3000 already in use"

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :3000
kill -9 <PID>
```

### ❌ "JWT token invalid"

```bash
# Limpiar localStorage y login de nuevo
# Abrir DevTools (F12) → Console:
localStorage.clear()
# Recargar página y login
```

### ❌ "ModuleNotFoundError"

```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
npm install missing-package
```

---

## 📋 Flujo de Ejecución Completo

### Paso 1: Preparación (1 min)
```bash
cd C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics
docker-compose up -d
sleep 30  # Esperar a que BD inicie
```

### Paso 2: Crear Usuario (1 min)
```bash
# Opción A: Por terminal
docker-compose exec backend python scripts/create_default_users.py

# Opción B: Por web
# Ir a http://localhost:3000/register
# Crear usuario con email/contraseña
```

### Paso 3: Iniciar Frontend (1 min)
```bash
cd frontend
npm install
npm run dev
```

### Paso 4: Login (30 seg)
```
Ir a: http://localhost:3000
Email: admin@example.com
Contraseña: Admin@12345
```

### Paso 5: Explorar (sin límite)
```
- Dashboard: http://localhost:3000/dashboard
- API Docs: http://localhost:8000/api/docs
- Upload CSV: http://localhost:3000/dashboard/datasets
```

**Tiempo total: ~5 minutos ⏱️**

---

## 🔄 Ciclo de Desarrollo

```bash
# Terminal 1: Backend con auto-reload
cd backend
uvicorn main:app --reload

# Terminal 2: Frontend con hot reload
cd frontend
npm run dev

# Terminal 3: Ejecutar tests
cd backend
pytest tests/ -v -s

# Cambios se reflejan automáticamente en navegador!
```

---

## 📊 Probar la API (Swagger)

1. Abrir: http://localhost:8000/api/docs
2. Click en "Authorize" (arriba derecha)
3. Ejecutar POST `/api/auth/login`:
   ```json
   {
     "email": "admin@example.com",
     "password": "Admin@12345"
   }
   ```
4. Copiar `access_token` del response
5. En "Authorize" pegar: `Bearer <token>`
6. ¡Ahora puedes probar endpoints protegidos!

---

## 🗂️ Estructura de Archivos Clave

```
C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics\
├── docker-compose.yml           ← Inicia BD, cache, backend
├── COMO_EJECUTAR.md            ← Guía completa
│
├── backend/
│   ├── main.py                 ← Punto de entrada FastAPI
│   ├── requirements.txt         ← Dependencias Python
│   ├── core/
│   │   ├── config.py           ← Variables de entorno
│   │   ├── database.py         ← Conexión a PostgreSQL
│   │   ├── security.py         ← Auth, JWT, hashing
│   │   └── redis_client.py     ← Conexión a Redis
│   ├── models/                 ← Esquemas BD (User, Dataset, etc)
│   ├── routers/                ← Endpoints API (/auth, /datasets)
│   ├── services/               ← Lógica de negocio
│   ├── schemas/                ← Validación Pydantic
│   ├── tests/                  ← Tests (83 tests ✅)
│   └── scripts/
│       └── create_default_users.py ← Script crear usuarios
│
└── frontend/
    ├── package.json
    ├── src/
    │   ├── app/                ← Páginas (login, register, dashboard)
    │   ├── components/         ← Componentes React
    │   ├── lib/api.ts         ← Cliente HTTP
    │   └── store/             ← Estado global
    └── README_EJECUCION.md
```

---

## 🎓 Recursos Documentación

| Documento | Ubicación | Contenido |
|-----------|-----------|----------|
| Guía Ejecución | `COMO_EJECUTAR.md` | Cómo correr la app |
| Tests | `backend/TEST_SUMMARY.md` | 83 tests documentados |
| BD Mejoras | `backend/DATABASE_IMPROVEMENTS.md` | Auditoría, versionado, etc |
| Arquitectura | `backend/SYSTEM_IMPROVEMENTS.md` | Caching, indexing, deploy |
| Quick Ref | `backend/QUICK_REFERENCE.md` | Resumen ejecutivo |
| Frontend | `frontend/README_EJECUCION.md` | Instrucciones frontend |

---

## ✅ Checklist Final

- [ ] Docker Desktop instalado y ejecutándose
- [ ] git clone (o ya tienes el código)
- [ ] docker-compose up -d completado
- [ ] PostgreSQL estado "ready"
- [ ] Usuario creado (admin@example.com / Admin@12345)
- [ ] Frontend: npm run dev ejecutándose
- [ ] Acceso a http://localhost:3000 funciona
- [ ] Login exitoso
- [ ] Dashboard visible

**Si todos los ✅, ¡estás listo! 🎉**

---

## 🆘 Soporte Rápido

**Backend no inicia:**
```bash
docker-compose logs backend
# Revisar error, normalmente es por:
# - Puerto en uso
# - BD no lista
# - Variable de entorno faltante
```

**BD no inicia:**
```bash
docker-compose logs postgres
# Esperar más tiempo o:
docker-compose down
docker volume rm enterpriseanalytics_pgdata
docker-compose up -d
```

**Frontend no carga:**
```bash
# Verificar que Backend esté en :8000
# Limpiar cache browser
# Reinstalar: cd frontend && rm -rf node_modules && npm install
```

---

**Total de tiempo para tener todo ejecutando: ~5-10 minutos** ⏱️

¡Buena suerte! 🚀
