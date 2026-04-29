from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AppError
from app.schemas.vehicle import VehicleCreateSchema, VehicleUpdateSchema
from app.security.csrf import validate_csrf_token
from app.services import location as location_service
from app.services import user as user_service
from app.services import vehicle as vehicle_service
from app.utils.flash import flash
from app.utils.forms import parse_errors, safe_int, safe_int_or_none
from app.utils.template import render

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _vehicle_form_context(db: Session):
    return {
        "locations": location_service.get_all_locations(db, active_only=True),
        "drivers": user_service.get_standard_users(db),
        "vehicle_types": [
            {"value": "roadside_van", "label": "Roadside Van"},
            {"value": "flat_loader_lorry", "label": "Flat Loader Lorry"},
            {"value": "patrol_van", "label": "Patrol Van"},
        ],
    }


@router.get("")
async def vehicle_list(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        vehicles = vehicle_service.get_all_vehicles(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])

    return render(request, "vehicles/list.html", {"vehicles": vehicles})


@router.get("/create")
async def vehicle_create_page(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    context = _vehicle_form_context(db)
    return render(request, "vehicles/create.html", context)


@router.post("/create")
async def vehicle_create_post(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        context = _vehicle_form_context(db)
        context.update({"form_data": form_data, "errors": {"_general": "Invalid request."}})
        return render(request, "vehicles/create.html", context)

    # Convert form strings to appropriate types
    form_data["year"] = safe_int(form_data.get("year", ""))
    form_data["current_mileage"] = safe_int(form_data.get("current_mileage", "0"))
    form_data["location_id"] = safe_int(form_data.get("location_id", ""))
    form_data["primary_driver_user_id"] = safe_int_or_none(form_data.get("primary_driver_user_id", ""))

    try:
        schema = VehicleCreateSchema(**form_data)
    except PydanticValidationError as e:
        context = _vehicle_form_context(db)
        context.update({"form_data": form_data, "errors": parse_errors(e)})
        return render(request, "vehicles/create.html", context)

    try:
        vehicle_service.create_vehicle(db, **schema.model_dump())
    except AppError as e:
        context = _vehicle_form_context(db)
        context.update({"form_data": form_data, "errors": {"_general": e.message}})
        return render(request, "vehicles/create.html", context)

    flash(request.state.session_id, "Vehicle created successfully.", "success")
    return RedirectResponse("/vehicles", status_code=303)


@router.get("/{vehicle_id}")
async def vehicle_detail(request: Request, vehicle_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        vehicle = vehicle_service.get_vehicle_by_id(db, vehicle_id)
        vehicle_service.check_vehicle_access(vehicle, user)
    except AppError:
        return render(request, "errors/403.html", status_code=403)

    return render(request, "vehicles/detail.html", {"vehicle": vehicle})


@router.get("/{vehicle_id}/edit")
async def vehicle_edit_page(request: Request, vehicle_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    try:
        vehicle = vehicle_service.get_vehicle_by_id(db, vehicle_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    if vehicle.is_retired:
        flash(request.state.session_id, "Retired vehicles cannot be edited.", "warning")
        return RedirectResponse(f"/vehicles/{vehicle_id}", status_code=302)

    context = _vehicle_form_context(db)
    context["vehicle"] = vehicle
    context["form_data"] = {
        "registration_number": vehicle.registration_number,
        "fleet_reference": vehicle.fleet_reference,
        "vehicle_type": vehicle.vehicle_type,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "location_id": vehicle.location_id,
        "primary_driver_user_id": vehicle.primary_driver_user_id or "",
    }
    return render(request, "vehicles/edit.html", context)


@router.post("/{vehicle_id}/edit")
async def vehicle_edit_post(request: Request, vehicle_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        context = _vehicle_form_context(db)
        context.update({"form_data": form_data, "errors": {"_general": "Invalid request."}})
        return render(request, "vehicles/edit.html", context)

    form_data["year"] = safe_int(form_data.get("year", ""))
    form_data["location_id"] = safe_int(form_data.get("location_id", ""))
    form_data["primary_driver_user_id"] = safe_int_or_none(form_data.get("primary_driver_user_id", ""))

    try:
        schema = VehicleUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            vehicle = vehicle_service.get_vehicle_by_id(db, vehicle_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        context = _vehicle_form_context(db)
        context.update({"vehicle": vehicle, "form_data": form_data, "errors": parse_errors(e)})
        return render(request, "vehicles/edit.html", context)

    try:
        vehicle_service.update_vehicle(db, vehicle_id, **schema.model_dump())
    except AppError as e:
        try:
            vehicle = vehicle_service.get_vehicle_by_id(db, vehicle_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        context = _vehicle_form_context(db)
        context.update({"vehicle": vehicle, "form_data": form_data, "errors": {"_general": e.message}})
        return render(request, "vehicles/edit.html", context)

    flash(request.state.session_id, "Vehicle updated successfully.", "success")
    return RedirectResponse(f"/vehicles/{vehicle_id}", status_code=303)


@router.post("/{vehicle_id}/delete")
async def vehicle_delete_post(request: Request, vehicle_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    if not validate_csrf_token(form.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/vehicles/{vehicle_id}", status_code=303)

    try:
        vehicle_service.soft_delete_vehicle(db, vehicle_id)
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse(f"/vehicles/{vehicle_id}", status_code=303)

    flash(request.state.session_id, "Vehicle deleted.", "success")
    return RedirectResponse("/vehicles", status_code=303)
