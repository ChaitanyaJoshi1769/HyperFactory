"""Supplier service - business logic for supplier management"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.supplier import Supplier, SupplierCapability, SupplierQuote
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierCapabilityCreate, SupplierQuoteCreate


class SupplierService:
    """Service layer for supplier management"""

    # ============================================================================
    # Supplier Management
    # ============================================================================

    @staticmethod
    def create_supplier(db: Session, supplier: SupplierCreate) -> Supplier:
        """Create a new supplier with optional capabilities"""
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
        return db_supplier

    @staticmethod
    def get_supplier(db: Session, supplier_id: UUID) -> Optional[Supplier]:
        """Get supplier by ID"""
        return db.query(Supplier).filter(Supplier.id == supplier_id).first()

    @staticmethod
    def list_suppliers(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        supplier_type: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Supplier]:
        """List suppliers with optional filtering"""
        query = db.query(Supplier)

        if supplier_type:
            query = query.filter(Supplier.type == supplier_type)
        if country:
            query = query.filter(Supplier.country == country)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_supplier(db: Session, supplier_id: UUID, update_data: SupplierUpdate) -> Optional[Supplier]:
        """Update a supplier"""
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return None

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(supplier, key, value)

        db.commit()
        db.refresh(supplier)
        return supplier

    @staticmethod
    def delete_supplier(db: Session, supplier_id: UUID) -> bool:
        """Delete a supplier (cascades to capabilities and quotes)"""
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return False

        db.delete(supplier)
        db.commit()
        return True

    # ============================================================================
    # Supplier Scoring and Metrics
    # ============================================================================

    @staticmethod
    def calculate_overall_score(supplier: Supplier) -> int:
        """Calculate weighted overall score for a supplier"""
        weights = {
            'quality': 0.35,
            'reliability': 0.25,
            'cost': 0.20,
            'delivery': 0.15,
            'defect': 0.05,
        }

        # Invert defect rate (lower is better)
        defect_score = max(0, 100 - supplier.defect_rate)

        overall = (
            supplier.quality_score * weights['quality'] +
            supplier.reliability_score * weights['reliability'] +
            supplier.cost_competitiveness_score * weights['cost'] +
            supplier.on_time_delivery_rate * weights['delivery'] +
            defect_score * weights['defect']
        )

        return int(overall)

    @staticmethod
    def rank_suppliers_by_score(db: Session, suppliers: List[Supplier]) -> List[tuple]:
        """Rank suppliers by overall score"""
        scored = [
            (supplier, SupplierService.calculate_overall_score(supplier))
            for supplier in suppliers
        ]
        return sorted(scored, key=lambda x: x[1], reverse=True)

    @staticmethod
    def find_best_supplier_for_capability(
        db: Session,
        capability_type: str,
        process: str
    ) -> Optional[Supplier]:
        """Find best supplier for a specific capability"""
        capabilities = db.query(SupplierCapability).filter(
            SupplierCapability.type == capability_type,
            SupplierCapability.process == process
        ).all()

        if not capabilities:
            return None

        suppliers = [cap.supplier for cap in capabilities]
        ranked = SupplierService.rank_suppliers_by_score(db, suppliers)
        return ranked[0][0] if ranked else None

    # ============================================================================
    # Supplier Capability Management
    # ============================================================================

    @staticmethod
    def add_capability(db: Session, supplier_id: UUID, capability: SupplierCapabilityCreate) -> Optional[SupplierCapability]:
        """Add capability to a supplier"""
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return None

        db_capability = SupplierCapability(**capability.dict(), supplier_id=supplier_id)
        db.add(db_capability)
        db.commit()
        db.refresh(db_capability)
        return db_capability

    @staticmethod
    def list_capabilities(db: Session, supplier_id: UUID) -> List[SupplierCapability]:
        """List capabilities for a supplier"""
        return db.query(SupplierCapability).filter(SupplierCapability.supplier_id == supplier_id).all()

    @staticmethod
    def get_capability(db: Session, capability_id: UUID) -> Optional[SupplierCapability]:
        """Get capability by ID"""
        return db.query(SupplierCapability).filter(SupplierCapability.id == capability_id).first()

    @staticmethod
    def delete_capability(db: Session, capability_id: UUID) -> bool:
        """Delete a capability"""
        capability = db.query(SupplierCapability).filter(SupplierCapability.id == capability_id).first()
        if not capability:
            return False

        db.delete(capability)
        db.commit()
        return True

    @staticmethod
    def check_capability_availability(
        db: Session,
        supplier_id: UUID,
        required_quantity: int,
        capability_type: Optional[str] = None
    ) -> dict:
        """Check if supplier has capacity for requested quantity"""
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return {"available": False, "error": "Supplier not found"}

        capabilities = db.query(SupplierCapability).filter(
            SupplierCapability.supplier_id == supplier_id
        ).all()

        if capability_type:
            capabilities = [c for c in capabilities if c.type == capability_type]

        if not capabilities:
            return {"available": False, "error": "No matching capabilities"}

        # Check if any capability can handle the quantity
        total_capacity = sum(c.max_annual_capacity or 0 for c in capabilities)
        available = total_capacity >= required_quantity

        return {
            "available": available,
            "required_quantity": required_quantity,
            "total_capacity": total_capacity,
            "capability_count": len(capabilities),
        }

    # ============================================================================
    # Supplier Quote Management
    # ============================================================================

    @staticmethod
    def create_quote(db: Session, quote: SupplierQuoteCreate) -> Optional[SupplierQuote]:
        """Create a supplier quote"""
        supplier = db.query(Supplier).filter(Supplier.id == quote.supplier_id).first()
        if not supplier:
            return None

        db_quote = SupplierQuote(**quote.dict())
        db.add(db_quote)
        db.commit()
        db.refresh(db_quote)
        return db_quote

    @staticmethod
    def list_quotes(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        supplier_id: Optional[UUID] = None,
        part_id: Optional[UUID] = None,
    ) -> List[SupplierQuote]:
        """List quotes with optional filtering"""
        query = db.query(SupplierQuote)

        if supplier_id:
            query = query.filter(SupplierQuote.supplier_id == supplier_id)
        if part_id:
            query = query.filter(SupplierQuote.part_id == part_id)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_quote(db: Session, quote_id: UUID) -> Optional[SupplierQuote]:
        """Get quote by ID"""
        return db.query(SupplierQuote).filter(SupplierQuote.id == quote_id).first()

    @staticmethod
    def delete_quote(db: Session, quote_id: UUID) -> bool:
        """Delete a quote"""
        quote = db.query(SupplierQuote).filter(SupplierQuote.id == quote_id).first()
        if not quote:
            return False

        db.delete(quote)
        db.commit()
        return True

    @staticmethod
    def get_best_quote_for_part(
        db: Session,
        part_id: UUID,
        quantity: Optional[int] = None
    ) -> Optional[SupplierQuote]:
        """Get best quote for a part (by total price)"""
        query = db.query(SupplierQuote).filter(SupplierQuote.part_id == part_id)

        if quantity:
            query = query.filter(
                (SupplierQuote.minimum_order_quantity.isnot(None)) &
                (SupplierQuote.minimum_order_quantity <= quantity)
            )

        # Filter active quotes (not expired)
        query = query.filter(
            (SupplierQuote.expiration_date.isnot(None)) &
            (SupplierQuote.expiration_date > datetime.utcnow())
        )

        quotes = query.all()
        if not quotes:
            return None

        # Return quote with lowest total price
        return min(quotes, key=lambda q: float(q.total_price))

    @staticmethod
    def compare_quotes(db: Session, part_id: UUID) -> List[dict]:
        """Compare all quotes for a part"""
        quotes = db.query(SupplierQuote).filter(SupplierQuote.part_id == part_id).all()

        comparison = []
        for quote in quotes:
            supplier = db.query(Supplier).filter(Supplier.id == quote.supplier_id).first()
            comparison.append({
                "quote_id": str(quote.id),
                "supplier_name": supplier.name if supplier else "Unknown",
                "unit_price": float(quote.unit_price),
                "total_price": float(quote.total_price),
                "lead_time_days": quote.lead_time_days,
                "minimum_order_quantity": quote.minimum_order_quantity,
                "is_expired": quote.expiration_date < datetime.utcnow() if quote.expiration_date else False,
            })

        return sorted(comparison, key=lambda x: x["total_price"])
