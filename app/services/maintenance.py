from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    NotFoundError,
    ConflictError,
)
from app.models.maintenance import MaintenanceCategory, MaintenanceRecord
from app.models.vehicle import Vehicle


# --- Categories ---

def get_category_by_id(db: Session, category_id: int) -> MaintenanceCategory:
    cat = (
        db.query(MaintenanceCategory)
        .filter(MaintenanceCategory.id == category_id, MaintenanceCategory.is_deleted == False)
        .first()
    )
    if not cat:
        raise NotFoundError("Maintenance category not found")
    return cat


def get_all_categories(db: Session, active_only: bool = False) -> list[MaintenanceCategory]:
    q = db.query(MaintenanceCategory).filter(MaintenanceCategory.is_deleted == False)
    if active_only:
        q = q.filter(MaintenanceCategory.is_active == True)
    return q.order_by(MaintenanceCategory.name).all()


def create_category(
    db: Session, name: str, description: str = "", requires_notes: bool = False
) -> MaintenanceCategory:
    if db.query(MaintenanceCategory).filter(MaintenanceCategory.name == name, MaintenanceCategory.is_deleted == False).first():
        raise ConflictError("Category name already in use")

    cat = MaintenanceCategory(
        name=name,
        description=description or None,
        requires_notes=requires_notes,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(
    db: Session,
    category_id: int,
    name: str,
    description: str = "",
    requires_notes: bool = False,
    is_active: bool = True,
) -> MaintenanceCategory:
    cat = get_category_by_id(db, category_id)

    existing = (
        db.query(MaintenanceCategory)
        .filter(MaintenanceCategory.name == name, MaintenanceCategory.id != category_id, MaintenanceCategory.is_deleted == False)
        .first()
    )
    if existing:
        raise ConflictError("Category name already in use")

    cat.name = name
    cat.description = description or None
    cat.requires_notes = requires_notes
    cat.is_active = is_active
    db.commit()
    db.refresh(cat)
    return cat


def soft_delete_category(db: Session, category_id: int) -> None:
    cat = get_category_by_id(db, category_id)
    cat.is_deleted = True
    db.commit()


# --- Maintenance Records ---

def get_record_by_id(db: Session, record_id: int) -> MaintenanceRecord:
    record = (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.id == record_id, MaintenanceRecord.is_deleted == False)
        .first()
    )
    if not record:
        raise NotFoundError("Maintenance record not found")
    return record


def get_records_for_vehicle(db: Session, vehicle_id: int) -> list[MaintenanceRecord]:
    return (
        db.query(MaintenanceRecord)
        .filter(
            MaintenanceRecord.vehicle_id == vehicle_id,
            MaintenanceRecord.is_deleted == False,
        )
        .order_by(MaintenanceRecord.maintenance_date.desc())
        .all()
    )


def get_all_records(db: Session) -> list[MaintenanceRecord]:
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.is_deleted == False)
        .order_by(MaintenanceRecord.maintenance_date.desc())
        .all()
    )


def create_record(
    db: Session,
    vehicle_id: int,
    category_id: int,
    logged_by_user_id: int,
    maintenance_date: date,
    mileage_at_time: int,
    notes: str = "",
    cost: Decimal | None = None,
    user_role: str = "standard",
    user_vehicle_id: int | None = None,
) -> MaintenanceRecord:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise BusinessRuleError("Vehicle not found or has been deleted")
    if vehicle.is_retired:
        raise BusinessRuleError("Cannot add maintenance to a retired vehicle")

    if user_role == "standard" and vehicle.primary_driver_user_id != user_vehicle_id:
        raise AuthorisationError("You can only add maintenance for your assigned vehicle")

    category = get_category_by_id(db, category_id)
    if not category.is_active:
        raise BusinessRuleError("This maintenance category is not active")
    if category.requires_notes and not notes.strip():
        raise BusinessRuleError("Notes are required for this maintenance category")

    record = MaintenanceRecord(
        vehicle_id=vehicle_id,
        category_id=category_id,
        logged_by_user_id=logged_by_user_id,
        maintenance_date=maintenance_date,
        mileage_at_time=mileage_at_time,
        notes=notes.strip() or None,
        cost=cost,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(
    db: Session,
    record_id: int,
    category_id: int,
    maintenance_date: date,
    mileage_at_time: int,
    notes: str = "",
    cost: Decimal | None = None,
) -> MaintenanceRecord:
    record = get_record_by_id(db, record_id)

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == record.vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise BusinessRuleError("Vehicle not found or has been deleted")
    if vehicle.is_retired:
        raise BusinessRuleError("Cannot edit maintenance for a retired vehicle")

    category = get_category_by_id(db, category_id)
    if category.requires_notes and not notes.strip():
        raise BusinessRuleError("Notes are required for this maintenance category")

    record.category_id = category_id
    record.maintenance_date = maintenance_date
    record.mileage_at_time = mileage_at_time
    record.notes = notes.strip() or None
    record.cost = cost
    db.commit()
    db.refresh(record)
    return record


def soft_delete_record(db: Session, record_id: int) -> None:
    record = get_record_by_id(db, record_id)
    record.is_deleted = True
    db.commit()
