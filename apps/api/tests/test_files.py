"""File upload and management tests"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from io import BytesIO
from pathlib import Path

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.models.cad import CADModel


def create_authenticated_user(client: TestClient, db: Session):
    """Helper to create and authenticate a user"""
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]
    return user, token


def create_test_file(filename: str, content: bytes = None) -> tuple[BytesIO, bytes]:
    """Helper to create test file"""
    if content is None:
        content = b"STEP 214 HEADER SECTION" * 100  # Simulate STEP file

    file_obj = BytesIO(content)
    return file_obj, content


# ============================================================================
# CAD Model Upload Tests
# ============================================================================

def test_upload_cad_model_step(client: TestClient, db: Session):
    """Test uploading a STEP file"""
    _, token = create_authenticated_user(client, db)

    file_obj, content = create_test_file("bracket.step")

    response = client.post(
        "/api/files/cad/upload",
        files={"file": ("bracket.step", file_obj, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "bracket.step"
    assert data["file_size"] == len(content)
    assert "id" in data
    assert "file_hash" in data


def test_upload_cad_model_with_metadata(client: TestClient, db: Session):
    """Test uploading CAD model with name and description"""
    _, token = create_authenticated_user(client, db)

    file_obj, _ = create_test_file("model.step")

    response = client.post(
        "/api/files/cad/upload?name=Custom Name&description=Test model",
        files={"file": ("model.step", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom Name"


def test_upload_invalid_file_type(client: TestClient, db: Session):
    """Test uploading unsupported file type"""
    _, token = create_authenticated_user(client, db)

    file_obj, _ = create_test_file("document.txt", b"Not a CAD file")

    response = client.post(
        "/api/files/cad/upload",
        files={"file": ("document.txt", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_file_too_large(client: TestClient, db: Session):
    """Test uploading file exceeding size limit"""
    _, token = create_authenticated_user(client, db)

    # Create file larger than 100MB
    large_content = b"x" * (101 * 1024 * 1024)
    file_obj, _ = create_test_file("large.step", large_content)

    response = client.post(
        "/api/files/cad/upload",
        files={"file": ("large.step", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 413


def test_upload_duplicate_file(client: TestClient, db: Session):
    """Test uploading duplicate file"""
    _, token = create_authenticated_user(client, db)

    file_obj1, content = create_test_file("model1.step")

    # Upload first time
    response1 = client.post(
        "/api/files/cad/upload",
        files={"file": ("model1.step", file_obj1)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 201

    # Upload same content again with different filename
    file_obj2 = BytesIO(content)
    response2 = client.post(
        "/api/files/cad/upload",
        files={"file": ("model2.step", file_obj2)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_upload_requires_authentication(client: TestClient, db: Session):
    """Test that upload requires authentication"""
    file_obj, _ = create_test_file("model.step")

    response = client.post(
        "/api/files/cad/upload",
        files={"file": ("model.step", file_obj)}
    )
    assert response.status_code == 403


# ============================================================================
# CAD Model Listing Tests
# ============================================================================

def test_list_cad_models(client: TestClient, db: Session):
    """Test listing CAD models"""
    _, token = create_authenticated_user(client, db)

    # Upload multiple models
    for i in range(3):
        file_obj, _ = create_test_file(f"model{i}.step")
        client.post(
            "/api/files/cad/upload",
            files={"file": (f"model{i}.step", file_obj)},
            headers={"Authorization": f"Bearer {token}"}
        )

    # List models
    response = client.get(
        "/api/files/cad",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 3


def test_list_cad_models_with_pagination(client: TestClient, db: Session):
    """Test listing models with pagination"""
    _, token = create_authenticated_user(client, db)

    # Upload 5 models
    for i in range(5):
        file_obj, _ = create_test_file(f"model{i}.step")
        client.post(
            "/api/files/cad/upload",
            files={"file": (f"model{i}.step", file_obj)},
            headers={"Authorization": f"Bearer {token}"}
        )

    # Get first page
    response = client.get(
        "/api/files/cad?skip=0&limit=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    models = response.json()
    assert len(models) <= 2


# ============================================================================
# CAD Model Details Tests
# ============================================================================

def test_get_cad_model_details(client: TestClient, db: Session):
    """Test getting CAD model details"""
    _, token = create_authenticated_user(client, db)

    # Upload model
    file_obj, _ = create_test_file("model.step")
    upload_response = client.post(
        "/api/files/cad/upload",
        files={"file": ("model.step", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    model_id = upload_response.json()["id"]

    # Get details
    response = client.get(
        f"/api/files/cad/{model_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == model_id
    assert data["file_name"] == "model.step"


def test_get_nonexistent_model(client: TestClient, db: Session):
    """Test getting non-existent model"""
    _, token = create_authenticated_user(client, db)

    from uuid import uuid4
    fake_id = uuid4()

    response = client.get(
        f"/api/files/cad/{fake_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


# ============================================================================
# CAD Model Update Tests
# ============================================================================

def test_update_cad_model(client: TestClient, db: Session):
    """Test updating CAD model metadata"""
    _, token = create_authenticated_user(client, db)

    # Upload model
    file_obj, _ = create_test_file("model.step")
    upload_response = client.post(
        "/api/files/cad/upload",
        files={"file": ("model.step", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    model_id = upload_response.json()["id"]

    # Update model
    response = client.put(
        f"/api/files/cad/{model_id}?name=Updated Name&description=Updated Description",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated Description"


# ============================================================================
# CAD Model Deletion Tests
# ============================================================================

def test_delete_cad_model(client: TestClient, db: Session):
    """Test deleting CAD model"""
    _, token = create_authenticated_user(client, db)

    # Upload model
    file_obj, _ = create_test_file("model.step")
    upload_response = client.post(
        "/api/files/cad/upload",
        files={"file": ("model.step", file_obj)},
        headers={"Authorization": f"Bearer {token}"}
    )
    model_id = upload_response.json()["id"]

    # Delete model
    response = client.delete(
        f"/api/files/cad/{model_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(
        f"/api/files/cad/{model_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404


# ============================================================================
# File Statistics Tests
# ============================================================================

def test_get_file_stats(client: TestClient, db: Session):
    """Test getting file storage statistics"""
    _, token = create_authenticated_user(client, db)

    # Upload models
    for i in range(2):
        file_obj, _ = create_test_file(f"model{i}.step")
        client.post(
            "/api/files/cad/upload",
            files={"file": (f"model{i}.step", file_obj)},
            headers={"Authorization": f"Bearer {token}"}
        )

    # Get stats
    response = client.get(
        "/api/files/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "total_size_bytes" in data
    assert "file_types" in data
    assert data["total_files"] >= 2


# ============================================================================
# Batch Operations Tests
# ============================================================================

def test_batch_delete_cad_models(client: TestClient, db: Session):
    """Test batch deleting CAD models"""
    _, token = create_authenticated_user(client, db)

    # Upload models
    model_ids = []
    for i in range(3):
        file_obj, _ = create_test_file(f"model{i}.step")
        upload_response = client.post(
            "/api/files/cad/upload",
            files={"file": (f"model{i}.step", file_obj)},
            headers={"Authorization": f"Bearer {token}"}
        )
        model_ids.append(upload_response.json()["id"])

    # Batch delete
    response = client.post(
        "/api/files/cad/batch-delete",
        json={"model_ids": model_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 3


# ============================================================================
# Search Tests
# ============================================================================

def test_search_cad_models(client: TestClient, db: Session):
    """Test searching CAD models"""
    _, token = create_authenticated_user(client, db)

    # Upload models with different names
    client.post(
        "/api/files/cad/upload?name=Bracket Assembly",
        files={"file": ("bracket.step", create_test_file("bracket.step")[0])},
        headers={"Authorization": f"Bearer {token}"}
    )

    client.post(
        "/api/files/cad/upload?name=Gear Assembly",
        files={"file": ("gear.step", create_test_file("gear.step")[0])},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Search for bracket
    response = client.get(
        "/api/files/cad/search?query=Bracket",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any("Bracket" in r["name"] for r in results)


def test_search_by_file_type(client: TestClient, db: Session):
    """Test searching by file type"""
    _, token = create_authenticated_user(client, db)

    # Upload STEP file
    client.post(
        "/api/files/cad/upload",
        files={"file": ("model.step", create_test_file("model.step")[0])},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Search by type
    response = client.get(
        "/api/files/cad/search?query=model&file_type=.step",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    results = response.json()
    assert all(r["file_type"] == ".step" for r in results)
