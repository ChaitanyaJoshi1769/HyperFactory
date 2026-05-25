"""Hardware part schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


class MaterialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    density: Optional[float] = None
    cost_per_kg: Decimal = Field(..., decimal_places=2)
    tensile_strength: Optional[float] = None
    yield_strength: Optional[float] = None
    thermal_conductivity: Optional[float] = None
    machinability_index: Optional[float] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialRead(MaterialBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToleranceBase(BaseModel):
    dimension: str = Field(..., min_length=1, max_length=255)
    nominal_value: float
    upper_tolerance: float
    lower_tolerance: float
    tolerance_type: Optional[str] = None
    tolerance_grade: Optional[str] = None


class ToleranceCreate(ToleranceBase):
    pass


class ToleranceRead(ToleranceBase):
    id: UUID
    hardware_part_id: UUID

    class Config:
        from_attributes = True


class SurfaceFinishBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    roughness_ra: float
    roughness_rz: Optional[float] = None
    process: Optional[str] = None
    cost_multiplier: Optional[float] = None


class SurfaceFinishCreate(SurfaceFinishBase):
    pass


class SurfaceFinishRead(SurfaceFinishBase):
    id: UUID
    hardware_part_id: UUID

    class Config:
        from_attributes = True


class HardwarePartBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    revision: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)
    weight_kg: float = Field(..., gt=0)
    estimated_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_lead_time_days: Optional[int] = None
    volume: Optional[float] = None
    surface_area: Optional[float] = None
    cad_model_url: Optional[str] = Field(None, max_length=500)
    cad_model_hash: Optional[str] = Field(None, max_length=256)


class HardwarePartCreate(HardwarePartBase):
    material_id: Optional[UUID] = None
    tolerances: Optional[List[ToleranceCreate]] = None
    surface_finishes: Optional[List[SurfaceFinishCreate]] = None


class HardwarePartRead(HardwarePartBase):
    id: UUID
    material_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    tolerances: List[ToleranceRead] = []
    surface_finishes: List[SurfaceFinishRead] = []

    class Config:
        from_attributes = True


class HardwarePartUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    revision: Optional[str] = None
    description: Optional[str] = None
    weight_kg: Optional[float] = None
    estimated_cost: Optional[Decimal] = None
    estimated_lead_time_days: Optional[int] = None
    volume: Optional[float] = None
    surface_area: Optional[float] = None
    cad_model_url: Optional[str] = None
    cad_model_hash: Optional[str] = None
