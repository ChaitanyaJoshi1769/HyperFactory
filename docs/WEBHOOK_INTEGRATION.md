# Webhook Integration Guide

This guide explains how to integrate webhook event publishing into your HyperFactory API service methods.

## Overview

The webhook system consists of three main components:

1. **EventPublisher** - Publishes events when API operations occur
2. **WebhookService** - Manages webhook subscriptions and deliveries
3. **WebhookProcessor** - Background task that processes pending deliveries

## Quick Start

### 1. Publishing an Event

When a factory is created, publish an event:

```python
from app.event_publisher import EventPublisher

# In your factory_service.py create_factory method
def create_factory(db: Session, user_id: str, factory_data: FactoryCreate):
    factory = FactoryConfig(**factory_data.dict())
    db.add(factory)
    db.commit()
    db.refresh(factory)

    # Publish event to all subscribed webhooks
    EventPublisher.factory_created(
        db=db,
        user_id=user_id,
        factory_id=str(factory.id),
        name=factory.name,
        location=factory.location,
        status=factory.status
    )

    return factory
```

### 2. Event Publishing Examples

**Factory Event:**
```python
EventPublisher.factory_created(
    db=db,
    user_id=user_id,
    factory_id=str(factory.id),
    name=factory.name,
    location=factory.location,
    status="operational"
)
```

**Job Event:**
```python
EventPublisher.job_completed(
    db=db,
    user_id=user_id,
    job_id=str(job.id),
    part_id=str(job.part_id),
    quantity=job.quantity,
    actual_duration_minutes=duration,
    actual_cost=float(job.actual_cost),
    quality_passed=job.quality_checks_passed,
    quality_failed=job.quality_checks_failed
)
```

**Machine Event:**
```python
EventPublisher.machine_updated(
    db=db,
    user_id=user_id,
    machine_id=str(machine.id),
    name=machine.name,
    changes={"status": "offline", "reason": "maintenance"}
)
```

**CAD Analysis Event:**
```python
EventPublisher.cad_analysis_completed(
    db=db,
    user_id=user_id,
    analysis_id=str(analysis.id),
    part_id=str(analysis.hardware_part_id),
    dfm_score=85.5,
    manufacturability_issues=[
        "Sharp internal corner at position (23, 45, 12)",
        "Minimum wall thickness 1.2mm below recommended 2mm"
    ],
    optimization_recommendations=[
        "Add 1mm fillet radius to internal corners",
        "Increase wall thickness to 2mm minimum"
    ]
)
```

## Integration Patterns

### Pattern 1: Publish After Create

```python
from app.event_publisher import EventPublisher

@router.post("/hardware-parts")
def create_hardware_part(
    part_data: HardwarePartCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # Create the resource
    hardware_part = HardwarePart(**part_data.dict())
    db.add(hardware_part)
    db.commit()
    db.refresh(hardware_part)

    # Publish event
    EventPublisher.part_created(
        db=db,
        user_id=user_id,
        part_id=str(hardware_part.id),
        name=hardware_part.name,
        part_type=hardware_part.type
    )

    return hardware_part
```

### Pattern 2: Publish After Update

```python
@router.put("/factories/{factory_id}")
def update_factory(
    factory_id: UUID,
    factory_update: FactoryUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    factory = db.query(FactoryConfig).filter(FactoryConfig.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")

    # Track changes
    changes = {}
    update_data = factory_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        old_value = getattr(factory, key, None)
        if old_value != value:
            changes[key] = {"old": old_value, "new": value}
        setattr(factory, key, value)

    db.commit()
    db.refresh(factory)

    # Publish update event with changes
    EventPublisher.factory_updated(
        db=db,
        user_id=user_id,
        factory_id=str(factory.id),
        name=factory.name,
        changes=changes
    )

    return factory
```

### Pattern 3: Publish on Status Change

```python
@router.post("/jobs/{job_id}/start")
def start_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "queued":
        raise HTTPException(status_code=400, detail="Job cannot be started")

    # Start the job
    job.status = "running"
    job.start_time = datetime.utcnow()
    db.commit()
    db.refresh(job)

    # Publish job started event
    EventPublisher.job_started(
        db=db,
        user_id=user_id,
        job_id=str(job.id),
        part_id=str(job.part_id),
        machine_id=str(job.machine_id),
        estimated_duration_minutes=job.estimated_duration_minutes or 0
    )

    return job
```

### Pattern 4: Publish on Error

```python
@router.post("/jobs/{job_id}/abort")
def abort_job(
    job_id: UUID,
    reason: str,
    error_message: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Abort the job
    job.status = "failed"
    job.completion_time = datetime.utcnow()
    db.commit()
    db.refresh(job)

    # Publish job failed event
    EventPublisher.job_failed(
        db=db,
        user_id=user_id,
        job_id=str(job.id),
        part_id=str(job.part_id),
        reason=reason,
        error_message=error_message
    )

    return {"status": "aborted", "reason": reason}
```

## Available Events

### Factory Events
```python
EventPublisher.factory_created(db, user_id, factory_id, name, location, **kwargs)
EventPublisher.factory_updated(db, user_id, factory_id, name, changes, **kwargs)
EventPublisher.factory_deleted(db, user_id, factory_id, name, **kwargs)
```

### Machine Events
```python
EventPublisher.machine_created(db, user_id, machine_id, name, factory_id, **kwargs)
EventPublisher.machine_updated(db, user_id, machine_id, name, changes, **kwargs)
EventPublisher.machine_deleted(db, user_id, machine_id, name, **kwargs)
```

