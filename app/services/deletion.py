from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions import AuthorisationError, BusinessRuleError, NotFoundError
from app.models.deletion_request import DeletionRequest
from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.vehicle import Vehicle
from app.services.mileage import _recalculate_vehicle_mileage


def get_request_by_id(db: Session, request_id: int) -> DeletionRequest:
    req = db.query(DeletionRequest).filter(DeletionRequest.id == request_id).first()
    if not req:
        raise NotFoundError("Deletion request not found")
    return req


def get_all_requests(
    db: Session, status: str | None = None
) -> list[DeletionRequest]:
    q = db.query(DeletionRequest)
    if status:
        q = q.filter(DeletionRequest.status == status)
    return q.order_by(DeletionRequest.requested_at.desc()).all()


def get_requests_for_user(db: Session, user_id: int) -> list[DeletionRequest]:
    return (
        db.query(DeletionRequest)
        .filter(DeletionRequest.requested_by_user_id == user_id)
        .order_by(DeletionRequest.requested_at.desc())
        .all()
    )


def _get_target_record(db: Session, target_type: str, target_id: int):
    if target_type == "maintenance_record":
        record = (
            db.query(MaintenanceRecord)
            .filter(MaintenanceRecord.id == target_id, MaintenanceRecord.is_deleted == False)
            .first()
        )
    elif target_type == "mileage_record":
        record = (
            db.query(MileageRecord)
            .filter(MileageRecord.id == target_id, MileageRecord.is_deleted == False)
            .first()
        )
    else:
        record = None
    return record


def create_request(
    db: Session,
    target_type: str,
    target_id: int,
    requested_by_user_id: int,
    reason: str,
    user_role: str = "standard",
    user_id: int | None = None,
) -> DeletionRequest:
    record = _get_target_record(db, target_type, target_id)
    if not record:
        raise BusinessRuleError("Target record not found or already deleted")

    # Check that standard user owns the vehicle this record belongs to
    if user_role == "standard":
        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.id == record.vehicle_id, Vehicle.is_deleted == False)
            .first()
        )
        if not vehicle or vehicle.primary_driver_user_id != user_id:
            raise AuthorisationError(
                "You can only request deletion for records tied to your assigned vehicle"
            )

    pending = (
        db.query(DeletionRequest)
        .filter(
            DeletionRequest.target_type == target_type,
            DeletionRequest.target_id == target_id,
            DeletionRequest.status == "pending",
        )
        .first()
    )
    if pending:
        raise BusinessRuleError(
            "A pending deletion request already exists for this record"
        )

    req = DeletionRequest(
        target_type=target_type,
        target_id=target_id,
        requested_by_user_id=requested_by_user_id,
        reason=reason,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def review_request(
    db: Session,
    request_id: int,
    reviewed_by_user_id: int,
    action: str,
    review_notes: str = "",
) -> DeletionRequest:
    req = get_request_by_id(db, request_id)

    if req.status != "pending":
        raise BusinessRuleError("This request has already been reviewed")

    req.reviewed_by_user_id = reviewed_by_user_id
    req.review_notes = review_notes.strip() or None
    req.reviewed_at = datetime.now(timezone.utc)

    if action == "approve":
        req.status = "approved"
        record = _get_target_record(db, req.target_type, req.target_id)
        if record:
            record.is_deleted = True
            # Recalculate vehicle mileage if deleting a mileage or maintenance record
            if req.target_type in ("mileage_record", "maintenance_record"):
                vehicle = (
                    db.query(Vehicle)
                    .filter(Vehicle.id == record.vehicle_id, Vehicle.is_deleted == False)
                    .first()
                )
                if vehicle:
                    db.flush()
                    _recalculate_vehicle_mileage(db, vehicle)
    elif action == "reject":
        req.status = "rejected"

    db.commit()
    db.refresh(req)
    return req
