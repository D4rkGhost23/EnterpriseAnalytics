#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from core.config import settings
    from core.security import hash_password
    from models.user import User, Tenant, UserRole
    from core.database import Base
    
    print("🔌 Conectando a BD...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Crear tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tablas creadas/verificadas")
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Verificar si tenant existe
            result = await db.execute(select(Tenant))
            existing_tenant = result.scalar_one_or_none()
            
            if existing_tenant:
                tenant_id = existing_tenant.id
                print(f"✅ Tenant existente: {existing_tenant.name} (ID: {tenant_id})")
            else:
                tenant = Tenant(
                    name="Default Company",
                    slug="default-company",
                    created_at=datetime.now(timezone.utc)
                )
                db.add(tenant)
                await db.flush()
                tenant_id = tenant.id
                print(f"✅ Tenant creado: {tenant.name} (ID: {tenant_id})")
            
            # Crear usuarios
            users_data = [
                ("admin@example.com", "Admin@12345", "Administrator", UserRole.ADMIN),
                ("user@example.com", "User@12345", "Regular User", UserRole.ANALYST),
            ]
            
            for email, password, name, role in users_data:
                # Verificar si existe
                result = await db.execute(select(User).where(User.email == email))
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"⚠️  Usuario ya existe: {email}")
                else:
                    user = User(
                        email=email,
                        hashed_password=hash_password(password),
                        full_name=name,
                        role=role,
                        tenant_id=tenant_id,
                        is_active=True,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(user)
                    print(f"✅ Usuario creado: {email} / {password}")
            
            await db.commit()
            print("\n🎉 Base de datos inicializada correctamente!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
