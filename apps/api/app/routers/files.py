"""File upload and management router - CAD models, documents, etc."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
import os
import shutil
from pathlib import Path
from datetime import datetime
import mimetypes
import hashlib

from app.db import get_db
from app.models.user import User
from app.models.cad import CADModel
from app.middleware import get_current_user
from app.services.cad_service import CADService

router = APIRouter(prefix="/api/files", tags=["files"])

# File storage configuration
UPLOAD_DIR = Path("./uploads")
ALLOWED_EXTENSIONS = {".step", ".stp", ".stl", ".iges", ".igs", ".dwg", ".dxf", ".pdf"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Create upload directory
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================================
# CAD Model Upload
# ============================================================================

@router.post("/cad/upload", status_code=201)
async def upload_cad_model(
    file: UploadFile = File(...),
    name: str = Query(None),
    description: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a CAD model file.

    Supported formats: STEP, IGES, STL, DWG, DXF, PDF
    Max file size: 100MB

    Query Parameters:
    - name: Optional custom name for the model
    - description: Optional description
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # Calculate file hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = db.query(CADModel).filter(CADModel.file_hash == file_hash).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This file already exists in the system"
        )

    # Save file to disk
    file_id = str(uuid4())
    file_path = UPLOAD_DIR / file_id / file.filename
    file_path.parent.mkdir(exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create CAD model record
    model_name = name or Path(file.filename).stem
    cad_model = CADModel(
        name=model_name,
        description=description,
        file_name=file.filename,
        file_path=str(file_path),
        file_hash=file_hash,
        file_size=len(content),
        file_type=file_ext,
        uploaded_by=current_user.id,
        upload_date=datetime.utcnow(),
    )

    db.add(cad_model)
    db.commit()
    db.refresh(cad_model)

    return {
        "id": str(cad_model.id),
        "name": cad_model.name,
        "file_name": cad_model.file_name,
        "file_size": cad_model.file_size,
        "file_type": cad_model.file_type,
        "file_hash": cad_model.file_hash,
        "uploaded_by": str(cad_model.uploaded_by),
        "upload_date": cad_model.upload_date.isoformat(),
        "message": "File uploaded successfully"
    }


# ============================================================================
# CAD Model Download
# ============================================================================

@router.get("/cad/{model_id}/download")
async def download_cad_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a CAD model file.

    Returns the file for download with appropriate content-type header.
    """
    model = db.query(CADModel).filter(CADModel.id == model_id).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    file_path = Path(model.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file with streaming response
    from fastapi.responses import FileResponse

    return FileResponse(
        path=file_path,
        filename=model.file_name,
        media_type=mimetypes.guess_type(model.file_name)[0] or "application/octet-stream"
    )


# ============================================================================
# CAD Model Listing
# ============================================================================

@router.get("/cad")
async def list_cad_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all CAD models with pagination.

    Query Parameters:
    - skip: Number of models to skip (default: 0)
    - limit: Number of models to return (default: 100, max: 1000)
    """
    models = db.query(CADModel).offset(skip).limit(limit).all()

    return [
        {
            "id": str(model.id),
            "name": model.name,
            "description": model.description,
            "file_name": model.file_name,
            "file_size": model.file_size,
            "file_type": model.file_type,
            "uploaded_by": str(model.uploaded_by),
            "upload_date": model.upload_date.isoformat(),
            "last_modified": model.last_modified.isoformat() if model.last_modified else None,
        }
        for model in models
    ]


# ============================================================================
# CAD Model Details
# ============================================================================

@router.get("/cad/{model_id}")
async def get_cad_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get CAD model details"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": str(model.id),
        "name": model.name,
        "description": model.description,
        "file_name": model.file_name,
        "file_size": model.file_size,
        "file_type": model.file_type,
        "file_hash": model.file_hash,
        "uploaded_by": str(model.uploaded_by),
        "upload_date": model.upload_date.isoformat(),
        "last_modified": model.last_modified.isoformat() if model.last_modified else None,
        "bounding_box": {
            "min_x": model.bounding_box_min_x,
            "min_y": model.bounding_box_min_y,
            "min_z": model.bounding_box_min_z,
            "max_x": model.bounding_box_max_x,
            "max_y": model.bounding_box_max_y,
            "max_z": model.bounding_box_max_z,
        } if model.bounding_box_min_x is not None else None,
    }


# ============================================================================
# CAD Model Updates
# ============================================================================

@router.put("/cad/{model_id}")
async def update_cad_model(
    model_id: UUID,
    name: str = Query(None),
    description: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update CAD model metadata"""
    model = db.query(CADModel).filter(CADModel.id == model_id).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if name is not None:
        model.name = name

    if description is not None:
        model.description = description

    model.last_modified = datetime.utcnow()
    db.commit()
    db.refresh(model)

    return {
        "id": str(model.id),
        "name": model.name,
        "description": model.description,
        "last_modified": model.last_modified.isoformat(),
    }


# ============================================================================
# CAD Model Deletion
# ============================================================================

@router.delete("/cad/{model_id}", status_code=204)
async def delete_cad_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a CAD model and its associated files.

    Removes both the database record and the file from disk.
    """
    model = db.query(CADModel).filter(CADModel.id == model_id).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete file from disk
    file_path = Path(model.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            # Log but don't fail if file deletion fails
            print(f"Warning: Could not delete file {file_path}: {e}")

    # Delete empty directories
    try:
        file_path.parent.rmdir()
    except:
        pass

    # Delete from database
    db.delete(model)
    db.commit()


# ============================================================================
# File Statistics
# ============================================================================

@router.get("/stats")
async def get_file_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get file storage statistics"""
    from sqlalchemy import func

    total_files = db.query(CADModel).count()
    total_size = db.query(func.sum(CADModel.file_size)).scalar() or 0
    file_types = db.query(
        CADModel.file_type,
        func.count(CADModel.id)
    ).group_by(CADModel.file_type).all()

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "file_types": {
            file_type: count
            for file_type, count in file_types
        },
        "max_file_size_bytes": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
    }


# ============================================================================
# Batch Operations
# ============================================================================

@router.post("/cad/batch-delete")
async def batch_delete_cad_models(
    model_ids: list[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple CAD models at once"""
    deleted_count = 0
    errors = []

    for model_id in model_ids:
        try:
            model = db.query(CADModel).filter(CADModel.id == model_id).first()

            if not model:
                errors.append({"model_id": str(model_id), "error": "Not found"})
                continue

            # Delete file
            file_path = Path(model.file_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass

            # Delete from database
            db.delete(model)
            deleted_count += 1

        except Exception as e:
            errors.append({"model_id": str(model_id), "error": str(e)})

    db.commit()

    return {
        "deleted_count": deleted_count,
        "total_requested": len(model_ids),
        "errors": errors if errors else None,
    }


# ============================================================================
# Search & Filter
# ============================================================================

@router.get("/cad/search")
async def search_cad_models(
    query: str = Query(..., min_length=1),
    file_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search CAD models by name or description.

    Query Parameters:
    - query: Search term (required)
    - file_type: Filter by file type (e.g., .step)
    """
    search_term = f"%{query}%"
    q = db.query(CADModel).filter(
        (CADModel.name.ilike(search_term)) |
        (CADModel.description.ilike(search_term))
    )

    if file_type:
        q = q.filter(CADModel.file_type == file_type)

    models = q.all()

    return [
        {
            "id": str(model.id),
            "name": model.name,
            "description": model.description,
            "file_type": model.file_type,
            "file_size": model.file_size,
            "upload_date": model.upload_date.isoformat(),
        }
        for model in models
    ]
