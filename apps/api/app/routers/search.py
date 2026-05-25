"""Advanced search and filtering router - unified search across all entities"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.db import get_db
from app.models.user import User
from app.models.hardware import HardwarePart, Material, Tolerance, SurfaceFinish
from app.models.supplier import Supplier, SupplierCapability, SupplierQuote
from app.models.factory import FactoryConfig, Machine, ProductionJob
from app.models.cad import CADModel
from app.middleware import get_current_user

router = APIRouter(prefix="/api/search", tags=["search"])


# ============================================================================
# Global Search
# ============================================================================

@router.get("/global")
async def global_search(
    query: str = Query(..., min_length=1, max_length=200),
    entity_types: Optional[str] = Query(None),  # Comma-separated: hardware,suppliers,factories,cad
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Global search across all entities.

    Query Parameters:
    - query: Search term (required)
    - entity_types: Comma-separated entity types to search (hardware, suppliers, factories, cad)
    - skip: Offset for pagination
    - limit: Results per type (max 500)

    Returns mixed results from all searched entities.
    """
    search_term = f"%{query}%"
    entity_types_list = [e.strip() for e in entity_types.split(",")] if entity_types else [
        "hardware", "suppliers", "factories", "cad"
    ]

    results = {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "entity_results": {}
    }

    # Hardware Parts
    if "hardware" in entity_types_list:
        parts = db.query(HardwarePart).filter(
            (HardwarePart.part_number.ilike(search_term)) |
            (HardwarePart.description.ilike(search_term))
        ).offset(skip).limit(limit).all()

        results["entity_results"]["hardware_parts"] = [
            {
                "id": str(part.id),
                "part_number": part.part_number,
                "description": part.description,
                "material": part.material,
                "weight": part.weight,
            }
            for part in parts
        ]

    # Suppliers
    if "suppliers" in entity_types_list:
        suppliers = db.query(Supplier).filter(
            (Supplier.name.ilike(search_term)) |
            (Supplier.contact_email.ilike(search_term))
        ).offset(skip).limit(limit).all()

        results["entity_results"]["suppliers"] = [
            {
                "id": str(supplier.id),
                "name": supplier.name,
                "country": supplier.country,
                "quality_score": supplier.quality_score,
            }
            for supplier in suppliers
        ]

    # Factories
    if "factories" in entity_types_list:
        factories = db.query(FactoryConfig).filter(
            (FactoryConfig.name.ilike(search_term)) |
            (FactoryConfig.location.ilike(search_term))
        ).offset(skip).limit(limit).all()

        results["entity_results"]["factories"] = [
            {
                "id": str(factory.id),
                "name": factory.name,
                "location": factory.location,
                "machine_count": factory.machine_count,
            }
            for factory in factories
        ]

    # CAD Models
    if "cad" in entity_types_list:
        models = db.query(CADModel).filter(
            (CADModel.name.ilike(search_term)) |
            (CADModel.description.ilike(search_term))
        ).offset(skip).limit(limit).all()

        results["entity_results"]["cad_models"] = [
            {
                "id": str(model.id),
                "name": model.name,
                "file_name": model.file_name,
                "file_type": model.file_type,
                "upload_date": model.upload_date.isoformat(),
            }
            for model in models
        ]

    return results


# ============================================================================
# Hardware Search
# ============================================================================

