"""Factory and manufacturing schemas"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


class MachineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=255)
    process: Optional[str] = None
    location: Optional[str] = None
    status: str = Field("idle", max_length=50)
    capacity_per_hour: Optional[float] = None
    power_consumption_kw: Optional[float] = None
    precision_microns: Optional[float] = None
    material_compatibility: List[str] = []
    certifications: List[str] = []
    last_maintenance: Optional[datetime] = None


class MachineCreate(MachineBase):
    factory_id: Optional[UUID] = None


class MachineRead(MachineBase):
    id: UUID
    factory_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    process: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    capacity_per_hour: Optional[float] = None
    power_consumption_kw: Optional[float] = None
    precision_microns: Optional[float] = None
    material_compatibility: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    last_maintenance: Optional[datetime] = None


class ProductionJobBase(BaseModel):
    quantity: int = Field(..., gt=0)
    priority: str = Field("medium", max_length=20)
    status: str = Field("queued", max_length=50)
    estimated_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = Field(None, decimal_places=2)
    actual_cost: Optional[Decimal] = Field(None, decimal_places=2)
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None


class ProductionJobCreate(ProductionJobBase):
    part_id: UUID
    machine_id: Optional[UUID] = None


class ProductionJobRead(ProductionJobBase):
    id: UUID
    part_id: UUID
    machine_id: Optional[UUID] = None
    quality_checks_passed: int = 0
    quality_checks_failed: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductionJobUpdate(BaseModel):
    priority: Optional[str] = None
    status: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    quality_checks_passed: Optional[int] = None
    quality_checks_failed: Optional[int] = None


class FactoryConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=100)
    status: str = Field("idle", max_length=50)
    capacity_utilization: float = Field(0.0, ge=0, le=100)
    power_consumption_kwh: float = Field(0.0, ge=0)
    production_efficiency: float = Field(80.0, ge=0, le=100)
    defect_rate: float = Field(2.0, ge=0, le=100)
    average_lead_time_days: Optional[int] = None
    throughput_parts_per_day: Optional[int] = None


class FactoryConfigCreate(FactoryConfigBase):
    pass


class FactoryConfigRead(FactoryConfigBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    machines: List[MachineRead] = []

    class Config:
        from_attributes = True


class FactoryConfigUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None
    capacity_utilization: Optional[float] = None
    power_consumption_kwh: Optional[float] = None
    production_efficiency: Optional[float] = None
    defect_rate: Optional[float] = None
    average_lead_time_days: Optional[int] = None
    throughput_parts_per_day: Optional[int] = None
