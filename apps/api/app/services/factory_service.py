"""Factory service - business logic for manufacturing orchestration"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.factory import FactoryConfig, Machine, ProductionJob
from app.schemas.factory import (
    FactoryConfigCreate,
    FactoryConfigUpdate,
    MachineCreate,
    MachineUpdate,
    ProductionJobCreate,
    ProductionJobUpdate,
)


class FactoryService:
    """Service layer for factory management"""

    # ============================================================================
    # Factory Config Management
    # ============================================================================

    @staticmethod
    def create_factory(db: Session, factory: FactoryConfigCreate) -> FactoryConfig:
        """Create a new factory"""
        db_factory = FactoryConfig(**factory.dict())
        db.add(db_factory)
        db.commit()
        db.refresh(db_factory)
        return db_factory

    @staticmethod
    def get_factory(db: Session, factory_id: UUID) -> Optional[FactoryConfig]:
        """Get factory by ID"""
        return db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()

    @staticmethod
    def list_factories(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        country: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[FactoryConfig]:
        """List factories with optional filtering"""
        query = db.query(FactoryConfig)

        if country:
            query = query.filter(FactoryConfig.country == country)
        if status:
            query = query.filter(FactoryConfig.status == status)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_factory(db: Session, factory_id: UUID, update_data: FactoryConfigUpdate) -> Optional[FactoryConfig]:
        """Update a factory"""
        factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
        if not factory:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(factory, key, value)

        db.commit()
        db.refresh(factory)
        return factory

    @staticmethod
    def delete_factory(db: Session, factory_id: UUID) -> bool:
        """Delete a factory (cascades to machines)"""
        factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
        if not factory:
            return False

        db.delete(factory)
        db.commit()
        return True

    # ============================================================================
    # Machine Management
    # ============================================================================

    @staticmethod
    def add_machine(db: Session, factory_id: UUID, machine: MachineCreate) -> Optional[Machine]:
        """Add machine to a factory"""
        factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
        if not factory:
            return None

        machine_data = machine.dict()
        machine_data['factory_id'] = factory_id
        db_machine = Machine(**machine_data)
        db.add(db_machine)
        db.commit()
        db.refresh(db_machine)
        return db_machine

    @staticmethod
    def list_machines(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        machine_type: Optional[str] = None,
        status: Optional[str] = None,
        factory_id: Optional[UUID] = None,
    ) -> List[Machine]:
        """List machines with optional filtering"""
        query = db.query(Machine)

        if machine_type:
            query = query.filter(Machine.type == machine_type)
        if status:
            query = query.filter(Machine.status == status)
        if factory_id:
            query = query.filter(Machine.factory_id == factory_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_machine(db: Session, machine_id: UUID) -> Optional[Machine]:
        """Get machine by ID"""
        return db.query(Machine).filter(Machine.id == machine_id).first()

    @staticmethod
    def update_machine(db: Session, machine_id: UUID, update_data: MachineUpdate) -> Optional[Machine]:
        """Update a machine"""
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(machine, key, value)

        db.commit()
        db.refresh(machine)
        return machine

    @staticmethod
    def delete_machine(db: Session, machine_id: UUID) -> bool:
        """Delete a machine"""
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            return False

        db.delete(machine)
        db.commit()
        return True

    @staticmethod
    def find_available_machine(
        db: Session,
        machine_type: str,
        process: Optional[str] = None,
    ) -> Optional[Machine]:
        """Find an available machine of given type"""
        query = db.query(Machine).filter(
            Machine.type == machine_type,
            Machine.status == "idle"
        )

        if process:
            query = query.filter(Machine.process == process)

        return query.first()

    # ============================================================================
    # Production Job Management
    # ============================================================================

    @staticmethod
    def create_job(db: Session, job: ProductionJobCreate) -> ProductionJob:
        """Create a new production job"""
        db_job = ProductionJob(**job.dict())
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job

    @staticmethod
    def get_job(db: Session, job_id: UUID) -> Optional[ProductionJob]:
        """Get job by ID"""
        return db.query(ProductionJob).filter(ProductionJob.id == job_id).first()

    @staticmethod
    def list_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        machine_id: Optional[UUID] = None,
        part_id: Optional[UUID] = None,
    ) -> List[ProductionJob]:
        """List jobs with optional filtering"""
        query = db.query(ProductionJob)

        if status:
            query = query.filter(ProductionJob.status == status)
        if priority:
            query = query.filter(ProductionJob.priority == priority)
        if machine_id:
            query = query.filter(ProductionJob.machine_id == machine_id)
        if part_id:
            query = query.filter(ProductionJob.part_id == part_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_job(db: Session, job_id: UUID, update_data: ProductionJobUpdate) -> Optional[ProductionJob]:
        """Update a job"""
        job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
        if not job:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(job, key, value)

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def delete_job(db: Session, job_id: UUID) -> bool:
        """Delete a job"""
        job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
        if not job:
            return False

        db.delete(job)
        db.commit()
        return True

    # ============================================================================
    # Job Status Transitions
    # ============================================================================

    @staticmethod
    def queue_job(db: Session, job_id: UUID) -> Optional[ProductionJob]:
        """Queue a job"""
        job = FactoryService.get_job(db, job_id)
        if not job:
            return None

        job.status = "queued"
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def start_job(db: Session, job_id: UUID) -> Optional[ProductionJob]:
        """Start a job (in progress)"""
        job = FactoryService.get_job(db, job_id)
        if not job:
            return None

        job.status = "in_progress"
        job.start_time = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def complete_job(db: Session, job_id: UUID) -> Optional[ProductionJob]:
        """Complete a job"""
        job = FactoryService.get_job(db, job_id)
        if not job:
            return None

        job.status = "completed"
        job.completion_time = datetime.utcnow()

        # Calculate actual duration if start time exists
        if job.start_time:
            duration = (job.completion_time - job.start_time).total_seconds() / 60
            job.actual_duration_minutes = int(duration)

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def cancel_job(db: Session, job_id: UUID) -> Optional[ProductionJob]:
        """Cancel a job"""
        job = FactoryService.get_job(db, job_id)
        if not job:
            return None

        job.status = "cancelled"
        db.commit()
        db.refresh(job)
        return job

    # ============================================================================
    # Job Scheduling and Optimization
    # ============================================================================

    @staticmethod
    def get_queue_length(db: Session, machine_id: UUID) -> int:
        """Get number of queued jobs for a machine"""
        return db.query(ProductionJob).filter(
            ProductionJob.machine_id == machine_id,
            ProductionJob.status.in_(["queued", "in_progress"])
        ).count()

    @staticmethod
    def estimate_job_completion(db: Session, job_id: UUID) -> Optional[datetime]:
        """Estimate job completion time"""
        job = FactoryService.get_job(db, job_id)
        if not job or not job.estimated_duration_minutes:
            return None

        if job.start_time:
            return job.start_time + timedelta(minutes=job.estimated_duration_minutes)

        # If not started, use current time + duration
        return datetime.utcnow() + timedelta(minutes=job.estimated_duration_minutes)

    @staticmethod
    def get_jobs_by_priority(db: Session, machine_id: UUID) -> List[ProductionJob]:
        """Get queued jobs sorted by priority"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        jobs = db.query(ProductionJob).filter(
            ProductionJob.machine_id == machine_id,
            ProductionJob.status == "queued"
        ).all()

        return sorted(jobs, key=lambda j: priority_order.get(j.priority, 4))

    @staticmethod
    def calculate_factory_metrics(db: Session, factory_id: UUID) -> dict:
        """Calculate factory performance metrics"""
        factory = FactoryService.get_factory(db, factory_id)
        if not factory:
            return {}

        machines = factory.machines
        total_jobs = db.query(ProductionJob).filter(
            ProductionJob.machine_id.in_([m.id for m in machines])
        ).count()

        completed_jobs = db.query(ProductionJob).filter(
            ProductionJob.machine_id.in_([m.id for m in machines]),
            ProductionJob.status == "completed"
        ).count()

        # Calculate average quality
        quality_checks_total = sum(
            j.quality_checks_passed + j.quality_checks_failed
            for j in db.query(ProductionJob).filter(
                ProductionJob.machine_id.in_([m.id for m in machines])
            ).all()
        )

        quality_checks_passed = sum(
            j.quality_checks_passed
            for j in db.query(ProductionJob).filter(
                ProductionJob.machine_id.in_([m.id for m in machines])
            ).all()
        )

        quality_rate = (quality_checks_passed / quality_checks_total * 100) if quality_checks_total > 0 else 0

        return {
            "factory_id": str(factory_id),
            "factory_name": factory.name,
            "machines": len(machines),
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "quality_pass_rate": round(quality_rate, 2),
            "utilization": factory.capacity_utilization,
            "efficiency": factory.production_efficiency,
            "defect_rate": factory.defect_rate,
        }
