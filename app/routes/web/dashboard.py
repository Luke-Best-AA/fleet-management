from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deletion_request import DeletionRequest
from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.retirement_request import RetirementRequest
from app.models.vehicle import Vehicle
from app.utils.template import render

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    context = {}

    if user["role"] == "admin":
        context["total_vehicles"] = db.query(Vehicle).filter(Vehicle.is_deleted == False).count()
        context["active_vehicles"] = db.query(Vehicle).filter(Vehicle.status == "active", Vehicle.is_deleted == False).count()
        context["retired_vehicles"] = db.query(Vehicle).filter(Vehicle.status == "retired", Vehicle.is_deleted == False).count()
        context["pending_retirement"] = db.query(RetirementRequest).filter(RetirementRequest.status == "pending").count()
        context["pending_deletion"] = db.query(DeletionRequest).filter(DeletionRequest.status == "pending").count()
        context["recent_mileage"] = (
            db.query(MileageRecord)
            .filter(MileageRecord.is_deleted == False)
            .order_by(MileageRecord.recorded_at.desc())
            .limit(5)
            .all()
        )
        context["recent_maintenance"] = (
            db.query(MaintenanceRecord)
            .filter(MaintenanceRecord.is_deleted == False)
            .order_by(MaintenanceRecord.created_at.desc())
            .limit(5)
            .all()
        )
    else:
        vehicles = (
            db.query(Vehicle)
            .filter(
                Vehicle.primary_driver_user_id == user["id"],
                Vehicle.is_deleted == False,
            )
            .all()
        )
        context["vehicles"] = vehicles
        context["my_retirement_requests"] = (
            db.query(RetirementRequest)
            .filter(RetirementRequest.requested_by_user_id == user["id"])
            .order_by(RetirementRequest.requested_at.desc())
            .limit(5)
            .all()
        )
        context["my_deletion_requests"] = (
            db.query(DeletionRequest)
            .filter(DeletionRequest.requested_by_user_id == user["id"])
            .order_by(DeletionRequest.requested_at.desc())
            .limit(5)
            .all()
        )

    return render(request, "dashboard.html", context)
