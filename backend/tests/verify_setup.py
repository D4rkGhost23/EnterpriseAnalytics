#!/usr/bin/env python
"""
Quick test verification script
Run this first to check if tests can run
"""
import sys
import os

# Add backend to path - IMPORTANT FOR IMPORTS
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_path)
print(f"✓ Added to path: {backend_path}")

def test_imports():
    """Test that all necessary imports work."""
    print("🔍 Verificando imports...")
    
    try:
        from core.config import settings
        print("✅ core.config imports ok")
    except ImportError as e:
        print(f"❌ core.config: {e}")
        return False
    
    try:
        from core.security import hash_password, verify_password, create_access_token
        print("✅ core.security imports ok")
    except ImportError as e:
        print(f"❌ core.security: {e}")
        return False
    
    try:
        from models.user import User, Tenant, UserRole
        print("✅ models.user imports ok")
    except ImportError as e:
        print(f"❌ models.user: {e}")
        return False
    
    try:
        from services.ingestion_service import validate_file_extension, scan_for_malicious_content
        print("✅ services.ingestion_service imports ok")
    except ImportError as e:
        print(f"❌ services.ingestion_service: {e}")
        return False
    
    try:
        from services.prediction_engine import run_linear_regression
        print("✅ services.prediction_engine imports ok")
    except ImportError as e:
        print(f"❌ services.prediction_engine: {e}")
        return False
    
    try:
        from schemas.auth import UserRegister, UserLogin
        print("✅ schemas.auth imports ok")
    except ImportError as e:
        print(f"❌ schemas.auth: {e}")
        return False
    
    return True


def test_basic_functions():
    """Test basic functions work."""
    print("\n🧪 Probando funciones básicas...")
    
    try:
        from core.security import hash_password, verify_password
        password = "Test123!@#"  # Más corta para evitar problemas bcrypt
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        print("✅ Password hashing works")
    except Exception as e:
        print(f"❌ Password hashing: {e}")
        return False
    
    try:
        from core.security import create_access_token, decode_token
        token = create_access_token({"sub": "test"})
        decoded = decode_token(token)
        assert decoded["sub"] == "test"
        print("✅ JWT token creation/validation works")
    except Exception as e:
        print(f"❌ JWT tokens: {e}")
        return False
    
    try:
        from services.ingestion_service import validate_file_extension
        ext = validate_file_extension("data.csv")
        assert ext == ".csv"
        print("✅ File extension validation works")
    except Exception as e:
        print(f"❌ File extension: {e}")
        return False
    
    try:
        from services.ingestion_service import scan_for_malicious_content
        is_malicious, _ = scan_for_malicious_content(b"Name,Age\n1,30")
        assert is_malicious is False
        print("✅ Malware scanning works")
    except Exception as e:
        print(f"❌ Malware scanning: {e}")
        return False
    
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("🚀 VERIFICACIÓN DE CONFIGURACIÓN DE TESTS")
    print("=" * 60)
    
    if not test_imports():
        print("\n❌ Fallo en imports. Verifica las rutas.")
        sys.exit(1)
    
    if not test_basic_functions():
        print("\n❌ Fallo en funciones básicas.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ ¡TODO OK! Puedes ejecutar los tests con:")
    print("=" * 60)
    print("\n  pytest tests/test_auth_service_v2.py -v")
    print("  pytest tests/test_ingestion_service_v2.py -v")
    print("  pytest tests/test_security_v2.py -v")
    print("  pytest tests/test_prediction_engine_v2.py -v")
    print("\n  O todos a la vez:")
    print("  pytest tests/ -v")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
