"""Hardware part models"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Numeric, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    density = Column(Float)
    cost_per_kg = Column(Numeric(10, 2), nullable=False)
    tensile_strength = Column(Float)
    yield_strength = Column(Float)
    thermal_conductivity = Column(Float)
    machinability_index = Column(Float)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hardware_parts = relationship("HardwarePart", back_populates="material")


class Tolerance(Base):
    __tablename__ = "tolerances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    dimension = Column(String(255), nullable=False)
    nominal_value = Column(Float, nullable=False)
    upper_tolerance = Column(Float, nullable=False)
    lower_tolerance = Column(Float, nullable=False)
    tolerance_type = Column(String(50))
    tolerance_grade = Column(String(50))

    hardware_part = relationship("HardwarePart", back_populates="tolerances")


class SurfaceFinish(Base):
    __tablename__ = "surface_finishes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    name = Column(String(255), nullable=False)
    roughness_ra = Column(Float, nullable=False)
    roughness_rz = Column(Float)
    process = Column(String(255))
    cost_multiplier = Column(Float)

    hardware_part = relationship("HardwarePart", back_populates="surface_finishes")


class HardwarePart(Base):
    __tablename__ = "hardware_parts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    revision = Column(String(50))
    description = Column(String(2000))
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"))
    weight_kg = Column(Float, nullable=False)
    estimated_cost = Column(Numeric(10, 2))
    estimated_lead_time_days = Column(Integer)
    volume = Column(Float)
    surface_area = Column(Float)
    cad_model_url = Column(String(500))
    cad_model_hash = Column(String(256))
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material", back_populates="hardware_parts")
    tolerances = relationship("Tolerance", back_populates="hardware_part", cascade="all, delete-orphan")
    surface_finishes = relationship("SurfaceFinish", back_populates="hardware_part", cascade="all, delete-orphan")
    dfm_analyses = relationship("CADAnalysis", back_populates="hardware_part")
