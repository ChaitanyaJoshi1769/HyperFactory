"""CAD and analysis schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any


class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


class CADModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    format: str = Field(..., min_length=1, max_length=20)
    file_url: str = Field(..., max_length=500)
    file_hash: Optional[str] = Field(None, max_length=256)
    file_size_bytes: Optional[int] = None
    volume_cubic_mm: Optional[float] = None
    surface_area_mm2: Optional[float] = None
    part_count: Optional[int] = None
    assembly_count: Optional[int] = None


class CADModelCreate(CADModelBase):
    hardware_part_id: Optional[UUID] = None
    bounding_box: Optional[BoundingBox] = None


class CADModelRead(CADModelBase):
    id: UUID
    hardware_part_id: Optional[UUID] = None
    bounding_box_min_x: Optional[float] = None
    bounding_box_min_y: Optional[float] = None
    bounding_box_min_z: Optional[float] = None
    bounding_box_max_x: Optional[float] = None
    bounding_box_max_y: Optional[float] = None
    bounding_box_max_z: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CADAnalysisBase(BaseModel):
    analysis_type: Optional[str] = None
    manufacturability_score: int = Field(50, ge=0, le=100)
    has_issues: bool = False
    issues_count: int = 0
    dfm_score: Optional[int] = None
    estimated_machining_time_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = Field(None, decimal_places=2)
    estimated_lead_time_days: Optional[int] = None
    features: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []


class CADAnalysisCreate(CADAnalysisBase):
    hardware_part_id: Optional[UUID] = None
    cad_model_id: Optional[UUID] = None


class CADAnalysisRead(CADAnalysisBase):
    id: UUID
    hardware_part_id: Optional[UUID] = None
    cad_model_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CADAnalysisUpdate(BaseModel):
    analysis_type: Optional[str] = None
    manufacturability_score: Optional[int] = None
    has_issues: Optional[bool] = None
    issues_count: Optional[int] = None
    dfm_score: Optional[int] = None
    estimated_machining_time_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = None
    estimated_lead_time_days: Optional[int] = None
    features: Optional[List[Dict[str, Any]]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
