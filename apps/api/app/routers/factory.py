"""Factory and manufacturing router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db import get_db
from app.models.factory import FactoryConfig, Machine, ProductionJob
from app.schemas.factory import (
    FactoryConfigCreate,
    FactoryConfigRead,
    FactoryConfigUpdate,
    MachineCreate,
    MachineRead,
    MachineUpdate,
    ProductionJobCreate,
    ProductionJobRead,
    ProductionJobUpdate,
)

router = APIRouter(prefix="/api", tags=["factory"])


# ============================================================================
# Factory Config Endpoints
# ============================================================================

@router.post("/factories", response_model=FactoryConfigRead, status_code=201)
def create_factory(factory: FactoryConfigCreate, db: Session = Depends(get_db)):
    """Create a new factory"""
    db_factory = FactoryConfig(**factory.dict())
    db.add(db_factory)
    db.commit()
    db.refresh(db_factory)
    return db_factory


@router.get("/factories", response_model=List[FactoryConfigRead])
def list_factories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    country: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """List factories with optional filtering"""
    query = db.query(FactoryConfig)

    if country:
        query = query.filter(FactoryConfig.country == country)
    if status:
        query = query.filter(FactoryConfig.status == status)

    factories = query.offset(skip).limit(limit).all()
    return factories


@router.get("/factories/{factory_id}", response_model=FactoryConfigRead)
def get_factory(factory_id: UUID, db: Session = Depends(get_db)):
    """Get a specific factory"""
    factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")
    return factory


@router.patch("/factories/{factory_id}", response_model=FactoryConfigRead)
def update_factory(
    factory_id: UUID,
    factory_update: FactoryConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update a factory"""
    factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    update_data = factory_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(factory, key, value)

    db.commit()
    db.refresh(factory)
    return factory


@router.delete("/factories/{factory_id}", status_code=204)
def delete_factory(factory_id: UUID, db: Session = Depends(get_db)):
    """Delete a factory"""
    factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    db.delete(factory)
    db.commit()


# ============================================================================
# Machine Endpoints
# ============================================================================

@router.post("/factories/{factory_id}/machines", response_model=MachineRead, status_code=201)
def add_machine(
    factory_id: UUID,
    machine: MachineCreate,
    db: Session = Depends(get_db)
):
    """Add a machine to a factory"""
    factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    machine_data = machine.dict()
    machine_data['factory_id'] = factory_id
    db_machine = Machine(**machine_data)
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine


@router.get("/machines", response_model=List[MachineRead])
def list_machines(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    machine_type: str = Query(None),
    status: str = Query(None),
    factory_id: UUID = Query(None),
    db: Session = Depends(get_db)
):
    """List machines with optional filtering"""
    query = db.query(Machine)

    if machine_type:
        query = query.filter(Machine.type == machine_type)
    if status:
        query = query.filter(Machine.status == status)
    if factory_id:
        query = query.filter(Machine.factory_id == factory_id)

    machines = query.offset(skip).limit(limit).all()
    return machines


@router.get("/machines/{machine_id}", response_model=MachineRead)
def get_machine(machine_id: UUID, db: Session = Depends(get_db)):
    """Get a specific machine"""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine


@router.patch("/machines/{machine_id}", response_model=MachineRead)
def update_machine(
    machine_id: UUID,
    machine_update: MachineUpdate,
    db: Session = Depends(get_db)
):
    """Update a machine"""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    update_data = machine_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(machine, key, value)

    db.commit()
    db.refresh(machine)
    return machine


@router.delete("/machines/{machine_id}", status_code=204)
def delete_machine(machine_id: UUID, db: Session = Depends(get_db)):
    """Delete a machine"""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    db.delete(machine)
    db.commit()


# ============================================================================
# Production Job Endpoints
# ============================================================================

@router.post("/production-jobs", response_model=ProductionJobRead, status_code=201)
def create_job(job: ProductionJobCreate, db: Session = Depends(get_db)):
    """Create a new production job"""
    db_job = ProductionJob(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.get("/production-jobs", response_model=List[ProductionJobRead])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    priority: str = Query(None),
    machine_id: UUID = Query(None),
    part_id: UUID = Query(None),
    db: Session = Depends(get_db)
):
    """List production jobs with optional filtering"""
    query = db.query(ProductionJob)

    if status:
        query = query.filter(ProductionJob.status == status)
    if priority:
        query = query.filter(ProductionJob.priority == priority)
    if machine_id:
        query = query.filter(ProductionJob.machine_id == machine_id)
    if part_id:
        query = query.filter(ProductionJob.part_id == part_id)

    jobs = query.offset(skip).limit(limit).all()
    return jobs


@router.get("/production-jobs/{job_id}", response_model=ProductionJobRead)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get a specific production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")
    return job


@router.patch("/production-jobs/{job_id}", response_model=ProductionJobRead)
def update_job(
    job_id: UUID,
    job_update: ProductionJobUpdate,
    db: Session = Depends(get_db)
):
    """Update a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    update_data = job_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)
    return job


@router.delete("/production-jobs/{job_id}", status_code=204)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Delete a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    db.delete(job)
    db.commit()


# ============================================================================
# Production Job Status Actions
# ============================================================================

@router.post("/production-jobs/{job_id}/queue", response_model=ProductionJobRead)
def queue_job(job_id: UUID, db: Session = Depends(get_db)):
    """Queue a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    job.status = "queued"
    db.commit()
    db.refresh(job)
    return job


@router.post("/production-jobs/{job_id}/start", response_model=ProductionJobRead)
def start_job(job_id: UUID, db: Session = Depends(get_db)):
    """Start a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    job.status = "in_progress"
    db.commit()
    db.refresh(job)
    return job


@router.post("/production-jobs/{job_id}/complete", response_model=ProductionJobRead)
def complete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Complete a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    job.status = "completed"
    db.commit()
    db.refresh(job)
    return job


@router.post("/production-jobs/{job_id}/cancel", response_model=ProductionJobRead)
def cancel_job(job_id: UUID, db: Session = Depends(get_db)):
    """Cancel a production job"""
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Production job not found")

    job.status = "cancelled"
    db.commit()
    db.refresh(job)
    return job
