from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AppError
from app.schemas.requests import (
    DeletionRequestCreateSchema,
    DeletionRequestReviewSchema,
    RetirementRequestCreateSchema,
    RetirementRequestReviewSchema,
)
from app.security.csrf import validate_csrf_token
from app.services import deletion as deletion_service
from app.services import maintenance as maint_service
from app.services import mileage as mileage_service
from app.services import retirement as retirement_service
from app.services import vehicle as vehicle_service
from app.utils.flash import flash
from app.utils.forms import parse_errors, safe_int
from app.utils.template import render

router = APIRouter(prefix="/requests", tags=["requests"])


# --- Retirement Requests ---

@router.get("/retirement")
async def retirement_list(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        requests_list = retirement_service.get_all_requests(db)
    else:
        requests_list = retirement_service.get_requests_for_user(db, user["id"])

    return render(request, "requests/retirement_list.html", {"requests": requests_list})


@router.get("/retirement/create")
async def retirement_create_page(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        vehicles = vehicle_service.get_all_vehicles(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
    vehicles = [v for v in vehicles if v.is_active_status]

    form_data = {"vehicle_id": request.query_params.get("vehicle_id", "")}
    return render(request, "requests/retirement_create.html", {"vehicles": vehicles, "form_data": form_data})


@router.post("/retirement/create")
async def retirement_create_post(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return RedirectResponse("/requests/retirement/create", status_code=303)

    form_data["vehicle_id"] = safe_int(form_data.get("vehicle_id", ""))

    try:
        schema = RetirementRequestCreateSchema(**form_data)
    except PydanticValidationError as e:
        if user["role"] == "admin":
            vehicles = vehicle_service.get_all_vehicles(db)
        else:
            vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
        vehicles = [v for v in vehicles if v.is_active_status]
        return render(request, "requests/retirement_create.html", {
            "vehicles": vehicles, "form_data": form_data, "errors": parse_errors(e),
        })

    try:
        if user["role"] == "admin":
            retirement_service.retire_vehicle_directly(
                db,
                vehicle_id=schema.vehicle_id,
                reason=schema.reason,
                admin_user_id=user["id"],
            )
            flash(request.state.session_id, "Vehicle retired successfully.", "success")
        else:
            retirement_service.create_request(
                db,
                vehicle_id=schema.vehicle_id,
                requested_by_user_id=user["id"],
                reason=schema.reason,
                user_role=user["role"],
                user_id=user["id"],
            )
            flash(request.state.session_id, "Retirement request submitted.", "success")
    except AppError as e:
        if user["role"] == "admin":
            vehicles = vehicle_service.get_all_vehicles(db)
        else:
            vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
        vehicles = [v for v in vehicles if v.is_active_status]
        return render(request, "requests/retirement_create.html", {
            "vehicles": vehicles, "form_data": form_data, "errors": {"_general": e.message},
        })

    if user["role"] == "admin":
        return RedirectResponse("/vehicles", status_code=303)
    return RedirectResponse("/requests/retirement", status_code=303)


@router.get("/retirement/{request_id}")
async def retirement_review_page(request: Request, request_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        req = retirement_service.get_request_by_id(db, request_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    return render(request, "requests/retirement_detail.html", {"req": req})


@router.post("/retirement/{request_id}/review")
async def retirement_review_post(request: Request, request_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/requests/retirement/{request_id}", status_code=303)

    try:
        schema = RetirementRequestReviewSchema(**form_data)
    except PydanticValidationError as e:
        flash(request.state.session_id, "Invalid review data.", "danger")
        return RedirectResponse(f"/requests/retirement/{request_id}", status_code=303)

    try:
        retirement_service.review_request(
            db,
            request_id=request_id,
            reviewed_by_user_id=user["id"],
            action=schema.action,
            review_notes=schema.review_notes,
        )
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse(f"/requests/retirement/{request_id}", status_code=303)

    action_label = "approved" if schema.action == "approve" else "rejected"
    flash(request.state.session_id, f"Retirement request {action_label}.", "success")
    return RedirectResponse("/requests/retirement", status_code=303)


# --- Deletion Requests ---

@router.get("/deletion")
async def deletion_list(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if user["role"] == "admin":
        requests_list = deletion_service.get_all_requests(db)
    else:
        requests_list = deletion_service.get_requests_for_user(db, user["id"])

    return render(request, "requests/deletion_list.html", {"requests": requests_list})


@router.get("/deletion/create")
async def deletion_create_page(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    form_data = {
        "target_type": request.query_params.get("target_type", ""),
        "target_id": request.query_params.get("target_id", ""),
    }

    if user["role"] == "admin":
        mileage_records = mileage_service.get_all_records(db)
        maintenance_records = maint_service.get_all_records(db)
    else:
        vehicles = vehicle_service.get_vehicles_for_user(db, user["id"])
        mileage_records = []
        maintenance_records = []
        for v in vehicles:
            mileage_records.extend(mileage_service.get_records_for_vehicle(db, v.id))
            maintenance_records.extend(maint_service.get_records_for_vehicle(db, v.id))
        mileage_records.sort(key=lambda r: r.recorded_at, reverse=True)
        maintenance_records.sort(key=lambda r: r.maintenance_date, reverse=True)

    return render(request, "requests/deletion_create.html", {
        "form_data": form_data,
        "mileage_records": mileage_records,
        "maintenance_records": maintenance_records,
    })


@router.post("/deletion/create")
async def deletion_create_post(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return RedirectResponse("/requests/deletion/create", status_code=303)

    form_data["target_id"] = safe_int(form_data.get("target_id", ""))

    try:
        schema = DeletionRequestCreateSchema(**form_data)
    except PydanticValidationError as e:
        return render(request, "requests/deletion_create.html", {
            "form_data": form_data, "errors": parse_errors(e),
        })

    try:
        deletion_service.create_request(
            db,
            target_type=schema.target_type,
            target_id=schema.target_id,
            requested_by_user_id=user["id"],
            reason=schema.reason,
            user_role=user["role"],
            user_id=user["id"],
        )
    except AppError as e:
        return render(request, "requests/deletion_create.html", {
            "form_data": form_data, "errors": {"_general": e.message},
        })

    flash(request.state.session_id, "Deletion request submitted.", "success")
    return RedirectResponse("/requests/deletion", status_code=303)


@router.get("/deletion/{request_id}")
async def deletion_detail_page(request: Request, request_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        req = deletion_service.get_request_by_id(db, request_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    return render(request, "requests/deletion_detail.html", {"req": req})


@router.post("/deletion/{request_id}/review")
async def deletion_review_post(request: Request, request_id: int, db: Session = Depends(get_db)):
    user = request.state.user
    if not user or user["role"] != "admin":
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/requests/deletion/{request_id}", status_code=303)

    try:
        schema = DeletionRequestReviewSchema(**form_data)
    except PydanticValidationError as e:
        flash(request.state.session_id, "Invalid review data.", "danger")
        return RedirectResponse(f"/requests/deletion/{request_id}", status_code=303)

    try:
        deletion_service.review_request(
            db,
            request_id=request_id,
            reviewed_by_user_id=user["id"],
            action=schema.action,
            review_notes=schema.review_notes,
        )
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse(f"/requests/deletion/{request_id}", status_code=303)

    action_label = "approved" if schema.action == "approve" else "rejected"
    flash(request.state.session_id, f"Deletion request {action_label}.", "success")
    return RedirectResponse("/requests/deletion", status_code=303)
