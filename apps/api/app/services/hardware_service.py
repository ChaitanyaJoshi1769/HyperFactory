"""Hardware service - business logic for hardware parts"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.models.hardware import HardwarePart, Material, Tolerance, SurfaceFinish
from app.schemas.hardware import (
    HardwarePartCreate,
    HardwarePartUpdate,
    MaterialCreate,
)


class HardwareService:
    """Service layer for hardware parts management"""

    @staticmethod
    def create_material(db: Session, material: MaterialCreate) -> Material:
        """Create a new material"""
        db_material = Material(**material.dict())
        db.add(db_material)
        db.commit()
        db.refresh(db_material)
        return db_material

    @staticmethod
    def get_material(db: Session, material_id: UUID) -> Optional[Material]:
        """Get material by ID"""
        return db.query(Material).filter(Material.id == material_id).first()

    @staticmethod
    def list_materials(db: Session, skip: int = 0, limit: int = 10) -> List[Material]:
        """List all materials with pagination"""
        return db.query(Material).offset(skip).limit(limit).all()

    @staticmethod
    def update_material(db: Session, material_id: UUID, update_data: MaterialCreate) -> Optional[Material]:
        """Update a material"""
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(material, key, value)

        db.commit()
        db.refresh(material)
        return material

    @staticmethod
    def delete_material(db: Session, material_id: UUID) -> bool:
        """Delete a material"""
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return False

        db.delete(material)
        db.commit()
        return True

    # ============================================================================
    # Hardware Part Management
    # ============================================================================

    @staticmethod
    def create_hardware_part(db: Session, part: HardwarePartCreate) -> HardwarePart:
        """Create a new hardware part with optional tolerances and surface finishes"""
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
        return db_part

    @staticmethod
    def get_hardware_part(db: Session, part_id: UUID) -> Optional[HardwarePart]:
        """Get hardware part by ID"""
        return db.query(HardwarePart).filter(HardwarePart.id == part_id).first()

    @staticmethod
    def list_hardware_parts(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        part_type: Optional[str] = None,
    ) -> List[HardwarePart]:
        """List hardware parts with optional filtering"""
        query = db.query(HardwarePart)

        if part_type:
            query = query.filter(HardwarePart.type == part_type)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_hardware_part(
        db: Session,
        part_id: UUID,
        update_data: HardwarePartUpdate
    ) -> Optional[HardwarePart]:
        """Update a hardware part"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(part, key, value)

        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def delete_hardware_part(db: Session, part_id: UUID) -> bool:
        """Delete a hardware part (cascades to tolerances and surface finishes)"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part:
            return False

        db.delete(part)
        db.commit()
        return True

    @staticmethod
    def calculate_part_weight_category(weight_kg: float) -> str:
        """Calculate weight category for a part"""
        if weight_kg < 0.1:
            return "micro"
        elif weight_kg < 1:
            return "light"
        elif weight_kg < 10:
            return "medium"
        elif weight_kg < 100:
            return "heavy"
        else:
            return "ultra_heavy"

    @staticmethod
    def estimate_cost_variance(
        db: Session,
        part_id: UUID,
        target_cost: float
    ) -> float:
        """Calculate cost variance vs similar parts"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part or not part.estimated_cost:
            return 0.0

        # Get similar parts by type
        similar_parts = db.query(HardwarePart).filter(
            HardwarePart.type == part.type,
            HardwarePart.id != part_id,
            HardwarePart.estimated_cost.isnot(None)
        ).all()

        if not similar_parts:
            return 0.0

        avg_cost = sum(p.estimated_cost for p in similar_parts) / len(similar_parts)
        variance = ((float(part.estimated_cost) - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
        return variance

    # ============================================================================
    # Tolerance Management
    # ============================================================================

    @staticmethod
    def add_tolerance(db: Session, part_id: UUID, tolerance_data: dict) -> Optional[Tolerance]:
        """Add tolerance to a part"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part:
            return None

        db_tolerance = Tolerance(**tolerance_data, hardware_part_id=part_id)
        db.add(db_tolerance)
        db.commit()
        db.refresh(db_tolerance)
        return db_tolerance

    @staticmethod
    def list_tolerances(db: Session, part_id: UUID) -> List[Tolerance]:
        """List tolerances for a part"""
        return db.query(Tolerance).filter(Tolerance.hardware_part_id == part_id).all()

    @staticmethod
    def delete_tolerance(db: Session, tolerance_id: UUID) -> bool:
        """Delete a tolerance"""
        tolerance = db.query(Tolerance).filter(Tolerance.id == tolerance_id).first()
        if not tolerance:
            return False

        db.delete(tolerance)
        db.commit()
        return True

    @staticmethod
    def validate_tolerance_stack(db: Session, part_id: UUID) -> dict:
        """Validate tolerance stack for a part"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part:
            return {"valid": False, "error": "Part not found"}

        tolerances = part.tolerances
        if not tolerances:
            return {"valid": True, "count": 0}

        # Check for conflicts
        conflicts = []
        for tol in tolerances:
            if tol.upper_tolerance <= tol.lower_tolerance:
                conflicts.append(f"Tolerance {tol.dimension}: upper <= lower")

        return {
            "valid": len(conflicts) == 0,
            "count": len(tolerances),
            "conflicts": conflicts
        }

    # ============================================================================
    # Surface Finish Management
    # ============================================================================

    @staticmethod
    def add_surface_finish(db: Session, part_id: UUID, finish_data: dict) -> Optional[SurfaceFinish]:
        """Add surface finish to a part"""
        part = db.query(HardwarePart).filter(HardwarePart.id == part_id).first()
        if not part:
            return None

        db_finish = SurfaceFinish(**finish_data, hardware_part_id=part_id)
        db.add(db_finish)
        db.commit()
        db.refresh(db_finish)
        return db_finish

    @staticmethod
    def list_surface_finishes(db: Session, part_id: UUID) -> List[SurfaceFinish]:
        """List surface finishes for a part"""
        return db.query(SurfaceFinish).filter(SurfaceFinish.hardware_part_id == part_id).all()

    @staticmethod
    def delete_surface_finish(db: Session, finish_id: UUID) -> bool:
        """Delete a surface finish"""
        finish = db.query(SurfaceFinish).filter(SurfaceFinish.id == finish_id).first()
        if not finish:
            return False

        db.delete(finish)
        db.commit()
        return True
