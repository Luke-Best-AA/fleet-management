from sqlalchemy.orm import Session

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.models.location import Location
from app.models.user import User
from app.models.vehicle import Vehicle


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise NotFoundError("Vehicle not found")
    return vehicle


def get_all_vehicles(db: Session) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .filter(Vehicle.is_deleted == False)
        .order_by(Vehicle.registration_number)
        .all()
    )


def get_vehicles_for_user(db: Session, user_id: int) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .filter(
            Vehicle.primary_driver_user_id == user_id,
            Vehicle.is_deleted == False,
        )
        .order_by(Vehicle.registration_number)
        .all()
    )


def check_vehicle_access(vehicle: Vehicle, user: dict) -> None:
    if user["role"] == "admin":
        return
    if vehicle.primary_driver_user_id != user["id"]:
        raise AuthorisationError("You can only access your assigned vehicle")


def create_vehicle(
    db: Session,
    registration_number: str,
    fleet_reference: str,
    vehicle_type: str,
    make: str,
    model: str,
    year: int,
    location_id: int,
    current_mileage: int = 0,
    primary_driver_user_id: int | None = None,
) -> Vehicle:
    loc = db.query(Location).filter(Location.id == location_id, Location.is_deleted == False).first()
    if not loc:
        raise BusinessRuleError("Location not found or has been deleted")

    if db.query(Vehicle).filter(Vehicle.registration_number == registration_number, Vehicle.is_deleted == False).first():
        raise ConflictError("Registration number already in use")

    if db.query(Vehicle).filter(Vehicle.fleet_reference == fleet_reference, Vehicle.is_deleted == False).first():
        raise ConflictError("Fleet reference already in use")

    if primary_driver_user_id:
        driver = db.query(User).filter(User.id == primary_driver_user_id).first()
        if not driver:
            raise BusinessRuleError("Primary driver not found")
        if driver.role != "standard":
            raise BusinessRuleError("Primary driver must be a standard user")
        if not driver.is_active:
            raise BusinessRuleError("Primary driver must be an active user")

    vehicle = Vehicle(
        registration_number=registration_number,
        fleet_reference=fleet_reference,
        vehicle_type=vehicle_type,
        make=make,
        model=model,
        year=year,
        location_id=location_id,
        current_mileage=current_mileage,
        primary_driver_user_id=primary_driver_user_id or None,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(
    db: Session,
    vehicle_id: int,
    registration_number: str,
    fleet_reference: str,
    vehicle_type: str,
    make: str,
    model: str,
    year: int,
    location_id: int,
    primary_driver_user_id: int | None = None,
) -> Vehicle:
    vehicle = get_vehicle_by_id(db, vehicle_id)

    if vehicle.is_retired:
        raise BusinessRuleError("Retired vehicles cannot be edited")

    loc = db.query(Location).filter(Location.id == location_id, Location.is_deleted == False).first()
    if not loc:
        raise BusinessRuleError("Location not found or has been deleted")

    existing = (
        db.query(Vehicle)
        .filter(Vehicle.registration_number == registration_number, Vehicle.id != vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if existing:
        raise ConflictError("Registration number already in use")

    existing = (
        db.query(Vehicle)
        .filter(Vehicle.fleet_reference == fleet_reference, Vehicle.id != vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if existing:
        raise ConflictError("Fleet reference already in use")

    if primary_driver_user_id:
        driver = db.query(User).filter(User.id == primary_driver_user_id).first()
        if not driver:
            raise BusinessRuleError("Primary driver not found")
        if driver.role != "standard":
            raise BusinessRuleError("Primary driver must be a standard user")
        if not driver.is_active:
            raise BusinessRuleError("Primary driver must be an active user")

    vehicle.registration_number = registration_number
    vehicle.fleet_reference = fleet_reference
    vehicle.vehicle_type = vehicle_type
    vehicle.make = make
    vehicle.model = model
    vehicle.year = year
    vehicle.location_id = location_id
    vehicle.primary_driver_user_id = primary_driver_user_id or None
    db.commit()
    db.refresh(vehicle)
    return vehicle


def soft_delete_vehicle(db: Session, vehicle_id: int) -> None:
    vehicle = get_vehicle_by_id(db, vehicle_id)
    vehicle.is_deleted = True
    db.commit()


def retire_vehicle(db: Session, vehicle_id: int, reason: str) -> Vehicle:
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if vehicle.is_retired:
        raise BusinessRuleError("Vehicle is already retired")
    vehicle.status = "retired"
    vehicle.retirement_reason = reason
    db.commit()
    db.refresh(vehicle)
    return vehicle


def unretire_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle.is_retired:
        raise BusinessRuleError("Vehicle is not retired")
    vehicle.status = "active"
    vehicle.retirement_reason = None
    db.commit()
    db.refresh(vehicle)
    return vehicle
