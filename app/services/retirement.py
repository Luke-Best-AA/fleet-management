from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions import AuthorisationError, BusinessRuleError, NotFoundError
from app.models.retirement_request import RetirementRequest
from app.models.vehicle import Vehicle


def get_request_by_id(db: Session, request_id: int) -> RetirementRequest:
    req = db.query(RetirementRequest).filter(RetirementRequest.id == request_id).first()
    if not req:
        raise NotFoundError("Retirement request not found")
    return req


def get_all_requests(db: Session, status: str | None = None) -> list[RetirementRequest]:
    q = db.query(RetirementRequest)
    if status:
        q = q.filter(RetirementRequest.status == status)
    return q.order_by(RetirementRequest.requested_at.desc()).all()


def get_requests_for_user(db: Session, user_id: int) -> list[RetirementRequest]:
    return (
        db.query(RetirementRequest)
        .filter(RetirementRequest.requested_by_user_id == user_id)
        .order_by(RetirementRequest.requested_at.desc())
        .all()
    )


def create_request(
    db: Session,
    vehicle_id: int,
    requested_by_user_id: int,
    reason: str,
    user_role: str = "standard",
    user_id: int | None = None,
) -> RetirementRequest:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.is_deleted == False)
        .first()
    )
    if not vehicle:
        raise BusinessRuleError("Vehicle not found or has been deleted")

    if not vehicle.is_active_status:
        raise BusinessRuleError("Vehicle must be active to request retirement")

    if user_role == "standard" and vehicle.primary_driver_user_id != user_id:
        raise AuthorisationError(
            "You can only request retirement for your assigned vehicle"
        )

    pending = (
        db.query(RetirementRequest)
        .filter(
            RetirementRequest.vehicle_id == vehicle_id,
            RetirementRequest.status == "pending",
        )
        .first()
    )
    if pending:
        raise BusinessRuleError(
            "A pending retirement request already exists for this vehicle"
        )

    vehicle.status = "pending_retirement"

    req = RetirementRequest(
        vehicle_id=vehicle_id,
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
) -> RetirementRequest:
    req = get_request_by_id(db, request_id)

    if req.status != "pending":
        raise BusinessRuleError("This request has already been reviewed")

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == req.vehicle_id)
        .first()
    )

    req.reviewed_by_user_id = reviewed_by_user_id
    req.review_notes = review_notes.strip() or None
    req.reviewed_at = datetime.now(timezone.utc)

    if action == "approve":
        req.status = "approved"
        if vehicle:
            vehicle.status = "retired"
            vehicle.retirement_reason = req.reason
    elif action == "reject":
        req.status = "rejected"
        if vehicle:
            vehicle.status = "active"

    db.commit()
    db.refresh(req)
    return req
