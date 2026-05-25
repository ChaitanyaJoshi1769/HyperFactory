# HyperFactory API Documentation

## Overview

The HyperFactory API is a comprehensive REST API for manufacturing orchestration, design analysis, and production management. Built with FastAPI and SQLAlchemy, it provides endpoints for managing hardware parts, suppliers, factory operations, and CAD analysis.

**API Version:** 0.2.0  
**Base URL:** `http://localhost:8000`

## Quick Start

### Running the API

```bash
cd apps/api
pip install -r requirements.txt
python main.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Health Check

```bash
curl http://localhost:8000/health
```

## Core Entities

### 1. Hardware Parts

Hardware parts represent physical components with specifications, tolerances, and surface finishes.

#### Create Hardware Part

```bash
POST /api/hardware-parts
Content-Type: application/json

{
  "name": "Engine Bracket",
  "type": "bracket",
  "weight_kg": 0.5,
  "description": "Aluminum mounting bracket",
  "revision": "A1",
  "estimated_cost": "12.50",
  "estimated_lead_time_days": 5,
  "tolerances": [
    {
      "dimension": "Length",
      "nominal_value": 100.0,
      "upper_tolerance": 100.2,
      "lower_tolerance": 99.8,
      "tolerance_type": "bilateral"
    }
  ],
  "surface_finishes": [
    {
      "name": "Anodized",
      "roughness_ra": 1.6,
      "process": "Type II Anodizing",
      "cost_multiplier": 1.2
    }
  ]
}
```

**Response:** 201 Created
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Engine Bracket",
  "type": "bracket",
  "weight_kg": 0.5,
  "description": "Aluminum mounting bracket",
  "revision": "A1",
  "estimated_cost": "12.50",
  "estimated_lead_time_days": 5,
  "created_at": "2026-05-25T12:00:00",
  "updated_at": "2026-05-25T12:00:00",
  "tolerances": [...],
  "surface_finishes": [...]
}
```

#### List Hardware Parts

```bash
GET /api/hardware-parts?skip=0&limit=10&part_type=bracket
```

**Query Parameters:**
- `skip` (int): Skip N records (default: 0)
- `limit` (int): Return N records (default: 10, max: 100)
- `part_type` (string): Filter by part type

#### Get Hardware Part

```bash
GET /api/hardware-parts/{part_id}
```

#### Update Hardware Part

```bash
PATCH /api/hardware-parts/{part_id}
Content-Type: application/json

{
  "name": "Engine Bracket v2",
  "weight_kg": 0.48
}
```

#### Delete Hardware Part

```bash
DELETE /api/hardware-parts/{part_id}
```

### 2. Materials

Materials define raw material properties and costs.

#### Create Material

```bash
POST /api/materials
Content-Type: application/json

{
  "name": "Aluminum 6061",
  "density": 2.7,
  "cost_per_kg": "5.50",
  "tensile_strength": 310.0,
  "yield_strength": 275.0,
  "thermal_conductivity": 167.0,
  "machinability_index": 8.0
}
```

### 3. Suppliers

Suppliers are partners for manufacturing capabilities and sourcing.

#### Create Supplier

```bash
POST /api/suppliers
Content-Type: application/json

{
  "name": "TechMfg Inc",
  "type": "cnc_shop",
  "country": "USA",
  "region": "California",
  "city": "San Jose",
  "contact_email": "sales@techmfg.com",
  "contact_phone": "+1-408-555-0123",
  "quality_score": 85,
  "reliability_score": 90,
  "cost_competitiveness_score": 75,
  "on_time_delivery_rate": 92.5,
  "defect_rate": 1.2,
  "minimum_order_value": "500.00",
  "certifications": ["ISO-9001", "AS9100"],
  "capabilities": [
    {
      "name": "5-Axis Machining",
      "type": "cnc",
      "process": "milling",
      "min_order_quantity": 1,
      "max_annual_capacity": 50000.0,
      "lead_time_standard_days": 7,
      "lead_time_expedited_days": 3,
      "cost_per_unit_base": "15.00",
      "precision_capability_microns": 2.5,
      "material_capabilities": ["aluminum", "steel", "titanium"],
      "certifications": ["AS9100"]
    }
  ]
}
```

#### List Suppliers

```bash
GET /api/suppliers?country=USA&supplier_type=cnc_shop&skip=0&limit=10
```

#### Get Supplier

```bash
GET /api/suppliers/{supplier_id}
```

#### Create Supplier Quote

```bash
POST /api/quotes
Content-Type: application/json

{
  "supplier_id": "550e8400-e29b-41d4-a716-446655440000",
  "part_id": "550e8400-e29b-41d4-a716-446655440001",
  "quantity": 100,
  "unit_price": "15.50",
  "total_price": "1550.00",
  "lead_time_days": 7,
  "minimum_order_quantity": 50,
  "volume_available": 5000.0,
  "expiration_date": "2026-06-30T23:59:59"
}
```

#### Get Best Quote for Part

```bash
GET /api/quotes?part_id={part_id}
```

### 4. Factory Operations

Manage factory configuration, machines, and production jobs.

