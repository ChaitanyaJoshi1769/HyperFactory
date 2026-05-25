"""Factory and manufacturing models"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Integer, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(255), nullable=False)
    process = Column(String(255))
    factory_id = Column(UUID(as_uuid=True), ForeignKey("factories.id"))
    location = Column(String(255))
    status = Column(String(50), default="idle")
    capacity_per_hour = Column(Float)
    power_consumption_kw = Column(Float)
    precision_microns = Column(Float)
    material_compatibility = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    last_maintenance = Column(DateTime)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    factory = relationship("FactoryConfig", back_populates="machines")
    jobs = relationship("ProductionJob", back_populates="machine")


class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"))
    status = Column(String(50), default="queued", index=True)
    quantity = Column(Integer, nullable=False)
    priority = Column(String(20), default="medium")
    estimated_duration_minutes = Column(Integer)
    actual_duration_minutes = Column(Integer)
    estimated_cost = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))
    start_time = Column(DateTime)
    completion_time = Column(DateTime)
    quality_checks_passed = Column(Integer, default=0)
    quality_checks_failed = Column(Integer, default=0)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    machine = relationship("Machine", back_populates="jobs")


class FactoryConfig(Base):
    __tablename__ = "factories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    country = Column(String(50))
    region = Column(String(100))
    status = Column(String(50), default="idle")
    capacity_utilization = Column(Float, default=0.0)
    power_consumption_kwh = Column(Float, default=0.0)
    production_efficiency = Column(Float, default=80.0)
    defect_rate = Column(Float, default=2.0)
    average_lead_time_days = Column(Integer)
    throughput_parts_per_day = Column(Integer)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    machines = relationship("Machine", back_populates="factory", cascade="all, delete-orphan")
