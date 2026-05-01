from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deletion_request import DeletionRequest
from app.models.location import Location
from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.retirement_request import RetirementRequest
from app.models.user import User
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
        context["total_drivers"] = db.query(User).filter(User.role == "standard", User.is_active == True).count()
        context["pending_retirement"] = db.query(RetirementRequest).filter(RetirementRequest.status == "pending").count()
        context["pending_deletion"] = db.query(DeletionRequest).filter(DeletionRequest.status == "pending").count()

        # Stats per location
        locations = db.query(Location).filter(Location.is_deleted == False, Location.is_active == True).all()
        location_stats = []
        for loc in locations:
            vehicle_count = db.query(Vehicle).filter(
                Vehicle.location_id == loc.id, Vehicle.is_deleted == False
            ).count()
            active_count = db.query(Vehicle).filter(
                Vehicle.location_id == loc.id, Vehicle.status == "active", Vehicle.is_deleted == False
            ).count()
            driver_count = db.query(User).filter(
                User.location_id == loc.id, User.role == "standard", User.is_active == True
            ).count()
            location_stats.append({
                "name": loc.name,
                "code": loc.code,
                "vehicles": vehicle_count,
                "active_vehicles": active_count,
                "drivers": driver_count,
            })
        context["location_stats"] = location_stats

        context["recent_mileage"] = (
            db.query(MileageRecord)
            .filter(MileageRecord.is_deleted == False)
            .order_by(MileageRecord.recorded_at.desc())
            .limit(10)
            .all()
        )
        context["recent_maintenance"] = (
            db.query(MaintenanceRecord)
            .filter(MaintenanceRecord.is_deleted == False)
            .order_by(MaintenanceRecord.created_at.desc())
            .limit(10)
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
