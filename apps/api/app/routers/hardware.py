"""Hardware parts router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db import get_db
from app.models.hardware import HardwarePart, Material, Tolerance, SurfaceFinish
from app.schemas.hardware import (
    HardwarePartCreate,
    HardwarePartRead,
    HardwarePartUpdate,
    MaterialCreate,
    MaterialRead,
    ToleranceCreate,
    ToleranceRead,
    SurfaceFinishCreate,
    SurfaceFinishRead,
)
from app.event_publisher import EventPublisher

router = APIRouter(prefix="/api", tags=["hardware"])


# ============================================================================
# Material Endpoints
# ============================================================================

@router.post("/materials", response_model=MaterialRead, status_code=201)
def create_material(material: MaterialCreate, db: Session = Depends(get_db)):
    """Create a new material"""
    db_material = Material(**material.dict())
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material


@router.get("/materials", response_model=List[MaterialRead])
def list_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all materials with pagination"""
    materials = db.query(Material).offset(skip).limit(limit).all()
    return materials


@router.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(material_id: UUID, db: Session = Depends(get_db)):
    """Get a specific material"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.put("/materials/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: UUID,
    material_update: MaterialCreate,
    db: Session = Depends(get_db)
):
    """Update a material"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    update_data = material_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(material, key, value)

    db.commit()
    db.refresh(material)
    return material


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(material_id: UUID, db: Session = Depends(get_db)):
    """Delete a material"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    db.delete(material)
    db.commit()


# ============================================================================
# Hardware Part Endpoints
# ============================================================================

@router.post("/hardware-parts", response_model=HardwarePartRead, status_code=201)
def create_hardware_part(part: HardwarePartCreate, db: Session = Depends(get_db)):
    """Create a new hardware part"""
    # Create the part
    part_data = part.dict(exclude={'tolerances', 'surface_finishes'})
    db_part = HardwarePart(**part_data)
    db.add(db_part)
    db.flush()

    # Add tolerances if provided
    if part.tolerances:
        for tol in part.tolerances:
            db_tolerance = Tolerance(**tol.dict(), hardware_part_id=db_part.id)
            db.add(db_tolerance)

    # Add surface finishes if provided
    if part.surface_finishes:
        for sf in part.surface_finishes:
            db_finish = SurfaceFinish(**sf.dict(), hardware_part_id=db_part.id)
            db.add(db_finish)

    db.commit()
    db.refresh(db_part)

    # Publish webhook event
    EventPublisher.part_created(
        db=db,
        user_id="system",  # TODO: Get from auth context
        part_id=str(db_part.id),
        name=db_part.name,
        part_type=db_part.type or ""
    )

    return db_part


@router.get("/hardware-parts", response_model=List[HardwarePartRead])
def list_hardware_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    part_type: str = Query(None),
    db: Session = Depends(get_db)
):
    """List hardware parts with optional filtering"""
    query = db.query(HardwarePart)

    if part_type:
        query = query.filter(HardwarePart.type == part_type)

    parts = query.offset(skip).limit(limit).all()
    return parts


@router.get("/hardware-parts/{part_id}", response_model=HardwarePartRead)
def get_hardware_part(part_id: UUID, db: Session = Depends(get_db)):
    """Get a specific hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")
    return part


@router.patch("/hardware-parts/{part_id}", response_model=HardwarePartRead)
def update_hardware_part(
    part_id: UUID,
    part_update: HardwarePartUpdate,
    db: Session = Depends(get_db)
):
    """Update a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    update_data = part_update.dict(exclude_unset=True)
    changes = {k: v for k, v in update_data.items()}

    for key, value in update_data.items():
        setattr(part, key, value)

    db.commit()
    db.refresh(part)

    # Publish webhook event
    if changes:
        EventPublisher.part_updated(
            db=db,
            user_id="system",  # TODO: Get from auth context
            part_id=str(part.id),
            name=part.name,
            changes=changes
        )

    return part


@router.delete("/hardware-parts/{part_id}", status_code=204)
def delete_hardware_part(part_id: UUID, db: Session = Depends(get_db)):
    """Delete a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    part_name = part.name

    db.delete(part)
    db.commit()

    # Publish webhook event
    EventPublisher.part_deleted(
        db=db,
        user_id="system",  # TODO: Get from auth context
        part_id=str(part_id),
        name=part_name
    )


# ============================================================================
# Tolerance Endpoints
# ============================================================================

@router.post("/hardware-parts/{part_id}/tolerances", response_model=ToleranceRead, status_code=201)
def add_tolerance(
    part_id: UUID,
    tolerance: ToleranceCreate,
    db: Session = Depends(get_db)
):
    """Add a tolerance to a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    db_tolerance = Tolerance(**tolerance.dict(), hardware_part_id=part_id)
    db.add(db_tolerance)
    db.commit()
    db.refresh(db_tolerance)
    return db_tolerance


@router.get("/hardware-parts/{part_id}/tolerances", response_model=List[ToleranceRead])
def list_tolerances(part_id: UUID, db: Session = Depends(get_db)):
    """List tolerances for a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    return part.tolerances


@router.delete("/tolerances/{tolerance_id}", status_code=204)
def delete_tolerance(tolerance_id: UUID, db: Session = Depends(get_db)):
    """Delete a tolerance"""
    tolerance = db.query(Tolerance).filter(Tolerance.id == tolerance_id).first()
    if not tolerance:
        raise HTTPException(status_code=404, detail="Tolerance not found")

    db.delete(tolerance)
    db.commit()


# ============================================================================
# Surface Finish Endpoints
# ============================================================================

@router.post("/hardware-parts/{part_id}/surface-finishes", response_model=SurfaceFinishRead, status_code=201)
def add_surface_finish(
    part_id: UUID,
    finish: SurfaceFinishCreate,
    db: Session = Depends(get_db)
):
    """Add a surface finish to a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    db_finish = SurfaceFinish(**finish.dict(), hardware_part_id=part_id)
    db.add(db_finish)
    db.commit()
    db.refresh(db_finish)
    return db_finish


@router.get("/hardware-parts/{part_id}/surface-finishes", response_model=List[SurfaceFinishRead])
def list_surface_finishes(part_id: UUID, db: Session = Depends(get_db)):
    """List surface finishes for a hardware part"""
    part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Hardware part not found")

    return part.surface_finishes


@router.delete("/surface-finishes/{finish_id}", status_code=204)
def delete_surface_finish(finish_id: UUID, db: Session = Depends(get_db)):
    """Delete a surface finish"""
    finish = db.query(SurfaceFinish).filter(SurfaceFinish.id == finish_id).first()
    if not finish:
        raise HTTPException(status_code=404, detail="Surface finish not found")

    db.delete(finish)
    db.commit()
