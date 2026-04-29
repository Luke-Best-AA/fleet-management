from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import AuthorisationError, BusinessRuleError, NotFoundError
from app.models.mileage import MileageRecord
from app.models.vehicle import Vehicle


def get_record_by_id(db: Session, record_id: int) -> MileageRecord:
    record = (
        db.query(MileageRecord)
        .filter(MileageRecord.id == record_id, MileageRecord.is_deleted == False)
        .first()
    )
    if not record:
        raise NotFoundError("Mileage record not found")
    return record


def get_records_for_vehicle(db: Session, vehicle_id: int) -> list[MileageRecord]:
    return (
        db.query(MileageRecord)
        .filter(
            MileageRecord.vehicle_id == vehicle_id,
            MileageRecord.is_deleted == False,
        )
        .order_by(MileageRecord.recorded_at.desc())
        .all()
    )


def get_all_records(db: Session) -> list[MileageRecord]:
    return (
        db.query(MileageRecord)
        .filter(MileageRecord.is_deleted == False)
        .order_by(MileageRecord.recorded_at.desc())
        .all()
    )


def create_record(
    db: Session,
    vehicle_id: int,
    recorded_by_user_id: int,
    reading_value: int,
    is_admin_override: bool = False,
    override_reason: str = "",
    user_role: str = "standard",
    user_id: int | None = None,
) -> MileageRecord:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise BusinessRuleError("Vehicle not found or has been deleted")
    if vehicle.is_retired:
        raise BusinessRuleError("Cannot add mileage to a retired vehicle")

    if user_role == "standard":
        if vehicle.primary_driver_user_id != user_id:
            raise AuthorisationError(
                "You can only record mileage for your assigned vehicle"
            )
        if reading_value < vehicle.current_mileage:
            raise BusinessRuleError(
                f"Reading must be at least {vehicle.current_mileage} (current mileage)"
            )
        is_admin_override = False
        override_reason = ""

    if user_role == "admin" and is_admin_override:
        if not override_reason.strip():
            raise BusinessRuleError(
                "Override reason is required for admin mileage overrides"
            )

    record = MileageRecord(
        vehicle_id=vehicle_id,
        recorded_by_user_id=recorded_by_user_id,
        reading_value=reading_value,
        is_admin_override=is_admin_override,
        override_reason=override_reason.strip() or None,
    )
    db.add(record)

    if reading_value > vehicle.current_mileage:
        vehicle.current_mileage = reading_value

    db.commit()
    db.refresh(record)
    return record


def update_record(
    db: Session,
    record_id: int,
    reading_value: int,
    is_admin_override: bool = False,
    override_reason: str = "",
) -> MileageRecord:
    record = get_record_by_id(db, record_id)

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == record.vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise BusinessRuleError("Vehicle not found or has been deleted")
    if vehicle.is_retired:
        raise BusinessRuleError("Cannot edit mileage for a retired vehicle")

    if is_admin_override and not override_reason.strip():
        raise BusinessRuleError(
            "Override reason is required for admin mileage overrides"
        )

    record.reading_value = reading_value
    record.is_admin_override = is_admin_override
    record.override_reason = override_reason.strip() or None

    _recalculate_vehicle_mileage(db, vehicle)
    db.commit()
    db.refresh(record)
    return record


def soft_delete_record(db: Session, record_id: int) -> None:
    record = get_record_by_id(db, record_id)
    record.is_deleted = True

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == record.vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if vehicle:
        db.flush()
        _recalculate_vehicle_mileage(db, vehicle)

    db.commit()


def _recalculate_vehicle_mileage(db: Session, vehicle: Vehicle) -> None:
    max_reading = (
        db.query(func.max(MileageRecord.reading_value))
        .filter(
            MileageRecord.vehicle_id == vehicle.id,
            MileageRecord.is_deleted == False,
        )
        .scalar()
    )
    vehicle.current_mileage = max_reading or 0
