from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AppError
from app.schemas.mileage import MileageCreateSchema, MileageUpdateSchema
from app.security.csrf import validate_csrf_token
from app.services import mileage as mileage_service
from app.services import vehicle as vehicle_service
from app.utils.flash import flash
from app.utils.forms import parse_errors, safe_int
from app.utils.template import render

router = APIRouter(prefix="/mileage", tags=["mileage"])


def _form_vehicles(db: Session, user: dict):
    if user["role"] == "admin":
        vehicles = vehicle_service.get_all_vehicles(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
    return [v for v in vehicles if not v.is_retired and not v.is_deleted]


@router.get("")
async def mileage_list(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        records = mileage_service.get_all_records(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
        records = []
        for v in vehicles:
            records.extend(mileage_service.get_records_for_vehicle(db, v.id))
        records.sort(key=lambda r: r.recorded_at, reverse=True)

    return render(request, "mileage/list.html", {"records": records})


@router.get("/{record_id}")
async def mileage_detail_page(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        record = mileage_service.get_record_by_id(db, record_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    return render(request, "mileage/detail.html", {"record": record})


@router.get("/create")
async def mileage_create_page(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    vehicles = _form_vehicles(db, user)
    return_to = request.query_params.get("return_to", "")
    return_id = request.query_params.get("return_id", "")
    form_data = {"vehicle_id": request.query_params.get("vehicle_id", "")}
    return render(request, "mileage/create.html", {
        "vehicles": vehicles, "form_data": form_data,
        "return_to": return_to, "return_id": return_id,
    })


@router.post("/create")
async def mileage_create_post(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    form_data = dict(form)

    return_to = form_data.get("return_to", "")
    return_id = form_data.get("return_id", "")
    return_ctx = {"return_to": return_to, "return_id": return_id}

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        vehicles = _form_vehicles(db, user)
        return render(request, "mileage/create.html", {
            "vehicles": vehicles, "form_data": form_data,
            "errors": {"_general": "Invalid request."}, **return_ctx,
        })

    form_data["vehicle_id"] = safe_int(form_data.get("vehicle_id", ""))
    form_data["reading_value"] = safe_int(form_data.get("reading_value", ""))
    form_data["is_admin_override"] = form_data.get("is_admin_override") == "true"

    try:
        schema = MileageCreateSchema(**form_data)
    except PydanticValidationError as e:
        vehicles = _form_vehicles(db, user)
        return render(request, "mileage/create.html", {
            "vehicles": vehicles, "form_data": form_data, "errors": parse_errors(e), **return_ctx,
        })

    try:
        mileage_service.create_record(
            db,
            vehicle_id=schema.vehicle_id,
            recorded_by_user_id=user["id"],
            reading_value=schema.reading_value,
            is_admin_override=schema.is_admin_override,
            override_reason=schema.override_reason,
            user_role=user["role"],
            user_id=user["id"],
        )
    except AppError as e:
        vehicles = _form_vehicles(db, user)
        return render(request, "mileage/create.html", {
            "vehicles": vehicles, "form_data": form_data, "errors": {"_general": e.message}, **return_ctx,
        })

    flash(request.state.session_id, "Mileage record created.", "success")
    if return_to == "vehicle" and return_id:
        return RedirectResponse(f"/vehicles/{return_id}", status_code=303)
    elif return_to == "vehicles":
        return RedirectResponse("/vehicles", status_code=303)
    return RedirectResponse("/mileage", status_code=303)


@router.get("/{record_id}/edit")
async def mileage_edit_page(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    try:
        record = mileage_service.get_record_by_id(db, record_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    form_data = {
        "reading_value": record.reading_value,
        "is_admin_override": record.is_admin_override,
        "override_reason": record.override_reason or "",
    }
    return render(request, "mileage/edit.html", {"record": record, "form_data": form_data})


@router.post("/{record_id}/edit")
async def mileage_edit_post(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/mileage/{record_id}/edit", status_code=303)

    form_data["reading_value"] = safe_int(form_data.get("reading_value", ""))
    form_data["is_admin_override"] = form_data.get("is_admin_override") == "true"

    try:
        schema = MileageUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            record = mileage_service.get_record_by_id(db, record_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(request, "mileage/edit.html", {
            "record": record, "form_data": form_data, "errors": parse_errors(e),
        })

    try:
        mileage_service.update_record(
            db,
            record_id=record_id,
            reading_value=schema.reading_value,
            is_admin_override=schema.is_admin_override,
            override_reason=schema.override_reason,
        )
    except AppError as e:
        try:
            record = mileage_service.get_record_by_id(db, record_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(request, "mileage/edit.html", {
            "record": record, "form_data": form_data, "errors": {"_general": e.message},
        })

    flash(request.state.session_id, "Mileage record updated.", "success")
    return RedirectResponse("/mileage", status_code=303)


@router.post("/{record_id}/delete")
async def mileage_delete_post(request: Request, record_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    if not validate_csrf_token(form.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse("/mileage", status_code=303)

    try:
        mileage_service.soft_delete_record(db, record_id)
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse("/mileage", status_code=303)

    flash(request.state.session_id, "Mileage record deleted.", "success")
    return RedirectResponse("/mileage", status_code=303)
