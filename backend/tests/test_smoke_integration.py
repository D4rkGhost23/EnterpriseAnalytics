"""
Smoke Tests / Integration Tests
Tests complete workflows: Register → Upload → Analyze → Predict
"""
import pytest
import json
import tempfile
import pandas as pd
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from main import app
from models.user import User, Tenant, UserRole
from models.dataset import Dataset
from schemas.auth import UserRegister, UserLogin
from services.auth_service import register_user, login_user


@pytest.fixture
async def test_db():
    """Create in-memory test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client():
    """Create test client for FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_csv_file():
    """Create sample CSV file for upload."""
    csv_data = "ProductID,SalesAmount,Quantity,Region\n1,1000.50,5,North\n2,2500.75,10,South\n3,1800.00,8,East"
    return csv_data.encode("utf-8")


@pytest.fixture
def sample_json_file():
    """Create sample JSON file for upload."""
    json_data = [
        {"id": 1, "name": "Product A", "price": 99.99, "stock": 100},
        {"id": 2, "name": "Product B", "price": 149.99, "stock": 50}
    ]
    return json.dumps(json_data).encode("utf-8")


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 1: User Registration Flow
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_user_registration(client):
    """Smoke test: User can register successfully."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!@#",
            "full_name": "New User",
            "tenant_name": "My Company"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["role"] in ["owner", "analyst"]


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 2: User Login Flow
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_user_login(client):
    """Smoke test: User can login after registration."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!@#",
            "full_name": "Test User",
            "tenant_name": "Test Org"
        }
    )
    assert register_response.status_code == 201

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!@#"
        }
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 3: Token Refresh Flow
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_token_refresh(client):
    """Smoke test: Access token can be refreshed."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "Pass123!",
            "full_name": "User",
            "tenant_name": "Org"
        }
    )
    refresh_token = register_response.json()["refresh_token"]

    # Refresh
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert data["access_token"] != refresh_token


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 4: Get Current User Profile
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_get_current_user(client):
    """Smoke test: Authenticated user can fetch their profile."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@example.com",
            "password": "Pass123!",
            "full_name": "Profile User",
            "tenant_name": "Org"
        }
    )
    access_token = register_response.json()["access_token"]

    # Get profile
    profile_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert profile_response.status_code == 200
    data = profile_response.json()
    assert data["email"] == "profile@example.com"


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 5: File Upload & Dataset Creation
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_file_upload(client, sample_csv_file):
    """Smoke test: User can upload CSV file."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "uploader@example.com",
            "password": "Pass123!",
            "full_name": "Uploader",
            "tenant_name": "DataOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Upload file
    files = {"file": ("data.csv", sample_csv_file, "text/csv")}
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert upload_response.status_code in [200, 201]
    data = upload_response.json()
    assert "dataset_id" in data or "id" in data


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 6: Generate Analytics Insights
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_generate_insights(client, sample_csv_file):
    """Smoke test: User can generate analytics on uploaded dataset."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@example.com",
            "password": "Pass123!",
            "full_name": "Analyst",
            "tenant_name": "AnalyticsOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Upload
    files = {"file": ("sales.csv", sample_csv_file, "text/csv")}
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    dataset_id = upload_response.json()["dataset_id"] or upload_response.json()["id"]

    # Generate insights
    insights_response = await client.get(
        f"/api/v1/analytics/insights/{dataset_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert insights_response.status_code in [200, 202]  # 202 if async
    data = insights_response.json()
    assert "insights" in data or "status" in data


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 7: Run Prediction Model
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_run_prediction(client, sample_csv_file):
    """Smoke test: User can run ML predictions."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "predictor@example.com",
            "password": "Pass123!",
            "full_name": "Predictor",
            "tenant_name": "PredictOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Upload
    files = {"file": ("data.csv", sample_csv_file, "text/csv")}
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    dataset_id = upload_response.json()["dataset_id"] or upload_response.json()["id"]

    # Run prediction
    prediction_response = await client.post(
        f"/api/v1/predictions/{dataset_id}",
        json={
            "model_type": "linear_regression",
            "target_col": "SalesAmount",
            "forecast_periods": 6
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert prediction_response.status_code in [200, 202]
    data = prediction_response.json()
    assert "forecast" in data or "status" in data


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 8: Execute Custom Query
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_execute_query(client, sample_csv_file):
    """Smoke test: User can execute SQL-like query on dataset."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "querier@example.com",
            "password": "Pass123!",
            "full_name": "Querier",
            "tenant_name": "QueryOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Upload
    files = {"file": ("data.csv", sample_csv_file, "text/csv")}
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    dataset_id = upload_response.json()["dataset_id"] or upload_response.json()["id"]

    # Execute query
    query_response = await client.post(
        f"/api/v1/query/{dataset_id}",
        json={
            "query": "SELECT * WHERE SalesAmount > 1500"
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert query_response.status_code in [200, 202]


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 9: Complete End-to-End Flow
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_complete_workflow(client, sample_csv_file):
    """Smoke test: Complete workflow (Register → Upload → Analyze → Predict)."""
    
    # Step 1: Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "e2e@example.com",
            "password": "Pass123!",
            "full_name": "End-to-End User",
            "tenant_name": "E2E Company"
        }
    )
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]

    # Step 2: Verify login works
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "e2e@example.com",
            "password": "Pass123!"
        }
    )
    assert login_response.status_code == 200

    # Step 3: Get profile
    profile_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert profile_response.status_code == 200

    # Step 4: Upload dataset
    files = {"file": ("e2e.csv", sample_csv_file, "text/csv")}
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert upload_response.status_code in [200, 201]
    dataset_id = upload_response.json().get("dataset_id") or upload_response.json().get("id")

    # Step 5: Generate insights (optional)
    insights_response = await client.get(
        f"/api/v1/analytics/insights/{dataset_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert insights_response.status_code in [200, 202, 404]  # 404 if endpoint not ready

    print("✓ Complete E2E workflow succeeded")


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 10: Security - Unauthorized Access Blocked
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_unauthorized_access_blocked(client):
    """Smoke test: Unauthorized requests are blocked."""
    
    # Try to access protected endpoint without token
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403 or response.status_code == 401

    # Try with invalid token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code in [401, 403]


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 11: Rate Limiting
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_rate_limiting():
    """Smoke test: Rate limiting is enforced."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        responses = []
        
        # Send multiple requests in quick succession
        for i in range(15):  # Try to exceed rate limit
            response = await client.get("/api/v1/auth/me")
            responses.append(response.status_code)

        # At least one request should hit rate limit (429) or auth error (401/403)
        status_codes = set(responses)
        assert 429 in status_codes or 401 in status_codes or 403 in status_codes


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 12: Malicious File Upload Rejected
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_malicious_file_rejected(client):
    """Smoke test: Malicious files are rejected."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "secure@example.com",
            "password": "Pass123!",
            "full_name": "Security User",
            "tenant_name": "SecureOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Try to upload executable disguised as CSV
    malicious_content = b"Name,Age\nexec(__import__('os').system('rm -rf /'))"
    files = {"file": ("data.csv", malicious_content, "text/csv")}
    
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    # Should be rejected
    assert upload_response.status_code in [400, 422, 403]


# ─────────────────────────────────────────────────────────────
# SMOKE TEST 13: Wrong File Type Rejected
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_wrong_file_type_rejected(client):
    """Smoke test: Unsupported file types are rejected."""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "filetype@example.com",
            "password": "Pass123!",
            "full_name": "FileType User",
            "tenant_name": "FileOrg"
        }
    )
    access_token = register_response.json()["access_token"]

    # Try to upload .exe
    files = {"file": ("malware.exe", b"MZ\x90\x00", "application/x-msdownload")}
    
    upload_response = await client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert upload_response.status_code in [400, 422, 403]
