"""Advanced search and filtering tests"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.models.hardware import HardwarePart, Material, Tolerance, SurfaceFinish
from app.models.supplier import Supplier, SupplierCapability, SupplierQuote
from app.models.factory import FactoryConfig, Machine, ProductionJob
from app.models.cad import CADModel
from io import BytesIO


def create_authenticated_user(client: TestClient, db: Session):
    """Helper to create and authenticate a user"""
    user_data = UserCreate(
        username="searchuser",
        email="search@example.com",
        password="SearchPass123",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "searchuser",
            "password": "SearchPass123",
        }
    )
    token = login_response.json()["access_token"]
    return user, token


# ============================================================================
# Global Search Tests
# ============================================================================

def test_global_search_all_entities(client: TestClient, db: Session):
    """Test global search across all entity types"""
    _, token = create_authenticated_user(client, db)

    # Create test hardware
    part = HardwarePart(
        part_number="PART-001",
        description="Test Bearing",
        material="Steel",
        weight=0.5,
    )
    db.add(part)
    db.commit()

    # Create test supplier
    supplier = Supplier(
        name="Test Supplier Co",
        country="USA",
        contact_email="test@supplier.com",
        contact_person="John Doe",
        supplier_type="Component",
        quality_score=0.95,
        reliability_score=0.92,
    )
    db.add(supplier)
    db.commit()

    # Global search
    response = client.get(
        "/api/search/global?query=Test",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "entity_results" in data
    assert data["query"] == "Test"
    assert "timestamp" in data


def test_global_search_with_entity_filter(client: TestClient, db: Session):
    """Test global search with entity type filter"""
    _, token = create_authenticated_user(client, db)

    # Create test data
    part = HardwarePart(
        part_number="BEARING-X1",
        description="Ball Bearing",
        material="Steel",
        weight=0.25,
    )
    db.add(part)
    db.commit()

    # Search only hardware
    response = client.get(
        "/api/search/global?query=Bearing&entity_types=hardware",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "hardware_parts" in data["entity_results"]


def test_global_search_pagination(client: TestClient, db: Session):
    """Test global search with pagination"""
    _, token = create_authenticated_user(client, db)

    # Create multiple parts
    for i in range(5):
        part = HardwarePart(
            part_number=f"PART-{i:03d}",
            description=f"Test Part {i}",
            material="Aluminum",
            weight=0.1 * (i + 1),
        )
        db.add(part)
    db.commit()

    # Search with limit
    response = client.get(
        "/api/search/global?query=Test&limit=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entity_results"]["hardware_parts"]) <= 2


# ============================================================================
# Hardware Part Search Tests
# ============================================================================

def test_search_hardware_parts_by_number(client: TestClient, db: Session):
    """Test searching hardware parts by part number"""
    _, token = create_authenticated_user(client, db)

    # Create test parts
    part1 = HardwarePart(
        part_number="BOLT-M10",
        description="M10 Bolt",
        material="Steel",
        weight=0.05,
    )
    part2 = HardwarePart(
        part_number="WASHER-M10",
        description="M10 Washer",
        material="Steel",
        weight=0.01,
    )
    db.add_all([part1, part2])
    db.commit()

    # Search by part number
    response = client.get(
        "/api/search/hardware/parts?query=BOLT",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
    assert any(p["part_number"] == "BOLT-M10" for p in data["results"])


def test_search_hardware_with_material_filter(client: TestClient, db: Session):
    """Test searching hardware parts with material filter"""
    _, token = create_authenticated_user(client, db)

    # Create parts with different materials
    steel_part = HardwarePart(
        part_number="BOLT-STEEL",
        description="Steel Bolt",
        material="Steel",
        weight=0.1,
    )
    aluminum_part = HardwarePart(
        part_number="BOLT-ALUMINUM",
        description="Aluminum Bolt",
        material="Aluminum",
        weight=0.05,
    )
    db.add_all([steel_part, aluminum_part])
    db.commit()

    # Filter by material
    response = client.get(
        "/api/search/hardware/parts?query=BOLT&material=Steel",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["material"] == "Steel"
    assert all(p["material"] == "Steel" for p in data["results"])


def test_search_hardware_with_weight_range(client: TestClient, db: Session):
    """Test searching hardware parts with weight filters"""
    _, token = create_authenticated_user(client, db)

    # Create parts with different weights
    light_part = HardwarePart(
        part_number="LIGHT-PART",
        description="Light Part",
        material="Aluminum",
        weight=0.01,
    )
    heavy_part = HardwarePart(
        part_number="HEAVY-PART",
        description="Heavy Part",
        material="Steel",
        weight=1.5,
    )
    db.add_all([light_part, heavy_part])
    db.commit()

    # Filter by weight
    response = client.get(
        "/api/search/hardware/parts?query=PART&weight_min=0.5&weight_max=2.0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(0.5 <= p["weight"] <= 2.0 for p in data["results"])


# ============================================================================
# Supplier Search Tests
# ============================================================================

def test_search_suppliers_by_name(client: TestClient, db: Session):
    """Test searching suppliers by name"""
    _, token = create_authenticated_user(client, db)

    supplier = Supplier(
        name="Global Manufacturing Corp",
        country="Germany",
        contact_email="info@global-mfg.com",
        contact_person="Klaus Mueller",
        supplier_type="Manufacturer",
        quality_score=0.96,
        reliability_score=0.94,
    )
    db.add(supplier)
    db.commit()

    response = client.get(
        "/api/search/suppliers?query=Global",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
    assert any(s["name"] == "Global Manufacturing Corp" for s in data["results"])


def test_search_suppliers_by_country(client: TestClient, db: Session):
    """Test searching suppliers with country filter"""
    _, token = create_authenticated_user(client, db)

    suppliers = [
        Supplier(
            name="US Supplier A",
            country="USA",
            contact_email="a@us.com",
            contact_person="John",
            supplier_type="Component",
            quality_score=0.90,
            reliability_score=0.88,
        ),
        Supplier(
            name="Japan Supplier B",
            country="Japan",
            contact_email="b@japan.com",
            contact_person="Takeshi",
            supplier_type="Component",
            quality_score=0.95,
            reliability_score=0.93,
        ),
    ]
    db.add_all(suppliers)
    db.commit()

    response = client.get(
        "/api/search/suppliers?query=Supplier&country=USA",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(s["country"] == "USA" for s in data["results"])


def test_search_suppliers_by_quality_score(client: TestClient, db: Session):
    """Test searching suppliers with quality score filter"""
    _, token = create_authenticated_user(client, db)

    supplier = Supplier(
        name="Premium Supplier",
        country="Switzerland",
        contact_email="premium@supplier.ch",
        contact_person="Hans",
        supplier_type="Premium",
        quality_score=0.98,
        reliability_score=0.97,
    )
    db.add(supplier)
    db.commit()

    response = client.get(
        "/api/search/suppliers?query=Supplier&quality_min=0.95",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(s["quality_score"] >= 0.95 for s in data["results"])


# ============================================================================
# Factory Search Tests
# ============================================================================

def test_search_factories_by_name(client: TestClient, db: Session):
    """Test searching factories by name"""
    _, token = create_authenticated_user(client, db)

    factory = FactoryConfig(
        name="Advanced Manufacturing Plant",
        location="Shanghai, China",
        # machine_count=50,
        capacity_utilization=0.85,
    )
    db.add(factory)
    db.commit()

    response = client.get(
        "/api/search/factories?query=Advanced",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0


def test_search_factories_by_location(client: TestClient, db: Session):
    """Test searching factories with location filter"""
    _, token = create_authenticated_user(client, db)

    factories = [
        FactoryConfig(
            name="Factory Europe",
            location="Germany",
            # machine_count=30,
            capacity_utilization=0.78,
        ),
        FactoryConfig(
            name="Factory Asia",
            location="Vietnam",
            # machine_count=45,
            capacity_utilization=0.82,
        ),
    ]
    db.add_all(factories)
    db.commit()

    response = client.get(
        "/api/search/factories?query=Factory&location=Germany",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all("Germany" in f["location"] for f in data["results"])


def test_search_factories_by_machine_count(client: TestClient, db: Session):
    """Test searching factories with machine count filter"""
    _, token = create_authenticated_user(client, db)

    factory = FactoryConfig(
        name="Large Factory",
        location="Texas, USA",
        # machine_count=100,
        capacity_utilization=0.90,
    )
    db.add(factory)
    db.commit()

    response = client.get(
        "/api/search/factories?query=Factory&machine_min=50",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(f["machine_count"] >= 50 for f in data["results"])


def test_search_factories_by_utilization(client: TestClient, db: Session):
    """Test searching factories with utilization filter"""
    _, token = create_authenticated_user(client, db)

    factory = FactoryConfig(
        name="Busy Factory",
        location="Michigan, USA",
        # machine_count=60,
        capacity_utilization=0.92,
    )
    db.add(factory)
    db.commit()

    response = client.get(
        "/api/search/factories?query=Factory&utilization_min=0.90",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(f["utilization_rate"] >= 0.90 for f in data["results"])


# ============================================================================
# CAD Model Search Tests
# ============================================================================

def test_search_cad_models(client: TestClient, db: Session):
    """Test searching CAD models"""
    _, token = create_authenticated_user(client, db)

    model = CADModel(
        name="Engine Block Assembly",
        description="V8 engine block with ports",
        file_name="engine_block.step",
        file_type=".step",
        file_size=2500000,
        file_hash="abcd1234",
        uploaded_by=None,
    )
    db.add(model)
    db.commit()

    response = client.get(
        "/api/search/cad?query=Engine",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0


def test_search_cad_by_file_type(client: TestClient, db: Session):
    """Test searching CAD models with file type filter"""
    _, token = create_authenticated_user(client, db)

    models = [
        CADModel(
            name="Part A",
            description="STEP format model",
            file_name="part_a.step",
            file_type=".step",
            file_size=1000000,
            file_hash="hash1",
            uploaded_by=None,
        ),
        CADModel(
            name="Part B",
            description="IGES format model",
            file_name="part_b.iges",
            file_type=".iges",
            file_size=1500000,
            file_hash="hash2",
            uploaded_by=None,
        ),
    ]
    db.add_all(models)
    db.commit()

    response = client.get(
        "/api/search/cad?query=Part&file_type=.step",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(m["file_type"] == ".step" for m in data["results"])


def test_search_cad_with_invalid_date(client: TestClient, db: Session):
    """Test CAD search with invalid ISO datetime"""
    _, token = create_authenticated_user(client, db)

    response = client.get(
        "/api/search/cad?query=model&uploaded_after=invalid-date",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Invalid ISO datetime format" in response.json()["detail"]


# ============================================================================
# Production Job Search Tests
# ============================================================================

def test_search_jobs_by_status(client: TestClient, db: Session):
    """Test searching production jobs by status"""
    _, token = create_authenticated_user(client, db)

    machine = Machine(
        name="Test Machine",
        type="CNC",
        status="operational",
    )
    db.add(machine)
    db.commit()

    job = ProductionJob(
        machine_id=machine.id,
        status="in_progress",
        priority="high",
        quantity=100,
    )
    db.add(job)
    db.commit()

    response = client.get(
        "/api/search/jobs?status=in_progress",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(j["status"] == "in_progress" for j in data["results"])


def test_search_jobs_by_priority(client: TestClient, db: Session):
    """Test searching production jobs by priority"""
    _, token = create_authenticated_user(client, db)

    machine = Machine(
        name="Critical Machine",
        type="CNC",
        status="operational",
    )
    db.add(machine)
    db.commit()

    job = ProductionJob(
        machine_id=machine.id,
        status="queued",
        priority="critical",
        quantity=50,
    )
    db.add(job)
    db.commit()

    response = client.get(
        "/api/search/jobs?priority=critical",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(j["priority"] == "critical" for j in data["results"])


def test_search_jobs_by_machine(client: TestClient, db: Session):
    """Test searching production jobs by machine ID"""
    _, token = create_authenticated_user(client, db)

    machine = Machine(
        name="Specific Machine",
        type="CNC",
        status="operational",
    )
    db.add(machine)
    db.commit()

    job = ProductionJob(
        machine_id=machine.id,
        status="completed",
        priority="medium",
        quantity=200,
    )
    db.add(job)
    db.commit()

    response = client.get(
        f"/api/search/jobs?machine_id={machine.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(str(j["machine_id"]) == str(machine.id) for j in data["results"])


def test_search_jobs_with_invalid_machine_id(client: TestClient, db: Session):
    """Test job search with invalid machine UUID"""
    _, token = create_authenticated_user(client, db)

    response = client.get(
        "/api/search/jobs?machine_id=not-a-uuid",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Invalid machine_id UUID" in response.json()["detail"]


# ============================================================================
# Search Suggestions/Autocomplete Tests
# ============================================================================

def test_get_suggestions_for_hardware(client: TestClient, db: Session):
    """Test getting autocomplete suggestions for hardware"""
    _, token = create_authenticated_user(client, db)

    parts = [
        HardwarePart(
            part_number="BOLT-M6",
            description="M6 Bolt",
            material="Steel",
            weight=0.02,
        ),
        HardwarePart(
            part_number="BOLT-M8",
            description="M8 Bolt",
            material="Steel",
            weight=0.03,
        ),
        HardwarePart(
            part_number="BOLT-M10",
            description="M10 Bolt",
            material="Steel",
            weight=0.05,
        ),
    ]
    db.add_all(parts)
    db.commit()

    response = client.get(
        "/api/search/suggestions?query=BOLT&entity_type=hardware",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) > 0
    assert all(s["type"] == "hardware" for s in data["suggestions"])


def test_get_suggestions_for_suppliers(client: TestClient, db: Session):
    """Test getting autocomplete suggestions for suppliers"""
    _, token = create_authenticated_user(client, db)

    suppliers = [
        Supplier(
            name="Precision Parts Inc",
            country="USA",
            contact_email="info@precision.com",
            contact_person="Bob",
            supplier_type="Component",
            quality_score=0.93,
            reliability_score=0.91,
        ),
        Supplier(
            name="Precision Manufacturing Ltd",
            country="UK",
            contact_email="info@precisionmfg.uk",
            contact_person="Alice",
            supplier_type="Manufacturer",
            quality_score=0.94,
            reliability_score=0.92,
        ),
    ]
    db.add_all(suppliers)
    db.commit()

    response = client.get(
        "/api/search/suggestions?query=Precision&entity_type=suppliers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) > 0
    assert all(s["type"] == "supplier" for s in data["suggestions"])


def test_get_suggestions_all_types(client: TestClient, db: Session):
    """Test getting suggestions for all entity types"""
    _, token = create_authenticated_user(client, db)

    # Create test data
    part = HardwarePart(
        part_number="TEST-001",
        description="Test Part",
        material="Steel",
        weight=0.1,
    )
    supplier = Supplier(
        name="Test Supplier",
        country="USA",
        contact_email="test@test.com",
        contact_person="Test",
        supplier_type="Component",
        quality_score=0.90,
        reliability_score=0.88,
    )
    factory = FactoryConfig(
        name="Test Factory",
        location="USA",
        # machine_count=20,
        capacity_utilization=0.80,
    )
    model = CADModel(
        name="Test Model",
        description="Test CAD Model",
        file_name="test.step",
        file_type=".step",
        file_size=1000000,
        file_hash="testhash",
        uploaded_by=None,
    )
    db.add_all([part, supplier, factory, model])
    db.commit()

    response = client.get(
        "/api/search/suggestions?query=Test&entity_type=all",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) > 0


def test_suggestions_limit(client: TestClient, db: Session):
    """Test suggestions with limit parameter"""
    _, token = create_authenticated_user(client, db)

    # Create many suppliers
    for i in range(20):
        supplier = Supplier(
            name=f"Supplier {i:02d}",
            country="USA",
            contact_email=f"supplier{i}@test.com",
            contact_person=f"Contact {i}",
            supplier_type="Component",
            quality_score=0.90,
            reliability_score=0.88,
        )
        db.add(supplier)
    db.commit()

    response = client.get(
        "/api/search/suggestions?query=Supplier&entity_type=suppliers&limit=5",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) <= 5


# ============================================================================
# Authentication Tests
# ============================================================================

def test_search_requires_authentication(client: TestClient, db: Session):
    """Test that search endpoints require authentication"""
    response = client.get("/api/search/global?query=test")
    assert response.status_code == 403


def test_supplier_search_requires_authentication(client: TestClient, db: Session):
    """Test that supplier search requires authentication"""
    response = client.get("/api/search/suppliers?query=test")
    assert response.status_code == 403


def test_hardware_search_requires_authentication(client: TestClient, db: Session):
    """Test that hardware search requires authentication"""
    response = client.get("/api/search/hardware/parts?query=test")
    assert response.status_code == 403


# ============================================================================
# Edge Cases and Validation Tests
# ============================================================================

def test_global_search_min_query_length(client: TestClient, db: Session):
    """Test global search with query below minimum length"""
    _, token = create_authenticated_user(client, db)

    response = client.get(
        "/api/search/global?query=",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422  # Validation error


def test_search_empty_results(client: TestClient, db: Session):
    """Test search returning empty results"""
    _, token = create_authenticated_user(client, db)

    response = client.get(
        "/api/search/hardware/parts?query=NONEXISTENT12345",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0


def test_search_case_insensitive(client: TestClient, db: Session):
    """Test that search is case-insensitive"""
    _, token = create_authenticated_user(client, db)

    supplier = Supplier(
        name="TestSupplier",
        country="USA",
        contact_email="test@test.com",
        contact_person="Test",
        supplier_type="Component",
        quality_score=0.90,
        reliability_score=0.88,
    )
    db.add(supplier)
    db.commit()

    # Test lowercase
    response1 = client.get(
        "/api/search/suppliers?query=testsupplier",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 200

    # Test uppercase
    response2 = client.get(
        "/api/search/suppliers?query=TESTSUPPLIER",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 200


def test_search_with_special_characters(client: TestClient, db: Session):
    """Test search with special characters in query"""
    _, token = create_authenticated_user(client, db)

    # This should handle SQL injection attempts gracefully
    response = client.get(
        "/api/search/hardware/parts?query=test'; DROP TABLE--",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200  # Should return empty, not error
    data = response.json()
    assert len(data["results"]) == 0
