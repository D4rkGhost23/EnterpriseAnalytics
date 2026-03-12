#!/usr/bin/env python3
"""
Script para crear usuarios por defecto en la base de datos
Uso: python scripts/create_default_users.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings
from core.security import hash_password
from models.user import User, Tenant, UserRole


async def create_default_users():
    """Crear usuarios por defecto en la BD"""
    
    # Crear engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    
    # Crear sesión
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Crear tenant por defecto
            tenant = Tenant(
                name="Default Company",
                slug="default-company",
                created_at=datetime.now(timezone.utc)
            )
            db.add(tenant)
            await db.flush()
            
            print(f"✅ Tenant creado: {tenant.name} (ID: {tenant.id})")
            
            # Usuarios por defecto
            default_users = [
                {
                    "email": "admin@example.com",
                    "password": "Admin@12345",
                    "full_name": "Admin User",
                    "role": UserRole.ADMIN,
                    "description": "Usuario administrador"
                },
                {
                    "email": "analyst@example.com",
                    "password": "Analyst@12345",
                    "full_name": "Data Analyst",
                    "role": UserRole.ANALYST,
                    "description": "Usuario analista"
                },
                {
                    "email": "viewer@example.com",
                    "password": "Viewer@12345",
                    "full_name": "Viewer User",
                    "role": UserRole.VIEWER,
                    "description": "Usuario lector"
                },
                {
                    "email": "demo@example.com",
                    "password": "Demo@12345",
                    "full_name": "Demo User",
                    "role": UserRole.ANALYST,
                    "description": "Usuario de demostración"
                }
            ]
            
            # Crear usuarios
            for user_data in default_users:
                hashed_password = hash_password(user_data["password"])
                
                user = User(
                    email=user_data["email"],
                    hashed_password=hashed_password,
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    tenant_id=tenant.id,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(user)
                
                print(f"✅ Usuario creado:")
                print(f"   Email:     {user_data['email']}")
                print(f"   Contraseña: {user_data['password']}")
                print(f"   Rol:       {user_data['role'].value}")
                print()
            
            # Commit
            await db.commit()
            
            print("=" * 60)
            print("✅ USUARIOS CREADOS EXITOSAMENTE")
            print("=" * 60)
            print()
            print("Credenciales para login:")
            print()
            for user_data in default_users:
                print(f"👤 {user_data['full_name']} ({user_data['role'].value})")
                print(f"   Email:      {user_data['email']}")
                print(f"   Contraseña: {user_data['password']}")
                print()
            
            print("URL de login: http://localhost:3000/login")
            print("API Docs:     http://localhost:8000/api/docs")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("Creando usuarios por defecto...")
    print()
    asyncio.run(create_default_users())
