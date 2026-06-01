from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.deletion_request import DeletionRequest
from app.models.location import Location
from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.retirement_request import RetirementRequest
from app.models.user import User
from app.models.vehicle import Vehicle
from app.utils.template import login_redirect, render

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return login_redirect(request)

    context = {}

    if user["role"] == "admin":
        # Collapse 3 vehicle COUNT queries into one
        vehicle_counts = (
            db.query(
                func.count(Vehicle.id).label("total"),
                func.sum(case((Vehicle.status == "active", 1), else_=0)).label("active"),
                func.sum(case((Vehicle.status == "retired", 1), else_=0)).label("retired"),
            )
            .filter(Vehicle.is_deleted == False)
            .one()
        )
        context["total_vehicles"] = vehicle_counts.total or 0
        context["active_vehicles"] = vehicle_counts.active or 0
        context["retired_vehicles"] = vehicle_counts.retired or 0

        context["total_drivers"] = db.query(User).filter(User.role == "standard", User.is_active == True).count()
        context["pending_retirement"] = (
            db.query(RetirementRequest).filter(RetirementRequest.status == "pending").count()
        )
        context["pending_deletion"] = db.query(DeletionRequest).filter(DeletionRequest.status == "pending").count()

        # Replace per-location query loop (3N queries) with 2 GROUP BY aggregations
        locations = db.query(Location).filter(Location.is_deleted == False, Location.is_active == True).all()

        vehicle_agg = {
            row.location_id: (row.vehicles, row.active_vehicles)
            for row in db.query(
                Vehicle.location_id,
                func.count(Vehicle.id).label("vehicles"),
                func.sum(case((Vehicle.status == "active", 1), else_=0)).label("active_vehicles"),
            )
            .filter(Vehicle.is_deleted == False)
            .group_by(Vehicle.location_id)
            .all()
        }
        driver_agg = {
            row.location_id: row.drivers
            for row in db.query(
                User.location_id,
                func.count(User.id).label("drivers"),
            )
            .filter(User.role == "standard", User.is_active == True)
            .group_by(User.location_id)
            .all()
        }
        context["location_stats"] = [
            {
                "id": loc.id,
                "name": loc.name,
                "code": loc.code,
                "vehicles": vehicle_agg.get(loc.id, (0, 0))[0],
                "active_vehicles": vehicle_agg.get(loc.id, (0, 0))[1],
                "drivers": driver_agg.get(loc.id, 0),
            }
            for loc in locations
        ]

        # Eager-load vehicle on mileage records (template accesses rec.vehicle)
        context["recent_mileage"] = (
            db.query(MileageRecord)
            .options(joinedload(MileageRecord.vehicle))
            .filter(MileageRecord.is_deleted == False)
            .order_by(MileageRecord.recorded_at.desc())
            .limit(10)
            .all()
        )
        # Eager-load vehicle and category on maintenance records
        context["recent_maintenance"] = (
            db.query(MaintenanceRecord)
            .options(joinedload(MaintenanceRecord.vehicle), joinedload(MaintenanceRecord.category))
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
        # Eager-load vehicle so the template doesn't lazy-query per row
        context["my_retirement_requests"] = (
            db.query(RetirementRequest)
            .options(joinedload(RetirementRequest.vehicle))
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