@router.get("/hardware/parts")
async def search_hardware_parts(
    query: str = Query(..., min_length=1),
    material: Optional[str] = Query(None),
    weight_min: Optional[float] = Query(None, ge=0),
    weight_max: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advanced search for hardware parts.

    Query Parameters:
    - query: Search term (part number, description)
    - material: Filter by material
    - weight_min: Minimum weight
    - weight_max: Maximum weight
    """
    search_term = f"%{query}%"
    q = db.query(HardwarePart).filter(
        (HardwarePart.part_number.ilike(search_term)) |
        (HardwarePart.description.ilike(search_term))
    )

    if material:
        q = q.filter(HardwarePart.material.ilike(f"%{material}%"))

    if weight_min is not None:
        q = q.filter(HardwarePart.weight >= weight_min)

    if weight_max is not None:
        q = q.filter(HardwarePart.weight <= weight_max)

    parts = q.offset(skip).limit(limit).all()

    return {
        "query": query,
        "filters": {
            "material": material,
            "weight_range": f"{weight_min}-{weight_max}" if weight_min or weight_max else None,
        },
        "results": [
            {
                "id": str(part.id),
                "part_number": part.part_number,
                "description": part.description,
                "material": part.material,
                "weight": part.weight,
            }
            for part in parts
        ],
    }


# ============================================================================
# Supplier Search
# ============================================================================

@router.get("/suppliers")
async def search_suppliers(
    query: str = Query(..., min_length=1),
    country: Optional[str] = Query(None),
    supplier_type: Optional[str] = Query(None),
    quality_min: Optional[float] = Query(None, ge=0, le=1),
    reliability_min: Optional[float] = Query(None, ge=0, le=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advanced supplier search.

    Query Parameters:
    - query: Search term (name, email, contact)
    - country: Filter by country
    - supplier_type: Filter by type
    - quality_min: Minimum quality score
    - reliability_min: Minimum reliability score
    """
    search_term = f"%{query}%"
    q = db.query(Supplier).filter(
        (Supplier.name.ilike(search_term)) |
        (Supplier.contact_email.ilike(search_term)) |
        (Supplier.contact_person.ilike(search_term))
    )

    if country:
        q = q.filter(Supplier.country.ilike(f"%{country}%"))

    if supplier_type:
        q = q.filter(Supplier.supplier_type.ilike(f"%{supplier_type}%"))

    if quality_min is not None:
        q = q.filter(Supplier.quality_score >= quality_min)

    if reliability_min is not None:
        q = q.filter(Supplier.reliability_score >= reliability_min)

    suppliers = q.offset(skip).limit(limit).all()

    return {
        "query": query,
        "filters": {
            "country": country,
            "supplier_type": supplier_type,
            "quality_score_min": quality_min,
            "reliability_score_min": reliability_min,
        },
        "results": [
            {
                "id": str(supplier.id),
                "name": supplier.name,
                "country": supplier.country,
                "supplier_type": supplier.supplier_type,
                "quality_score": supplier.quality_score,
                "reliability_score": supplier.reliability_score,
                "contact_email": supplier.contact_email,
            }
            for supplier in suppliers
        ],
    }


# ============================================================================
# Factory Search
# ============================================================================

@router.get("/factories")
async def search_factories(
    query: str = Query(..., min_length=1),
    location: Optional[str] = Query(None),
    machine_min: Optional[int] = Query(None, ge=0),
    machine_max: Optional[int] = Query(None, ge=0),
    utilization_min: Optional[float] = Query(None, ge=0, le=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advanced factory search.

    Query Parameters:
    - query: Search term (name, description)
    - location: Filter by location
    - machine_min: Minimum machine count
    - machine_max: Maximum machine count
    - utilization_min: Minimum utilization rate
    """
    search_term = f"%{query}%"
    q = db.query(FactoryConfig).filter(
        (FactoryConfig.name.ilike(search_term)) |
        (Factory.description.ilike(search_term))
    )

    if location:
        q = q.filter(FactoryConfig.location.ilike(f"%{location}%"))

    if machine_min is not None:
        q = q.filter(len(FactoryConfig.machines) >= machine_min)

    if machine_max is not None:
        q = q.filter(len(FactoryConfig.machines) <= machine_max)

    if utilization_min is not None:
        q = q.filter(FactoryConfig.capacity_utilization >= utilization_min)

    factories = q.offset(skip).limit(limit).all()

    return {
        "query": query,
        "filters": {
            "location": location,
            "machine_count_range": f"{machine_min}-{machine_max}" if machine_min or machine_max else None,
            "utilization_min": utilization_min,
        },
        "results": [
            {
                "id": str(factory.id),
                "name": factory.name,
                "location": factory.location,
                "machine_count": factory.machine_count,
                "utilization_rate": factory.utilization_rate,
            }
            for factory in factories
        ],
    }


# ============================================================================
# CAD Model Search
# ============================================================================

@router.get("/cad")
async def search_cad_models(
    query: str = Query(..., min_length=1),
    file_type: Optional[str] = Query(None),
    dfm_score_min: Optional[float] = Query(None, ge=0, le=1),
    uploaded_after: Optional[str] = Query(None),  # ISO datetime
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advanced CAD model search.

    Query Parameters:
    - query: Search term (name, description)
    - file_type: Filter by file type (.step, .iges, etc.)
    - dfm_score_min: Minimum DFM (Design for Manufacturing) score
    - uploaded_after: Filter models uploaded after date (ISO 8601)
    """
    search_term = f"%{query}%"
    q = db.query(CADModel).filter(
        (CADModel.name.ilike(search_term)) |
        (CADModel.description.ilike(search_term))
    )

    if file_type:
        q = q.filter(CADModel.file_type.ilike(f"%{file_type}%"))

    if dfm_score_min is not None:
        # Assuming DFM score would be in analysis table
        pass  # Would need to join with analysis table

    if uploaded_after:
        try:
            upload_date = datetime.fromisoformat(uploaded_after)
            q = q.filter(CADModel.upload_date >= upload_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ISO datetime format")

    models = q.offset(skip).limit(limit).all()

    return {
        "query": query,
        "filters": {
            "file_type": file_type,
            "dfm_score_min": dfm_score_min,
            "uploaded_after": uploaded_after,
        },
        "results": [
            {
                "id": str(model.id),
                "name": model.name,
                "description": model.description,
                "file_type": model.file_type,
                "file_size": model.file_size,
                "upload_date": model.upload_date.isoformat(),
            }
            for model in models
        ],
    }


# ============================================================================
# Production Job Search
# ============================================================================

@router.get("/jobs")
async def search_jobs(
    status: Optional[str] = Query(None),  # queued, in_progress, completed, cancelled
    priority: Optional[str] = Query(None),  # low, medium, high, critical
    machine_id: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),  # ISO datetime
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advanced production job search.

    Query Parameters:
    - status: Filter by status (queued, in_progress, completed, cancelled)
    - priority: Filter by priority (low, medium, high, critical)
    - machine_id: Filter by machine
    - created_after: Filter jobs created after date
    """
    q = db.query(ProductionJob)

    if status:
        q = q.filter(ProductionJob.status == status)

    if priority:
        q = q.filter(ProductionJob.priority == priority)

    if machine_id:
        try:
            machine_uuid = UUID(machine_id)
            q = q.filter(ProductionJob.machine_id == machine_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid machine_id UUID")

    if created_after:
        try:
            created_date = datetime.fromisoformat(created_after)
            q = q.filter(ProductionJob.created_at >= created_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ISO datetime format")

    jobs = q.offset(skip).limit(limit).all()

    return {
        "filters": {
            "status": status,
            "priority": priority,
            "machine_id": machine_id,
            "created_after": created_after,
        },
        "results": [
            {
                "id": str(job.id),
                "part_id": str(job.part_id) if job.part_id else None,
                "machine_id": str(job.machine_id),
                "status": job.status,
                "priority": job.priority,
                "quantity": job.quantity,
                "created_at": job.created_at.isoformat(),
                "start_time": job.start_time.isoformat() if job.start_time else None,
                "completion_time": job.completion_time.isoformat() if job.completion_time else None,
            }
            for job in jobs
        ],
    }


# ============================================================================
# Search Suggestions (Autocomplete)
# ============================================================================

@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=50),
    entity_type: str = Query("all"),  # all, hardware, suppliers, factories, cad, jobs
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get search suggestions/autocomplete for a partial query.

    Query Parameters:
    - query: Partial search term
    - entity_type: Which entity type to suggest from
    - limit: Max suggestions
    """
    search_term = f"{query}%"
    suggestions = []

    if entity_type in ["all", "hardware"]:
        parts = db.query(HardwarePart.part_number).filter(
            HardwarePart.part_number.ilike(search_term)
        ).limit(limit).all()
        suggestions.extend([{"type": "hardware", "value": p[0]} for p in parts])

    if entity_type in ["all", "suppliers"]:
        suppliers = db.query(Supplier.name).filter(
            Supplier.name.ilike(search_term)
        ).limit(limit).all()
        suggestions.extend([{"type": "supplier", "value": s[0]} for s in suppliers])

    if entity_type in ["all", "factories"]:
        factories = db.query(Factory.name).filter(
            Factory.name.ilike(search_term)
        ).limit(limit).all()
        suggestions.extend([{"type": "factory", "value": f[0]} for f in factories])

    if entity_type in ["all", "cad"]:
        models = db.query(CADModel.name).filter(
            CADModel.name.ilike(search_term)
        ).limit(limit).all()
        suggestions.extend([{"type": "cad", "value": m[0]} for m in models])

    return {
        "query": query,
        "suggestions": suggestions[:limit],
    }
