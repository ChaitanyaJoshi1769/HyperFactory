"""CAD model and analysis router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db import get_db
from app.models.cad import CADModel, CADAnalysis
from app.schemas.cad import (
    CADModelCreate,
    CADModelRead,
    CADAnalysisCreate,
    CADAnalysisRead,
    CADAnalysisUpdate,
)
from app.event_publisher import EventPublisher

router = APIRouter(prefix="/api", tags=["cad"])


# ============================================================================
# CAD Model Endpoints
# ============================================================================

@router.post("/cad-models", response_model=CADModelRead, status_code=201)
def create_cad_model(model: CADModelCreate, db: Session = Depends(get_db)):
    """Create a new CAD model entry"""
    model_data = model.dict(exclude={'bounding_box'})

    # Flatten bounding box if provided
    if model.bounding_box:
        model_data['bounding_box_min_x'] = model.bounding_box.min_x
        model_data['bounding_box_min_y'] = model.bounding_box.min_y
        model_data['bounding_box_min_z'] = model.bounding_box.min_z
        model_data['bounding_box_max_x'] = model.bounding_box.max_x
        model_data['bounding_box_max_y'] = model.bounding_box.max_y
        model_data['bounding_box_max_z'] = model.bounding_box.max_z

    db_model = CADModel(**model_data)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.get("/cad-models", response_model=List[CADModelRead])
def list_cad_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    format: str = Query(None),
    hardware_part_id: UUID = Query(None),
    db: Session = Depends(get_db)
):
    """List CAD models with optional filtering"""
    query = db.query(CADModel)

    if format:
        query = query.filter(CADModel.format == format)
    if hardware_part_id:
        query = query.filter(CADModel.hardware_part_id == hardware_part_id)

    models = query.offset(skip).limit(limit).all()
    return models


@router.get("/cad-models/{model_id}", response_model=CADModelRead)
def get_cad_model(model_id: UUID, db: Session = Depends(get_db)):
    """Get a specific CAD model"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="CAD model not found")
    return model


@router.delete("/cad-models/{model_id}", status_code=204)
def delete_cad_model(model_id: UUID, db: Session = Depends(get_db)):
    """Delete a CAD model"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="CAD model not found")

    db.delete(model)
    db.commit()


# ============================================================================
# CAD Analysis Endpoints
# ============================================================================

@router.post("/cad-analyses", response_model=CADAnalysisRead, status_code=201)
def create_cad_analysis(analysis: CADAnalysisCreate, db: Session = Depends(get_db)):
    """Create a new CAD analysis"""
    # Verify CAD model exists if provided
    if analysis.cad_model_id:
        model = db.query(CADModel).filter(CADModel.id == analysis.cad_model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="CAD model not found")

    db_analysis = CADAnalysis(**analysis.dict())
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    # Publish webhook event
    EventPublisher.cad_analysis_completed(
        db=db,
        user_id="system",  # TODO: Get from auth context
        analysis_id=str(db_analysis.id),
        part_id=str(db_analysis.hardware_part_id) if db_analysis.hardware_part_id else "",
        dfm_score=db_analysis.manufacturability_score or 0,
        manufacturability_issues=db_analysis.identified_issues or [],
        optimization_recommendations=db_analysis.recommended_optimizations or []
    )

    return db_analysis


@router.get("/cad-analyses", response_model=List[CADAnalysisRead])
def list_cad_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    analysis_type: str = Query(None),
    hardware_part_id: UUID = Query(None),
    cad_model_id: UUID = Query(None),
    has_issues: bool = Query(None),
    db: Session = Depends(get_db)
):
    """List CAD analyses with optional filtering"""
    query = db.query(CADAnalysis)

    if analysis_type:
        query = query.filter(CADAnalysis.analysis_type == analysis_type)
    if hardware_part_id:
        query = query.filter(CADAnalysis.hardware_part_id == hardware_part_id)
    if cad_model_id:
        query = query.filter(CADAnalysis.cad_model_id == cad_model_id)
    if has_issues is not None:
        query = query.filter(CADAnalysis.has_issues == has_issues)

    analyses = query.offset(skip).limit(limit).all()
    return analyses


@router.get("/cad-analyses/{analysis_id}", response_model=CADAnalysisRead)
def get_cad_analysis(analysis_id: UUID, db: Session = Depends(get_db)):
    """Get a specific CAD analysis"""
    analysis = db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="CAD analysis not found")
    return analysis


@router.patch("/cad-analyses/{analysis_id}", response_model=CADAnalysisRead)
def update_cad_analysis(
    analysis_id: UUID,
    analysis_update: CADAnalysisUpdate,
    db: Session = Depends(get_db)
):
    """Update a CAD analysis"""
    analysis = db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="CAD analysis not found")

    update_data = analysis_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(analysis, key, value)

    db.commit()
    db.refresh(analysis)
    return analysis


@router.delete("/cad-analyses/{analysis_id}", status_code=204)
def delete_cad_analysis(analysis_id: UUID, db: Session = Depends(get_db)):
    """Delete a CAD analysis"""
    analysis = db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="CAD analysis not found")

    db.delete(analysis)
    db.commit()


# ============================================================================
# Linked Operations
# ============================================================================

@router.get("/cad-models/{model_id}/analysis", response_model=CADAnalysisRead)
def get_model_analysis(model_id: UUID, db: Session = Depends(get_db)):
    """Get analysis for a CAD model"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="CAD model not found")

    if not model.analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this model")

    return model.analysis


@router.post("/cad-models/{model_id}/analyze", response_model=CADAnalysisRead, status_code=201)
def analyze_cad_model(
    model_id: UUID,
    analysis_type: str = Query("standard", min_length=1),
    db: Session = Depends(get_db)
):
    """Create analysis for a CAD model"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="CAD model not found")

    # Check if analysis already exists
    existing = db.query(CADAnalysis).filter(CADAnalysis.cad_model_id == model_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Analysis already exists for this model")

    # Create new analysis with default values
    db_analysis = CADAnalysis(
        cad_model_id=model_id,
        hardware_part_id=model.hardware_part_id,
        analysis_type=analysis_type,
        manufacturability_score=50,
        has_issues=False,
        issues_count=0,
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    # Publish webhook event
    EventPublisher.cad_analysis_completed(
        db=db,
        user_id="system",  # TODO: Get from auth context
        analysis_id=str(db_analysis.id),
        part_id=str(db_analysis.hardware_part_id) if db_analysis.hardware_part_id else "",
        dfm_score=db_analysis.manufacturability_score or 0,
        manufacturability_issues=db_analysis.identified_issues or [],
        optimization_recommendations=db_analysis.recommended_optimizations or []
    )

    return db_analysis
