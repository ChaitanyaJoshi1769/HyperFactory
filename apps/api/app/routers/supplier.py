"""Supplier router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db import get_db
from app.models.supplier import Supplier, SupplierCapability, SupplierQuote
from app.schemas.supplier import (
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
    SupplierCapabilityCreate,
    SupplierCapabilityRead,
    SupplierQuoteCreate,
    SupplierQuoteRead,
)
from app.event_publisher import EventPublisher
from app.security import get_current_user_id

router = APIRouter(prefix="/api", tags=["suppliers"])


# ============================================================================
# Supplier Endpoints
# ============================================================================

@router.post("/suppliers", response_model=SupplierRead, status_code=201)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new supplier"""
    supplier_data = supplier.dict(exclude={'capabilities'})
    db_supplier = Supplier(**supplier_data)
    db.add(db_supplier)
    db.flush()

    # Add capabilities if provided
    if supplier.capabilities:
        for cap in supplier.capabilities:
            db_capability = SupplierCapability(**cap.dict(), supplier_id=db_supplier.id)
            db.add(db_capability)

    db.commit()
    db.refresh(db_supplier)

    # Publish webhook event
    EventPublisher.supplier_created(
        db=db,
        user_id=user_id,
        supplier_id=str(db_supplier.id),
        name=db_supplier.name,
        supplier_type=db_supplier.type or ""
    )

    return db_supplier


@router.get("/suppliers", response_model=List[SupplierRead])
def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    supplier_type: str = Query(None),
    country: str = Query(None),
    db: Session = Depends(get_db)
):
    """List suppliers with optional filtering"""
    query = db.query(Supplier)

    if supplier_type:
        query = query.filter(Supplier.type == supplier_type)
    if country:
        query = query.filter(Supplier.country == country)

    suppliers = query.offset(skip).limit(limit).all()
    return suppliers


@router.get("/suppliers/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: UUID, db: Session = Depends(get_db)):
    """Get a specific supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/suppliers/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: UUID,
    supplier_update: SupplierUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Update a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = supplier_update.dict(exclude_unset=True)
    changes = {k: v for k, v in update_data.items()}

    for key, value in update_data.items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)

    # Publish webhook event
    if changes:
        EventPublisher.supplier_updated(
            db=db,
            user_id=user_id,
            supplier_id=str(supplier.id),
            name=supplier.name,
            changes=changes
        )

    return supplier


@router.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier_name = supplier.name

    db.delete(supplier)
    db.commit()

    # Publish webhook event
    EventPublisher.supplier_deleted(
        db=db,
        user_id=user_id,
        supplier_id=str(supplier_id),
        name=supplier_name
    )


# ============================================================================
# Supplier Capability Endpoints
# ============================================================================

@router.post("/suppliers/{supplier_id}/capabilities", response_model=SupplierCapabilityRead, status_code=201)
def add_capability(
    supplier_id: UUID,
    capability: SupplierCapabilityCreate,
    db: Session = Depends(get_db)
):
    """Add a capability to a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db_capability = SupplierCapability(**capability.dict(), supplier_id=supplier_id)
    db.add(db_capability)
    db.commit()
    db.refresh(db_capability)
    return db_capability


@router.get("/suppliers/{supplier_id}/capabilities", response_model=List[SupplierCapabilityRead])
def list_capabilities(supplier_id: UUID, db: Session = Depends(get_db)):
    """List capabilities for a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier.capabilities


@router.get("/capabilities/{capability_id}", response_model=SupplierCapabilityRead)
def get_capability(capability_id: UUID, db: Session = Depends(get_db)):
    """Get a specific capability"""
    capability = db.query(SupplierCapability).filter(SupplierCapability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    return capability


@router.delete("/capabilities/{capability_id}", status_code=204)
def delete_capability(capability_id: UUID, db: Session = Depends(get_db)):
    """Delete a capability"""
    capability = db.query(SupplierCapability).filter(SupplierCapability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    db.delete(capability)
    db.commit()


# ============================================================================
# Supplier Quote Endpoints
# ============================================================================

@router.post("/quotes", response_model=SupplierQuoteRead, status_code=201)
def create_quote(
    quote: SupplierQuoteCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Create a supplier quote"""
    # Verify supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == quote.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db_quote = SupplierQuote(**quote.dict())
    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)

    # Publish webhook event
    EventPublisher.quote_created(
        db=db,
        user_id=user_id,
        quote_id=str(db_quote.id),
        supplier_id=str(db_quote.supplier_id),
        part_id=str(db_quote.part_id) if db_quote.part_id else "",
        unit_price=float(db_quote.unit_price) if db_quote.unit_price else 0.0,
        lead_time_days=db_quote.lead_time_days or 0
    )

    return db_quote


@router.get("/quotes", response_model=List[SupplierQuoteRead])
def list_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    supplier_id: UUID = Query(None),
    part_id: UUID = Query(None),
    db: Session = Depends(get_db)
):
    """List supplier quotes with optional filtering"""
    query = db.query(SupplierQuote)

    if supplier_id:
        query = query.filter(SupplierQuote.supplier_id == supplier_id)
    if part_id:
        query = query.filter(SupplierQuote.part_id == part_id)

    quotes = query.offset(skip).limit(limit).all()
    return quotes


@router.get("/quotes/{quote_id}", response_model=SupplierQuoteRead)
def get_quote(quote_id: UUID, db: Session = Depends(get_db)):
    """Get a specific quote"""
    quote = db.query(SupplierQuote).filter(SupplierQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@router.delete("/quotes/{quote_id}", status_code=204)
def delete_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a quote"""
    quote = db.query(SupplierQuote).filter(SupplierQuote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    supplier_id = quote.supplier_id
    part_id = quote.part_id

    db.delete(quote)
    db.commit()

    # Publish webhook event
    EventPublisher.quote_deleted(
        db=db,
        user_id=user_id,
        quote_id=str(quote_id),
        supplier_id=str(supplier_id),
        part_id=str(part_id) if part_id else ""
    )
