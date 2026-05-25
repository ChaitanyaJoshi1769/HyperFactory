"""Tests for hardware endpoints"""

import pytest
from decimal import Decimal


@pytest.mark.asyncio
def test_create_material(client):
    """Test creating a material"""
    response = client.post(
        "/api/materials",
        json={
            "name": "Aluminum 6061",
            "density": 2.7,
            "cost_per_kg": "5.50",
            "tensile_strength": 310.0,
            "yield_strength": 275.0,
            "thermal_conductivity": 167.0,
            "machinability_index": 8.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Aluminum 6061"
    assert data["density"] == 2.7


@pytest.mark.asyncio
def test_list_materials(client):
    """Test listing materials"""
    # Create a few materials
    for i in range(3):
        client.post(
            "/api/materials",
            json={
                "name": f"Material {i}",
                "cost_per_kg": "10.00",
            },
        )

    response = client.get("/api/materials")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
def test_get_material(client):
    """Test getting a specific material"""
    # Create a material
    create_response = client.post(
        "/api/materials",
        json={
            "name": "Steel",
            "cost_per_kg": "2.00",
        },
    )
    material_id = create_response.json()["id"]

    # Get the material
    response = client.get(f"/api/materials/{material_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Steel"


@pytest.mark.asyncio
def test_update_material(client):
    """Test updating a material"""
    # Create a material
    create_response = client.post(
        "/api/materials",
        json={
            "name": "Copper",
            "cost_per_kg": "8.00",
        },
    )
    material_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/materials/{material_id}",
        json={
            "name": "Copper (Updated)",
            "cost_per_kg": "9.50",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Copper (Updated)"
    assert data["cost_per_kg"] == "9.50"


@pytest.mark.asyncio
def test_create_hardware_part(client):
    """Test creating a hardware part"""
    response = client.post(
        "/api/hardware-parts",
        json={
            "name": "Engine Bracket",
            "type": "bracket",
            "weight_kg": 0.5,
            "description": "Aluminum engine mounting bracket",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Engine Bracket"
    assert data["type"] == "bracket"
    assert data["weight_kg"] == 0.5


@pytest.mark.asyncio
def test_create_hardware_part_with_tolerances(client):
    """Test creating a hardware part with tolerances"""
    response = client.post(
        "/api/hardware-parts",
        json={
            "name": "Shaft",
            "type": "shaft",
            "weight_kg": 1.2,
            "tolerances": [
                {
                    "dimension": "OD",
                    "nominal_value": 20.0,
                    "upper_tolerance": 20.01,
                    "lower_tolerance": 19.99,
                    "tolerance_type": "bilateral",
                }
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["tolerances"]) == 1
    assert data["tolerances"][0]["dimension"] == "OD"


@pytest.mark.asyncio
def test_add_tolerance_to_part(client):
    """Test adding a tolerance to an existing part"""
    # Create a part first
    create_response = client.post(
        "/api/hardware-parts",
        json={
            "name": "Rod",
            "type": "rod",
            "weight_kg": 0.8,
        },
    )
    part_id = create_response.json()["id"]

    # Add tolerance
    response = client.post(
        f"/api/hardware-parts/{part_id}/tolerances",
        json={
            "dimension": "Length",
            "nominal_value": 100.0,
            "upper_tolerance": 100.2,
            "lower_tolerance": 99.8,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["dimension"] == "Length"


@pytest.mark.asyncio
def test_list_hardware_parts(client):
    """Test listing hardware parts"""
    # Create a few parts
    for i in range(2):
        client.post(
            "/api/hardware-parts",
            json={
                "name": f"Part {i}",
                "type": "bracket",
                "weight_kg": 0.5 + i,
            },
        )

    response = client.get("/api/hardware-parts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
def test_get_hardware_part_not_found(client):
    """Test getting a non-existent hardware part"""
    response = client.get("/api/hardware-parts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
def test_delete_hardware_part(client):
    """Test deleting a hardware part"""
    # Create a part
    create_response = client.post(
        "/api/hardware-parts",
        json={
            "name": "Temporary Part",
            "type": "test",
            "weight_kg": 0.1,
        },
    )
    part_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/hardware-parts/{part_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/hardware-parts/{part_id}")
    assert get_response.status_code == 404
