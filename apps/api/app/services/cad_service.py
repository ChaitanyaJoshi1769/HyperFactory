"""CAD service - business logic for CAD models and analysis"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.cad import CADModel, CADAnalysis
from app.schemas.cad import CADModelCreate, CADAnalysisCreate, CADAnalysisUpdate


class CADService:
    """Service layer for CAD models and analysis"""

    # ============================================================================
    # CAD Model Management
    # ============================================================================

    @staticmethod
    def create_cad_model(db: Session, model: CADModelCreate) -> CADModel:
        """Create a new CAD model"""
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

    @staticmethod
    def get_cad_model(db: Session, model_id: UUID) -> Optional[CADModel]:
        """Get CAD model by ID"""
        return db.query(CADModel).filter(CADModel.id == model_id).first()

    @staticmethod
    def list_cad_models(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        format: Optional[str] = None,
        hardware_part_id: Optional[UUID] = None,
    ) -> List[CADModel]:
        """List CAD models with optional filtering"""
        query = db.query(CADModel)

        if format:
            query = query.filter(CADModel.format == format)
        if hardware_part_id:
            query = query.filter(CADModel.hardware_part_id == hardware_part_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def delete_cad_model(db: Session, model_id: UUID) -> bool:
        """Delete a CAD model (cascades to analysis)"""
        model = db.query(CADModel).filter(CADModel.id == model_id).first()
        if not model:
            return False

        db.delete(model)
        db.commit()
        return True

    @staticmethod
    def get_model_by_hash(db: Session, file_hash: str) -> Optional[CADModel]:
        """Get CAD model by file hash (deduplication)"""
        return db.query(CADModel).filter(CADModel.file_hash == file_hash).first()

    @staticmethod
    def calculate_bounding_box_volume(model: CADModel) -> Optional[float]:
        """Calculate volume from bounding box"""
        if not all([
            model.bounding_box_min_x is not None,
            model.bounding_box_max_x is not None,
            model.bounding_box_min_y is not None,
            model.bounding_box_max_y is not None,
            model.bounding_box_min_z is not None,
            model.bounding_box_max_z is not None,
        ]):
            return None

        width = model.bounding_box_max_x - model.bounding_box_min_x
        height = model.bounding_box_max_y - model.bounding_box_min_y
        depth = model.bounding_box_max_z - model.bounding_box_min_z

        return width * height * depth

    @staticmethod
    def validate_cad_model(model: CADModel) -> dict:
        """Validate CAD model integrity"""
        issues = []

        # Check file hash
        if not model.file_hash:
            issues.append("Missing file hash")

        # Check bounding box consistency
        if model.bounding_box_min_x and model.bounding_box_max_x:
            if model.bounding_box_min_x >= model.bounding_box_max_x:
                issues.append("Invalid X bounding box: min >= max")

        if model.bounding_box_min_y and model.bounding_box_max_y:
            if model.bounding_box_min_y >= model.bounding_box_max_y:
                issues.append("Invalid Y bounding box: min >= max")

        if model.bounding_box_min_z and model.bounding_box_max_z:
            if model.bounding_box_min_z >= model.bounding_box_max_z:
                issues.append("Invalid Z bounding box: min >= max")

        # Check part and assembly counts
        if model.part_count and model.part_count < 1:
            issues.append("Part count must be >= 1")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    # ============================================================================
    # CAD Analysis Management
    # ============================================================================

    @staticmethod
    def create_cad_analysis(db: Session, analysis: CADAnalysisCreate) -> Optional[CADAnalysis]:
        """Create a new CAD analysis"""
        # Verify CAD model exists if provided
        if analysis.cad_model_id:
            model = db.query(CADModel).filter(CADModel.id == analysis.cad_model_id).first()
            if not model:
                return None

        db_analysis = CADAnalysis(**analysis.dict())
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        return db_analysis

    @staticmethod
    def get_cad_analysis(db: Session, analysis_id: UUID) -> Optional[CADAnalysis]:
        """Get CAD analysis by ID"""
        return db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()

    @staticmethod
    def list_cad_analyses(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        analysis_type: Optional[str] = None,
        hardware_part_id: Optional[UUID] = None,
        cad_model_id: Optional[UUID] = None,
        has_issues: Optional[bool] = None,
    ) -> List[CADAnalysis]:
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

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_cad_analysis(
        db: Session,
        analysis_id: UUID,
        update_data: CADAnalysisUpdate
    ) -> Optional[CADAnalysis]:
        """Update a CAD analysis"""
        analysis = db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()
        if not analysis:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(analysis, key, value)

        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def delete_cad_analysis(db: Session, analysis_id: UUID) -> bool:
        """Delete a CAD analysis"""
        analysis = db.query(CADAnalysis).filter(CADAnalysis.id == analysis_id).first()
        if not analysis:
            return False

        db.delete(analysis)
        db.commit()
        return True

    @staticmethod
    def get_model_analysis(db: Session, model_id: UUID) -> Optional[CADAnalysis]:
        """Get analysis for a CAD model (one-to-one relationship)"""
        model = db.query(CADModel).filter(CADModel.id == model_id).first()
        if not model:
            return None

        return db.query(CADAnalysis).filter(CADAnalysis.cad_model_id == model_id).first()

    @staticmethod
    def create_analysis_for_model(
        db: Session,
        model_id: UUID,
        analysis_type: str = "standard"
    ) -> Optional[CADAnalysis]:
        """Create analysis for a CAD model"""
        model = db.query(CADModel).filter(CADModel.id == model_id).first()
        if not model:
            return None

        # Check if analysis already exists
        existing = db.query(CADAnalysis).filter(CADAnalysis.cad_model_id == model_id).first()
        if existing:
            return None  # Analysis already exists

        # Create new analysis
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
        return db_analysis

    # ============================================================================
    # Analysis Metrics and Scoring
    # ============================================================================

    @staticmethod
    def calculate_overall_dfm_score(analysis: CADAnalysis) -> int:
        """Calculate overall DFM score from components"""
        if analysis.dfm_score is not None:
            return analysis.dfm_score

        # If no explicit DFM score, use manufacturability score
        score = analysis.manufacturability_score

        # Adjust for issues
        if analysis.issues_count > 0:
            score = max(0, score - (analysis.issues_count * 5))

        return int(score)

    @staticmethod
    def rank_models_by_manufacturability(models: List[CADModel]) -> List[tuple]:
        """Rank CAD models by manufacturability"""
        scored = []
        for model in models:
            if model.analysis:
                score = CADService.calculate_overall_dfm_score(model.analysis)
                scored.append((model, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    @staticmethod
    def get_analysis_summary(analysis: CADAnalysis) -> dict:
        """Get summary of analysis results"""
        return {
            "analysis_id": str(analysis.id),
            "analysis_type": analysis.analysis_type,
            "manufacturability_score": analysis.manufacturability_score,
            "dfm_score": analysis.dfm_score,
            "has_issues": analysis.has_issues,
            "issues_count": analysis.issues_count,
            "estimated_cost": float(analysis.estimated_cost) if analysis.estimated_cost else None,
            "estimated_lead_time_days": analysis.estimated_lead_time_days,
            "estimated_machining_time_minutes": analysis.estimated_machining_time_minutes,
            "feature_count": len(analysis.features),
            "issue_count": len(analysis.issues),
            "recommendation_count": len(analysis.recommendations),
            "created_at": analysis.created_at.isoformat(),
            "updated_at": analysis.updated_at.isoformat(),
        }

    @staticmethod
    def batch_analyze_models(
        db: Session,
        model_ids: List[UUID]
    ) -> List[dict]:
        """Get analysis summaries for multiple models"""
        summaries = []
        for model_id in model_ids:
            analysis = CADService.get_model_analysis(db, model_id)
            if analysis:
                summaries.append(CADService.get_analysis_summary(analysis))

        return summaries
