# 🎯 GUÍA DE INICIO - PASO A PASO

## ANTES DE EMPEZAR
Necesitas tener instalado:
- ✅ Docker Desktop (descarga desde https://www.docker.com/products/docker-desktop)
- ✅ Git (para descargar/manejar código)
- ✅ Node.js 18+ (si quieres ejecutar frontend sin Docker)

---

## MÉTODO 1: CON DOCKER (✅ RECOMENDADO - Más fácil)

### PASO 1: Abre PowerShell
```
1. Presiona Windows + R
2. Escribe: powershell
3. Presiona Enter
```

### PASO 2: Navega a la carpeta del proyecto
```powershell
cd "C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics"
```

### PASO 3: Inicia los servicios
```powershell
docker-compose up -d
```

**¿Qué hace esto?**
- Descarga imágenes de Docker (si es primera vez)
- Inicia PostgreSQL (la base de datos)
- Inicia Redis (el cache)
- Inicia el backend de FastAPI

**Espera 30-60 segundos** mientras se inicializa la base de datos.

### PASO 4: Crea los usuarios por defecto
```powershell
docker-compose exec backend python scripts/create_default_users.py
```

**¿Qué hace esto?**
- Crea la cuenta de admin
- Crea 3 usuarios de prueba
- Muestra las credenciales en pantalla

**Deberías ver algo así:**
```
✅ Usuario creado: admin@example.com / Admin@12345
✅ Usuario creado: analyst@example.com / Analyst@12345
✅ Usuario creado: viewer@example.com / Viewer@12345
✅ Usuario creado: demo@example.com / Demo@12345
```

### PASO 5: Abre el navegador
- **Frontend:** http://localhost:3000
- **Login con:** 
  - Email: `admin@example.com`
  - Contraseña: `Admin@12345`

---

## MÉTODO 2: SIN DOCKER (Si no tienes Docker instalado)

### PASO 1: Instala dependencias del Backend

```powershell
cd "C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics\backend"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**¿Qué hace esto?**
- Crea un "ambiente virtual" aislado de Python
- Instala todas las librerías necesarias

### PASO 2: Instala dependencias del Frontend

```powershell
cd "C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics\frontend"
npm install
```

**¿Qué hace esto?**
- Descarga todas las librerías de JavaScript/React

### PASO 3: Configura la Base de Datos (Necesitas PostgreSQL instalado)

**Opción A: Instalarlo localmente**
- Descarga PostgreSQL desde https://www.postgresql.org/download/
- Instala con contraseña: `analytics_pass` para usuario `analytics`
- Crea database: `analyticsdb`

**Opción B: (MÁS FÁCIL) Usar Docker SOLO para BD**
```powershell
docker run -d `
  --name postgres `
  -e POSTGRES_USER=analytics `
  -e POSTGRES_PASSWORD=analytics_pass `
  -e POSTGRES_DB=analyticsdb `
  -p 5432:5432 `
  postgres:15-alpine

docker run -d `
  --name redis `
  -p 6379:6379 `
  redis:7-alpine
```

### PASO 4: Inicia el Backend (en una ventana PowerShell)

```powershell
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Deberías ver:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
```

### PASO 5: Inicia el Frontend (en OTRA ventana PowerShell)

```powershell
cd frontend
npm run dev
```

**Deberías ver:**
```
> next dev
  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000
```

### PASO 6: Abre http://localhost:3000
- Email: `admin@example.com`
- Contraseña: `Admin@12345`

---

## ✅ VERIFICAR QUE TODO FUNCIONA

Ejecuta estos comandos para verificar:

### 1️⃣ ¿Los servicios de Docker están corriendo?
```powershell
docker-compose ps
```

**Deberías ver esto:**
```
NAME      STATUS
postgres  Up (healthy)
redis     Up
```

### 2️⃣ ¿El Backend responde?
```powershell
curl http://localhost:8000/api/health
```

**Deberías ver:**
```json
{"status":"ok"}
```

### 3️⃣ ¿El Frontend carga?
```powershell
curl http://localhost:3000
```

Abre en navegador: http://localhost:3000

### 4️⃣ ¿Puedo ver la API documentación?
Abre en navegador: http://localhost:8000/api/docs

---

## 🔐 TODAS LAS CREDENCIALES

```
┌─────────────────────────────────────────┐
│ CUENTA ADMIN (Acceso total)             │
├─────────────────────────────────────────┤
│ Email:      admin@example.com           │
│ Contraseña: Admin@12345                 │
│ Rol:        ADMIN                       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ CUENTA ANALYST (Solo lectura+análisis)  │
├─────────────────────────────────────────┤
│ Email:      analyst@example.com         │
│ Contraseña: Analyst@12345               │
│ Rol:        ANALYST                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ CUENTA VIEWER (Solo lectura)            │
├─────────────────────────────────────────┤
│ Email:      viewer@example.com          │
│ Contraseña: Viewer@12345                │
│ Rol:        VIEWER                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ CUENTA DEMO (Para pruebas)              │
├─────────────────────────────────────────┤
│ Email:      demo@example.com            │
│ Contraseña: Demo@12345                  │
│ Rol:        ANALYST                     │
└─────────────────────────────────────────┘
```

---

## 🌐 TODOS LOS LINKS

| Servicio | URL | Usuario |
|----------|-----|---------|
| **Frontend** | http://localhost:3000 | admin@example.com |
| **Login** | http://localhost:3000/login | (mismas credenciales) |
| **Dashboard** | http://localhost:3000/dashboard | (después de login) |
| **API Swagger** | http://localhost:8000/api/docs | Prueba endpoints aquí |
| **API ReDoc** | http://localhost:8000/api/redoc | Documentación |
| **Base Datos** | localhost:5432 | user: analytics |
| **Cache Redis** | localhost:6379 | (sin contraseña) |

---

## ⚠️ ERRORES COMUNES Y SOLUCIONES

### Error: "docker: command not found"
**Problema:** Docker no está instalado o no está en el PATH
**Solución:**
1. Descarga Docker Desktop desde https://www.docker.com/products/docker-desktop
2. Instala y reinicia tu computadora
3. Abre PowerShell y verifica: `docker --version`

---

### Error: "Port 3000 already in use"
**Problema:** Otro programa está usando el puerto 3000
**Solución:**
```powershell
# Ver qué está usando el puerto
netstat -ano | findstr :3000

# Resultará algo como: TCP ... 12345 (PID)
# Ciérralo:
taskkill /PID 12345 /F

# O simplemente usa otro puerto:
npm run dev -- -p 3001
```

---

### Error: "Connection refused" al login
**Problema:** El backend no está responde
**Solución:**
```powershell
# Verifica que el backend esté corriendo:
curl http://localhost:8000/api/docs

# Si no funciona, reinicia:
docker-compose down
docker-compose up -d
```

---

### Error: "Invalid credentials" en login
**Problema:** Contraseña incorrecta
**Verificar:**
1. Email exacto: `admin@example.com` (sin mayúsculas)
2. Contraseña: `Admin@12345` (A mayúscula, número 1 y 2 al final)
3. Limpia caché: Presiona Ctrl+Shift+R

---

### Error: "Database connection error"
**Problema:** PostgreSQL no está listo
**Solución:**
```powershell
# Espera más tiempo (30-60 seg)
# Verifica logs:
docker-compose logs postgres

# Si aún no funciona, reinicia:
docker-compose down
docker-compose up -d
docker-compose logs -f postgres
```

---

## 🧪 EJECUTAR TESTS

### Con Docker:
```powershell
docker-compose exec backend pytest tests/ -v
```

**Deberías ver:**
```
test_security_v2.py::test_password_hashing PASSED
test_auth_service_v2.py::test_register_user PASSED
...
======================== 83 passed in 16.90s ========================
```

### Sin Docker (desde carpeta backend):
```powershell
cd backend
venv\Scripts\activate
pytest tests/ -v
```

---

## 🎯 PRIMERAS ACCIONES DESPUÉS DE INICIAR

### 1. Entra a http://localhost:3000
```
Email:      admin@example.com
Contraseña: Admin@12345
Click "Sign In"
```

### 2. Explora el Dashboard
```
- Overview (resumen del sistema)
- Datasets (subir archivos)
- Query (ejecutar SQL)
- Predictions (ML predictions)
- Visualizations (ver gráficos)
```

### 3. Prueba subir un archivo
```
1. Click en "Datasets"
2. Click en "Upload Dataset"
3. Elige un archivo CSV, XLSX o JSON
4. Click "Upload"
```

### 4. Prueba ejecutar una query
```
1. Click en "Query"
2. Escribe: SELECT * FROM datasets LIMIT 5;
3. Click "Execute"
4. Ver resultados
```

### 5. Prueba la API
```
1. Ir a http://localhost:8000/api/docs
2. Click en "Authorize"
3. Copiar este token en body:
   {
     "email": "admin@example.com",
     "password": "Admin@12345"
   }
4. Click "Try it out"
5. Copiar el "access_token" de la respuesta
6. Pegar en Authorize: Bearer <token>
7. Ahora puedes probar otros endpoints
```

---

## 🔄 DESARROLLO CON AUTO-RELOAD

Si vas a modificar el código:

### Terminal 1: Backend (auto-reload)
```powershell
cd backend
uvicorn main:app --reload
```

### Terminal 2: Frontend (hot reload)
```powershell
cd frontend
npm run dev
```

**Ahora cada vez que guardes un archivo, se actualiza automáticamente** ⚡

---

## 📊 ESTRUCTURA DE CARPETAS

```
EnterpriseAnalytics/
│
├── 📄 README.md                    ← Info general
├── 📄 INICIO_RAPIDO.md             ← Este archivo (paso a paso)
├── 📄 COMO_EJECUTAR.md             ← Guía detallada
├── 📄 CHEAT_SHEET.md               ← Comandos rápidos
│
├── 📦 docker-compose.yml           ← Configuración Docker
│
├── 🐍 backend/                     ← API FastAPI
│   ├── main.py                     ← Punto de entrada
│   ├── requirements.txt            ← Dependencias Python
│   ├── core/
│   │   ├── config.py               ← Configuración
│   │   ├── database.py             ← Conexión BD
│   │   └── security.py             ← JWT, Auth
│   ├── models/                     ← Esquemas BD (User, Dataset, etc)
│   ├── routers/                    ← Endpoints API
│   │   ├── auth.py                 ← Login/Register
│   │   ├── datasets.py             ← Subir archivos
│   │   ├── analytics.py            ← Análisis
│   │   ├── predictions.py          ← ML
│   │   └── query.py                ← SQL queries
│   ├── services/                   ← Lógica de negocio
│   ├── tests/                      ← 83 tests ✅
│   └── scripts/
│       └── create_default_users.py ← Crear usuarios
│
└── 🌐 frontend/                    ← App Next.js React
    ├── package.json                ← Dependencias JavaScript
    ├── next.config.ts              ← Config Next.js
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx            ← Página inicio
    │   │   ├── login/page.tsx       ← Login
    │   │   ├── register/page.tsx    ← Registro
    │   │   └── dashboard/           ← Panel principal
    │   ├── components/              ← Componentes React
    │   │   ├── charts/              ← Gráficos
    │   │   ├── forms/               ← Formularios
    │   │   └── layout/              ← Header, Sidebar
    │   ├── lib/api.ts               ← Cliente HTTP
    │   └── types/                   ← TypeScript types
    └── public/                      ← Assets estáticos
```

---

## 💡 TIPS ÚTILES

### Ver logs en tiempo real (Docker)
```powershell
docker-compose logs -f backend      # Logs del backend
docker-compose logs -f postgres     # Logs de BD
docker-compose logs -f redis        # Logs de cache
```

### Entrar a la base de datos directamente
```powershell
docker-compose exec postgres psql -U analytics -d analyticsdb
# Luego:
SELECT * FROM users;
\dt  (ver todas las tablas)
\q   (salir)
```

### Limpiar todo y empezar de cero
```powershell
docker-compose down
docker volume rm enterpriseanalytics_pgdata
docker volume rm enterpriseanalytics_redisdata
docker-compose up -d
docker-compose exec backend python scripts/create_default_users.py
```

### Ver variables de entorno
```powershell
docker-compose exec backend python -c "from core.config import settings; print(settings.DATABASE_URL)"
```

---

## ⏱️ TIEMPO TOTAL

| Tarea | Tiempo |
|-------|--------|
| Descargar/instalar Docker | 10-15 min (primera vez) |
| `docker-compose up -d` | 1-2 min |
| Crear usuarios | 30 seg |
| `npm run dev` | 1 min |
| Abrir navegador | 30 seg |
| **TOTAL PRIMERA VEZ** | **~5 min** (después de Docker) |
| **Próximas veces** | **~2 min** |

---

## ✅ CHECKLIST FINAL

Antes de reportar problemas:

- [ ] Instalé Docker Desktop
- [ ] Ejecuté `docker-compose up -d` desde la carpeta principal
- [ ] Esperé 30 segundos a que la BD inicie
- [ ] Ejecuté el script de usuarios
- [ ] Veo `postgres Up` en `docker-compose ps`
- [ ] Puedo acceder a http://localhost:3000
- [ ] La página de login carga
- [ ] Intento login con admin@example.com / Admin@12345
- [ ] Me deja entrar al dashboard

Si todo esto ✅, **¡la app está funcionando!** 🎉

---

## 📖 DOCUMENTOS ADICIONALES

Para más detalles, lee estos archivos:

1. **README.md** - Información general del proyecto
2. **COMO_EJECUTAR.md** - Guía completa y detallada
3. **CHEAT_SHEET.md** - Comandos rápidos y atajos
4. **backend/TEST_SUMMARY.md** - Información sobre los 83 tests
5. **backend/QUICK_REFERENCE.md** - Resumen de mejoras propuestas

---

## 🆘 ¿Aún tienes problemas?

1. Lee la sección "⚠️ ERRORES COMUNES" arriba
2. Verifica los logs: `docker-compose logs`
3. Reinicia todo: `docker-compose down && docker-compose up -d`
4. Limpia caché del navegador: Ctrl+Shift+R
5. Cierra/abre Firefox o Chrome de nuevo

---

**¡Éxito! La aplicación está lista para usar.** 🚀

**Próximos pasos:**
1. Sube un dataset de ejemplo
2. Crea una query SQL
3. Prueba una predicción
4. Explora el dashboard
5. Lee las guías de mejoras (System Improvements)

---

*Última actualización: Febrero 2026*
