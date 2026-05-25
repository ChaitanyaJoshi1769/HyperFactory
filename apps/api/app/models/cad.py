"""CAD and analysis models"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, LargeBinary, Integer, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class CADModel(Base):
    __tablename__ = "cad_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    name = Column(String(255), nullable=False, index=True)
    format = Column(String(20), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_hash = Column(String(256), unique=True)
    file_size_bytes = Column(Integer)
    bounding_box_min_x = Column(Float)
    bounding_box_min_y = Column(Float)
    bounding_box_min_z = Column(Float)
    bounding_box_max_x = Column(Float)
    bounding_box_max_y = Column(Float)
    bounding_box_max_z = Column(Float)
    volume_cubic_mm = Column(Float)
    surface_area_mm2 = Column(Float)
    part_count = Column(Integer)
    assembly_count = Column(Integer)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analysis = relationship("CADAnalysis", back_populates="cad_model", uselist=False)


class CADAnalysis(Base):
    __tablename__ = "cad_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hardware_part_id = Column(UUID(as_uuid=True), ForeignKey("hardware_parts.id"))
    cad_model_id = Column(UUID(as_uuid=True), ForeignKey("cad_models.id"), unique=True)
    analysis_type = Column(String(255))
    manufacturability_score = Column(Integer, default=50)
    has_issues = Column(Boolean, default=False)
    issues_count = Column(Integer, default=0)
    dfm_score = Column(Integer)
    estimated_machining_time_minutes = Column(Integer)
    estimated_cost = Column(Numeric(10, 2))
    estimated_lead_time_days = Column(Integer)
    features = Column(JSON, default=list)
    issues = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cad_model = relationship("CADModel", back_populates="analysis")
    hardware_part = relationship("HardwarePart", back_populates="dfm_analyses")
