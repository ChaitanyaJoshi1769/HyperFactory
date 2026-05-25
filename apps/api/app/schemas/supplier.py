"""Supplier schemas"""

from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


class SupplierCapabilityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: Optional[str] = None
    process: Optional[str] = None
    min_order_quantity: Optional[int] = None
    max_annual_capacity: Optional[float] = None
    lead_time_standard_days: Optional[int] = None
    lead_time_expedited_days: Optional[int] = None
    cost_per_unit_base: Optional[Decimal] = Field(None, decimal_places=4)
    precision_capability_microns: Optional[float] = None
    material_capabilities: List[str] = []
    certifications: List[str] = []


class SupplierCapabilityCreate(SupplierCapabilityBase):
    pass


class SupplierCapabilityRead(SupplierCapabilityBase):
    id: UUID
    supplier_id: UUID

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    country: str = Field(..., min_length=1, max_length=50)
    region: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    quality_score: int = Field(50, ge=0, le=100)
    reliability_score: int = Field(50, ge=0, le=100)
    cost_competitiveness_score: int = Field(50, ge=0, le=100)
    on_time_delivery_rate: float = Field(80.0, ge=0, le=100)
    defect_rate: float = Field(2.0, ge=0, le=100)
    minimum_order_value: Optional[Decimal] = Field(None, decimal_places=2)
    payment_terms: Optional[str] = None
    lead_time_variability: Optional[float] = None
    certifications: List[str] = []


class SupplierCreate(SupplierBase):
    capabilities: Optional[List[SupplierCapabilityCreate]] = None


class SupplierRead(SupplierBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    capabilities: List[SupplierCapabilityRead] = []

    class Config:
        from_attributes = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    quality_score: Optional[int] = None
    reliability_score: Optional[int] = None
    cost_competitiveness_score: Optional[int] = None
    on_time_delivery_rate: Optional[float] = None
    defect_rate: Optional[float] = None
    minimum_order_value: Optional[Decimal] = None
    payment_terms: Optional[str] = None
    lead_time_variability: Optional[float] = None
    certifications: Optional[List[str]] = None


class SupplierQuoteBase(BaseModel):
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., decimal_places=4)
    total_price: Decimal = Field(..., decimal_places=2)
    lead_time_days: Optional[int] = None
    minimum_order_quantity: Optional[int] = None
    volume_available: Optional[float] = None
    expiration_date: Optional[datetime] = None
    terms: Optional[str] = Field(None, max_length=2000)


class SupplierQuoteCreate(SupplierQuoteBase):
    supplier_id: UUID
    part_id: UUID
    capability_id: Optional[UUID] = None


class SupplierQuoteRead(SupplierQuoteBase):
    id: UUID
    supplier_id: UUID
    part_id: UUID
    capability_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
