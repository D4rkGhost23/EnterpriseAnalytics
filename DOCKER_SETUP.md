# Guía de Ejecución con Docker

## Estado Actual ✅
- **Predicción Engine Tests**: 26/26 ✅ PASADOS
- **Total Tests Backend**: 156/197 PASADOS
- **Dependencias**: Todas instaladas
- **Configuración**: .env creado

## Prerequisitos
- Docker y Docker Compose instalados
- Puerto 5432 (PostgreSQL) disponible
- Puerto 6379 (Redis) disponible  
- Puerto 8000 (Backend) disponible
- Puerto 3000 (Frontend) disponible

## Ejecutar Aplicación

### 1. Desde raíz del proyecto:
```bash
docker-compose up -d
```

### 2. Esperar a que todos los servicios inicien
```bash
docker-compose ps
```

Debería ver:
- postgres: healthy
- redis: healthy
- backend: running
- frontend: running

### 3. Acceder a la Aplicación
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Crear Usuario Default (Opcional)
```bash
docker-compose exec backend python scripts/create_default_users.py
```

## Logs
```bash
docker-compose logs -f backend    # Backend logs
docker-compose logs -f frontend   # Frontend logs
docker-compose logs -f postgres   # Database logs
docker-compose logs -f redis      # Cache logs
```

## Detener Servicios
```bash
docker-compose down
```

## Detener y Limpiar Volúmenes
```bash
docker-compose down -v
```

## Problemas Conocidos
- Tests async en test_security.py y test_smoke_integration.py necesitan refactor
- Usar TEST_SUMMARY.md para detalles de tests unitarios

## Variables Importantes en .env
- DATABASE_URL: URL de conexión PostgreSQL
- REDIS_URL: URL de conexión Redis
- SECRET_KEY: Clave secreta (cambiar en producción)
- NEXT_PUBLIC_API_URL: URL del API para el frontend