### Production Job Events
```python
EventPublisher.job_created(db, user_id, job_id, part_id, machine_id, quantity, **kwargs)
EventPublisher.job_started(db, user_id, job_id, part_id, machine_id, estimated_duration_minutes, **kwargs)
EventPublisher.job_completed(db, user_id, job_id, part_id, quantity, actual_duration_minutes, actual_cost, quality_passed, quality_failed, **kwargs)
EventPublisher.job_failed(db, user_id, job_id, part_id, reason, error_message, **kwargs)
```

### CAD Events
```python
EventPublisher.cad_analysis_completed(db, user_id, analysis_id, part_id, dfm_score, manufacturability_issues, optimization_recommendations, **kwargs)
EventPublisher.cad_analysis_failed(db, user_id, analysis_id, part_id, error_reason, error_message, **kwargs)
```

### Hardware Part Events
```python
EventPublisher.part_created(db, user_id, part_id, name, part_type, **kwargs)
EventPublisher.part_updated(db, user_id, part_id, name, changes, **kwargs)
EventPublisher.part_deleted(db, user_id, part_id, name, **kwargs)
```

### User/Account Events
```python
EventPublisher.user_created(db, user_id, username, email, **kwargs)
EventPublisher.user_updated(db, user_id, username, changes, **kwargs)
EventPublisher.api_key_created(db, user_id, key_id, key_name, **kwargs)
EventPublisher.api_key_revoked(db, user_id, key_id, key_name, **kwargs)
```

## Background Processing

### Manual Processing

Trigger webhook delivery processing manually via admin endpoint:

```bash
curl -X POST https://api.hyperfactory.com/api/admin/webhooks/process \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Automated Processing

For production, set up a background task to process webhooks periodically:

```python
# In your main.py or task scheduler

from app.tasks import WebhookProcessor
import schedule
import time

def webhook_worker():
    while True:
        try:
            WebhookProcessor.process_pending_deliveries()
            time.sleep(60)  # Process every 60 seconds
        except Exception as e:
            logger.error(f"Webhook processor error: {e}")
            time.sleep(60)

# Start in a separate thread
import threading
webhook_thread = threading.Thread(target=webhook_worker, daemon=True)
webhook_thread.start()
```

Or using APScheduler:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks import WebhookProcessor

scheduler = BackgroundScheduler()

def process_webhooks():
    WebhookProcessor.process_pending_deliveries()

scheduler.add_job(process_webhooks, 'interval', seconds=60)
scheduler.start()
```

## Monitoring

### Check Webhook Health

```bash
curl -X GET https://api.hyperfactory.com/api/admin/webhooks/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Response:
```json
{
  "message": "Webhook statistics",
  "timestamp": "2026-05-26T14:30:00Z",
  "webhooks": {
    "total": 45,
    "active": 42,
    "disabled": 3
  },
  "deliveries": {
    "total": 12450,
    "successful": 12100,
    "failed": 325,
    "pending": 25,
    "success_rate": 97.28
  }
}
```

### Monitor Specific User's Webhooks

```bash
curl -X GET https://api.hyperfactory.com/api/admin/webhooks/user/{user_id} \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Clean Up Old Deliveries

```bash
curl -X POST "https://api.hyperfactory.com/api/admin/webhooks/cleanup?days_to_keep=30" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Error Handling

### Exception Handling in EventPublisher

```python
from app.event_publisher import EventPublisher

try:
    EventPublisher.job_completed(db, user_id, job_id, ...)
except Exception as e:
    # EventPublisher logs errors internally
    # Continue processing even if webhook publishing fails
    logger.warning(f"Failed to publish event: {e}")
    # Still return success to the user
```

### Retry Configuration

Configure retry behavior when creating webhooks:

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourserver.com/webhooks",
    "events": ["*"],
    "max_retries": 10,
    "retry_delay_seconds": 120,
    "timeout_seconds": 60
  }'
```

## Testing

### Test Event Publishing

```python
from app.event_publisher import EventPublisher
from app.db import SessionLocal

db = SessionLocal()
try:
    EventPublisher.factory_created(
        db=db,
        user_id="test-user-id",
        factory_id="test-factory-123",
        name="Test Factory",
        location="Test Location"
    )
    print("✓ Event published successfully")
finally:
    db.close()
```

### Manual Webhook Test

```bash
curl -X POST https://api.hyperfactory.com/api/webhooks/{webhook_id}/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "factory.created",
    "payload": {
      "factory_id": "test-123",
      "name": "Test Factory"
    }
  }'
```

## Best Practices

1. **Always publish events after successful database commits**
   - Only publish after `db.commit()` to ensure consistency

2. **Include relevant context in events**
   - Pass IDs, names, and status information that users will need

3. **Log event publishing**
   - Monitor which events are being published successfully

4. **Handle missing webhooks gracefully**
   - EventPublisher returns silently if no webhooks are subscribed

5. **Keep event payloads focused**
   - Include essential data, avoid unnecessary information

6. **Use consistent timestamps**
   - Events include `created_at` timestamp from the API server

7. **Track changes in updates**
   - Include before/after values when resources are modified

## Checklist for Integration

- [ ] Import EventPublisher in your service
- [ ] Add event publishing after successful operations
- [ ] Include relevant identifiers (IDs, names, status)
- [ ] Test with webhook created in development
- [ ] Verify webhook delivery in dashboard
- [ ] Monitor success rate in `/api/admin/webhooks/stats`
- [ ] Set up background webhook processor
- [ ] Configure cleanup for old deliveries (optional)

## Support

For issues or questions about webhook integration:
- Review webhook delivery history in dashboard
- Check `/api/admin/webhooks/stats` for health metrics
- Test webhook endpoint directly with manual test event
- Review webhook signature verification in receiver
