from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AppError
from app.schemas.maintenance import (
    MaintenanceRecordCreateSchema,
    MaintenanceRecordUpdateSchema,
)
from app.security.csrf import validate_csrf_token
from app.services import maintenance as maint_service
from app.services import vehicle as vehicle_service
from app.utils.flash import flash
from app.utils.forms import parse_errors, safe_int, safe_date, safe_decimal
from app.utils.template import render

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _record_form_context(db: Session, user: dict):
    categories = maint_service.get_all_categories(db, active_only=True)
    if user["role"] == "admin":
        vehicles = vehicle_service.get_all_vehicles(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
    # Only active/pending vehicles
    vehicles = [v for v in vehicles if not v.is_retired and not v.is_deleted]
    return {"categories": categories, "vehicles": vehicles}


@router.get("")
async def maintenance_list(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        records = maint_service.get_all_records(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
        records = []
        for v in vehicles:
            records.extend(maint_service.get_records_for_vehicle(db, v.id))
        records.sort(key=lambda r: r.maintenance_date, reverse=True)

    return render(request, "maintenance/list.html", {"records": records})


@router.get("/create")
async def maintenance_create_page(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    context = _record_form_context(db, user)
    context["form_data"] = {
        "vehicle_id": request.query_params.get("vehicle_id", ""),
        "maintenance_date": str(date.today()),
    }
    context["return_to"] = request.query_params.get("return_to", "")
    context["return_id"] = request.query_params.get("return_id", "")
    return render(request, "maintenance/create.html", context)


@router.post("/create")
async def maintenance_create_post(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    form_data = dict(form)

    return_to = form_data.get("return_to", "")
    return_id = form_data.get("return_id", "")
    return_ctx = {"return_to": return_to, "return_id": return_id}

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        context = _record_form_context(db, user)
        context.update({"form_data": form_data, "errors": {"_general": "Invalid request."}, **return_ctx})
        return render(request, "maintenance/create.html", context)

    form_data["vehicle_id"] = safe_int(form_data.get("vehicle_id", ""))
    form_data["category_id"] = safe_int(form_data.get("category_id", ""))
    form_data["mileage_at_time"] = safe_int(form_data.get("mileage_at_time", ""))
    form_data["cost"] = safe_decimal(form_data.get("cost", ""))
    form_data["maintenance_date"] = safe_date(form_data.get("maintenance_date", ""))

    try:
        schema = MaintenanceRecordCreateSchema(**form_data)
    except PydanticValidationError as e:
        context = _record_form_context(db, user)
        context.update({"form_data": form_data, "errors": parse_errors(e), **return_ctx})
        return render(request, "maintenance/create.html", context)

    try:
        maint_service.create_record(
            db,
            vehicle_id=schema.vehicle_id,
            category_id=schema.category_id,
            logged_by_user_id=user["id"],
            maintenance_date=schema.maintenance_date,
            mileage_at_time=schema.mileage_at_time,
            notes=schema.notes,
            cost=schema.cost,
            user_role=user["role"],
            user_vehicle_id=user["id"],
        )
    except AppError as e:
        context = _record_form_context(db, user)
        context.update({"form_data": form_data, "errors": {"_general": e.message}, **return_ctx})
        return render(request, "maintenance/create.html", context)

    flash(request.state.session_id, "Maintenance record created.", "success")

    return_to = form_data.get("return_to", "")
    return_id = form_data.get("return_id", "")
    if return_to == "vehicle" and return_id:
        return RedirectResponse(f"/vehicles/{return_id}", status_code=303)
    elif return_to == "vehicles":
        return RedirectResponse("/vehicles", status_code=303)
    return RedirectResponse("/maintenance", status_code=303)


@router.get("/{record_id}")
async def maintenance_detail_page(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        record = maint_service.get_record_by_id(db, record_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    return_to = request.query_params.get("return_to", "")
    return_id = request.query_params.get("return_id", "")
    return render(request, "maintenance/detail.html", {
        "record": record, "return_to": return_to, "return_id": return_id,
    })


@router.get("/{record_id}/edit")
async def maintenance_edit_page(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    try:
        record = maint_service.get_record_by_id(db, record_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    context = _record_form_context(db, user)
    context["record"] = record
    context["form_data"] = {
        "category_id": record.category_id,
        "maintenance_date": str(record.maintenance_date),
        "mileage_at_time": record.mileage_at_time,
        "notes": record.notes or "",
        "cost": str(record.cost) if record.cost else "",
    }
    return render(request, "maintenance/edit.html", context)


@router.post("/{record_id}/edit")
async def maintenance_edit_post(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/maintenance/{record_id}/edit", status_code=303)

    form_data["category_id"] = safe_int(form_data.get("category_id", ""))
    form_data["mileage_at_time"] = safe_int(form_data.get("mileage_at_time", ""))
    form_data["cost"] = safe_decimal(form_data.get("cost", ""))
    form_data["maintenance_date"] = safe_date(form_data.get("maintenance_date", ""))

    try:
        schema = MaintenanceRecordUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            record = maint_service.get_record_by_id(db, record_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        context = _record_form_context(db, user)
        context.update({"record": record, "form_data": form_data, "errors": parse_errors(e)})
        return render(request, "maintenance/edit.html", context)

    try:
        maint_service.update_record(
            db,
            record_id=record_id,
            category_id=schema.category_id,
            maintenance_date=schema.maintenance_date,
            mileage_at_time=schema.mileage_at_time,
            notes=schema.notes,
            cost=schema.cost,
        )
    except AppError as e:
        try:
            record = maint_service.get_record_by_id(db, record_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        context = _record_form_context(db, user)
        context.update({"record": record, "form_data": form_data, "errors": {"_general": e.message}})
        return render(request, "maintenance/edit.html", context)

    flash(request.state.session_id, "Maintenance record updated.", "success")
    return RedirectResponse("/maintenance", status_code=303)


@router.post("/{record_id}/delete")
async def maintenance_delete_post(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    if not validate_csrf_token(form.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse("/maintenance", status_code=303)

    try:
        maint_service.soft_delete_record(db, record_id)
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse("/maintenance", status_code=303)

    flash(request.state.session_id, "Maintenance record deleted.", "success")
    return RedirectResponse("/maintenance", status_code=303)