#### Create Factory

```bash
POST /api/factories
Content-Type: application/json

{
  "name": "Silicon Valley Factory",
  "location": "San Jose, CA",
  "country": "USA",
  "region": "California",
  "status": "operational",
  "capacity_utilization": 75.0,
  "power_consumption_kwh": 5000.0,
  "production_efficiency": 85.0,
  "defect_rate": 1.5,
  "average_lead_time_days": 5,
  "throughput_parts_per_day": 10000
}
```

#### Add Machine to Factory

```bash
POST /api/factories/{factory_id}/machines
Content-Type: application/json

{
  "name": "CNC-5Axis-001",
  "type": "cnc",
  "process": "milling",
  "location": "Building A, Floor 2",
  "status": "idle",
  "capacity_per_hour": 10.0,
  "power_consumption_kw": 15.0,
  "precision_microns": 2.5,
  "material_compatibility": ["aluminum", "steel", "titanium"],
  "certifications": ["AS9100"],
  "last_maintenance": "2026-05-20T10:00:00"
}
```

#### Create Production Job

```bash
POST /api/production-jobs
Content-Type: application/json

{
  "part_id": "550e8400-e29b-41d4-a716-446655440000",
  "machine_id": "550e8400-e29b-41d4-a716-446655440001",
  "quantity": 100,
  "priority": "high",
  "status": "queued",
  "estimated_duration_minutes": 240,
  "estimated_cost": "1500.00"
}
```

#### Job Status Transitions

```bash
# Start a job
POST /api/production-jobs/{job_id}/start

# Complete a job
POST /api/production-jobs/{job_id}/complete

# Cancel a job
POST /api/production-jobs/{job_id}/cancel
```

### 5. CAD Models and Analysis

Manage CAD files and DFM analysis.

#### Create CAD Model

```bash
POST /api/cad-models
Content-Type: application/json

{
  "name": "Bracket_v1.stp",
  "format": "stp",
  "file_url": "https://storage.example.com/models/bracket_v1.stp",
  "file_hash": "sha256:abc123...",
  "file_size_bytes": 524288,
  "volume_cubic_mm": 12500.0,
  "surface_area_mm2": 8500.0,
  "part_count": 1,
  "assembly_count": 0,
  "hardware_part_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Create CAD Analysis

```bash
POST /api/cad-analyses
Content-Type: application/json

{
  "cad_model_id": "550e8400-e29b-41d4-a716-446655440000",
  "hardware_part_id": "550e8400-e29b-41d4-a716-446655440001",
  "analysis_type": "dfm",
  "manufacturability_score": 82,
  "has_issues": false,
  "dfm_score": 85,
  "estimated_machining_time_minutes": 45,
  "estimated_cost": "120.00",
  "estimated_lead_time_days": 3,
  "features": [
    {
      "type": "pocket",
      "depth_mm": 5.0,
      "length_mm": 20.0,
      "width_mm": 15.0
    }
  ],
  "issues": [],
  "recommendations": [
    "Consider adding fillet to sharp edges",
    "Wall thickness acceptable at 2mm minimum"
  ]
}
```

#### Analyze CAD Model

```bash
POST /api/cad-models/{model_id}/analyze?analysis_type=dfm
```

## Error Handling

All errors follow a consistent JSON format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "detail": "1 validation error(s)",
    "status": 422,
    "timestamp": "2026-05-25T12:00:00.000000",
    "validation_errors": [
      {
        "field": "weight_kg",
        "message": "ensure this value is greater than 0",
        "type": "value_error.number.not_gt"
      }
    ]
  }
}
```

### Error Codes

- `VALIDATION_ERROR` (422): Input validation failed
- `RESOURCE_NOT_FOUND` (404): Resource does not exist
- `CONFLICT_ERROR` (409): Resource conflict (e.g., already exists)
- `UNAUTHORIZED` (401): Authentication required
- `FORBIDDEN` (403): Insufficient permissions
- `DATABASE_ERROR` (500): Database operation failed
- `INTERNAL_SERVER_ERROR` (500): Unexpected server error

## Pagination

List endpoints support pagination:

```bash
GET /api/hardware-parts?skip=20&limit=10
```

- `skip`: Number of records to skip (default: 0)
- `limit`: Number of records to return (default: 10, max: 100)

## Filtering

Many list endpoints support filtering:

```bash
# Filter by type
GET /api/hardware-parts?part_type=bracket

# Filter by status
GET /api/production-jobs?status=in_progress

# Filter by multiple criteria
GET /api/suppliers?country=USA&supplier_type=cnc_shop
```

## Authentication (Future)

Authentication support is planned for Phase 3. Currently, all endpoints are public.

## Rate Limiting (Future)

Rate limiting will be implemented in Phase 3.

## Testing

Run tests with pytest:

```bash
pip install pytest pytest-asyncio
pytest tests/
```

## OpenAPI Specification

The complete OpenAPI specification is available at:
- http://localhost:8000/openapi.json

This can be imported into tools like Postman or Swagger Editor for API testing.

## Support

For issues or questions, please refer to the main HyperFactory documentation or contact the development team.
