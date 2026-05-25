"""Supplier models"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class SupplierCapability(Base):
    __tablename__ = "supplier_capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    name = Column(String(255), nullable=False)
    type = Column(String(255))
    process = Column(String(255))
    min_order_quantity = Column(Integer)
    max_annual_capacity = Column(Float)
    lead_time_standard_days = Column(Integer)
    lead_time_expedited_days = Column(Integer)
    cost_per_unit_base = Column(Numeric(10, 4))
    precision_capability_microns = Column(Float)
    material_capabilities = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    properties = Column(JSON, default=dict)

    supplier = relationship("Supplier", back_populates="capabilities")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    country = Column(String(50), nullable=False, index=True)
    region = Column(String(100), index=True)
    city = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    quality_score = Column(Integer, default=50)
    reliability_score = Column(Integer, default=50)
    cost_competitiveness_score = Column(Integer, default=50)
    on_time_delivery_rate = Column(Float, default=80.0)
    defect_rate = Column(Float, default=2.0)
    minimum_order_value = Column(Numeric(10, 2))
    payment_terms = Column(String(255))
    lead_time_variability = Column(Float)
    certifications = Column(JSON, default=list)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    capabilities = relationship("SupplierCapability", back_populates="supplier", cascade="all, delete-orphan")
    quotes = relationship("SupplierQuote", back_populates="supplier")


class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    capability_id = Column(UUID(as_uuid=True), ForeignKey("supplier_capabilities.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=False)
    total_price = Column(Numeric(15, 2), nullable=False)
    lead_time_days = Column(Integer)
    minimum_order_quantity = Column(Integer)
    volume_available = Column(Float)
    expiration_date = Column(DateTime)
    terms = Column(String(2000))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="quotes")
