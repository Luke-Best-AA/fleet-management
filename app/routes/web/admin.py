from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AppError
from app.schemas.location import LocationCreateSchema, LocationUpdateSchema
from app.schemas.maintenance import (
    MaintenanceCategoryCreateSchema,
    MaintenanceCategoryUpdateSchema,
)
from app.schemas.user import UserCreateSchema, UserUpdateSchema
from app.security.csrf import validate_csrf_token
from app.services import audit as audit_service
from app.services import location as location_service
from app.services import maintenance as maint_service
from app.services import page_visit as page_visit_service
from app.services import user as user_service
from app.utils.flash import flash
from app.utils.forms import parse_errors, safe_int_or_none
from app.utils.template import render

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(request: Request):
    user = request.state.user
    if not user or user["role"] != "admin":
        return None
    return user


# --- Locations ---


@router.get("/locations")
async def location_list(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    locations = location_service.get_all_locations(db)
    return render(request, "admin/locations/list.html", {"locations": locations})


@router.get("/locations/create")
async def location_create_page(request: Request):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    return render(request, "admin/locations/create.html")


@router.post("/locations/create")
async def location_create_post(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return render(
            request,
            "admin/locations/create.html",
            {
                "form_data": form_data,
                "errors": {"_general": "Invalid request."},
            },
        )

    try:
        schema = LocationCreateSchema(**form_data)
    except PydanticValidationError as e:
        return render(
            request,
            "admin/locations/create.html",
            {
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        loc = location_service.create_location(db, **schema.model_dump())
    except AppError as e:
        return render(
            request,
            "admin/locations/create.html",
            {
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(
        db, user_id=admin["id"], action="create", target_type="location", target_id=loc.id, target_label=loc.name
    )
    flash(request.state.session_id, "Location created.", "success")
    return RedirectResponse("/admin/locations", status_code=303)


@router.get("/locations/{location_id}/edit")
async def location_edit_page(request: Request, location_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    try:
        loc = location_service.get_location_by_id(db, location_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    form_data = {
        "name": loc.name,
        "code": loc.code,
        "region": loc.region or "",
        "address_line_1": loc.address_line_1 or "",
        "address_line_2": loc.address_line_2 or "",
        "city": loc.city or "",
        "postcode": loc.postcode or "",
        "is_active": loc.is_active,
    }
    return render(request, "admin/locations/edit.html", {"location": loc, "form_data": form_data})


@router.post("/locations/{location_id}/edit")
async def location_edit_post(request: Request, location_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)
    form_data["is_active"] = form_data.get("is_active") == "true"

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        try:
            loc = location_service.get_location_by_id(db, location_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "admin/locations/edit.html",
            {
                "location": loc,
                "form_data": form_data,
                "errors": {"_general": "Invalid request."},
            },
        )

    try:
        schema = LocationUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            loc = location_service.get_location_by_id(db, location_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "admin/locations/edit.html",
            {
                "location": loc,
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        location_service.update_location(db, location_id, **schema.model_dump())
    except AppError as e:
        try:
            loc = location_service.get_location_by_id(db, location_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "admin/locations/edit.html",
            {
                "location": loc,
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(
        db,
        user_id=admin["id"],
        action="update",
        target_type="location",
        target_id=location_id,
        target_label=schema.name,
    )
    flash(request.state.session_id, "Location updated.", "success")
    return RedirectResponse("/admin/locations", status_code=303)


@router.post("/locations/{location_id}/delete")
async def location_delete_post(request: Request, location_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    if not validate_csrf_token(form.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse("/admin/locations", status_code=303)

    try:
        location_service.soft_delete_location(db, location_id)
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse("/admin/locations", status_code=303)

    admin = _require_admin(request)
    audit_service.log_action(db, user_id=admin["id"], action="delete", target_type="location", target_id=location_id)
    flash(request.state.session_id, "Location deleted.", "success")
    return RedirectResponse("/admin/locations", status_code=303)


# --- Maintenance Categories ---


@router.get("/categories")
async def category_list(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    categories = maint_service.get_all_categories(db)
    return render(request, "admin/categories/list.html", {"categories": categories})


@router.get("/categories/create")
async def category_create_page(request: Request):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    return render(request, "admin/categories/create.html")


@router.post("/categories/create")
async def category_create_post(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)
    form_data["requires_notes"] = form_data.get("requires_notes") == "true"

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return render(
            request,
            "admin/categories/create.html",
            {
                "form_data": form_data,
                "errors": {"_general": "Invalid request."},
            },
        )

    try:
        schema = MaintenanceCategoryCreateSchema(**form_data)
    except PydanticValidationError as e:
        return render(
            request,
            "admin/categories/create.html",
            {
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        cat = maint_service.create_category(db, **schema.model_dump())
    except AppError as e:
        return render(
            request,
            "admin/categories/create.html",
            {
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(
        db, user_id=admin["id"], action="create", target_type="category", target_id=cat.id, target_label=cat.name
    )
    flash(request.state.session_id, "Category created.", "success")
    return RedirectResponse("/admin/categories", status_code=303)


@router.get("/categories/{category_id}/edit")
async def category_edit_page(request: Request, category_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    try:
        cat = maint_service.get_category_by_id(db, category_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    form_data = {
        "name": cat.name,
        "description": cat.description or "",
        "requires_notes": cat.requires_notes,
        "is_active": cat.is_active,
    }
    return render(request, "admin/categories/edit.html", {"category": cat, "form_data": form_data})


@router.post("/categories/{category_id}/edit")
async def category_edit_post(request: Request, category_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)
    form_data["requires_notes"] = form_data.get("requires_notes") == "true"
    form_data["is_active"] = form_data.get("is_active") == "true"

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/admin/categories/{category_id}/edit", status_code=303)

    try:
        schema = MaintenanceCategoryUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            cat = maint_service.get_category_by_id(db, category_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "admin/categories/edit.html",
            {
                "category": cat,
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        maint_service.update_category(db, category_id, **schema.model_dump())
    except AppError as e:
        try:
            cat = maint_service.get_category_by_id(db, category_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        return render(
            request,
            "admin/categories/edit.html",
            {
                "category": cat,
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(
        db,
        user_id=admin["id"],
        action="update",
        target_type="category",
        target_id=category_id,
        target_label=schema.name,
    )
    flash(request.state.session_id, "Category updated.", "success")
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
async def category_delete_post(request: Request, category_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    if not validate_csrf_token(form.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse("/admin/categories", status_code=303)

    try:
        maint_service.soft_delete_category(db, category_id)
    except AppError as e:
        flash(request.state.session_id, e.message, "danger")
        return RedirectResponse("/admin/categories", status_code=303)

    admin = _require_admin(request)
    audit_service.log_action(db, user_id=admin["id"], action="delete", target_type="category", target_id=category_id)
    flash(request.state.session_id, "Category deleted.", "success")
    return RedirectResponse("/admin/categories", status_code=303)


# --- Users ---


@router.get("/users")
async def user_list(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    role = request.query_params.get("role")
    if role == "standard":
        users = user_service.get_standard_users(db, active_only=False)
    else:
        users = user_service.get_all_users(db)
        role = None
    return render(request, "admin/users/list.html", {"users": users, "role_filter": role})


@router.get("/users/create")
async def user_create_page(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)
    locations = location_service.get_all_locations(db, active_only=True)
    return render(request, "admin/users/create.html", {"locations": locations})


@router.post("/users/create")
async def user_create_post(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        locations = location_service.get_all_locations(db, active_only=True)
        return render(
            request,
            "admin/users/create.html",
            {
                "locations": locations,
                "form_data": form_data,
                "errors": {"_general": "Invalid request."},
            },
        )

    try:
        loc_id = form_data.get("location_id", "")
        form_data["location_id"] = int(loc_id) if loc_id else None
    except (ValueError, TypeError):
        form_data["location_id"] = None

    try:
        schema = UserCreateSchema(**form_data)
    except PydanticValidationError as e:
        locations = location_service.get_all_locations(db, active_only=True)
        return render(
            request,
            "admin/users/create.html",
            {
                "locations": locations,
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        user_service.create_user(
            db,
            username=schema.username,
            email=schema.email,
            password=schema.password,
            first_name=schema.first_name,
            last_name=schema.last_name,
            role=schema.role,
            employee_number=schema.employee_number,
            location_id=schema.location_id,
            requesting_user_role="admin",
        )
    except AppError as e:
        locations = location_service.get_all_locations(db, active_only=True)
        return render(
            request,
            "admin/users/create.html",
            {
                "locations": locations,
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(db, user_id=admin["id"], action="create", target_type="user", target_label=schema.username)
    flash(request.state.session_id, "User created.", "success")
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/users/{user_id}")
async def user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    try:
        target_user = user_service.get_user_by_id(db, user_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    return render(request, "admin/users/detail.html", {"target_user": target_user})


@router.get("/users/{user_id}/edit")
async def user_edit_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    try:
        target_user = user_service.get_user_by_id(db, user_id)
    except AppError:
        return render(request, "errors/404.html", status_code=404)

    locations = location_service.get_all_locations(db, active_only=True)
    form_data = {
        "first_name": target_user.first_name,
        "last_name": target_user.last_name,
        "email": target_user.email,
        "employee_number": target_user.employee_number or "",
        "location_id": target_user.location_id or "",
        "is_active": target_user.is_active,
    }
    return render(
        request,
        "admin/users/edit.html",
        {
            "target_user": target_user,
            "locations": locations,
            "form_data": form_data,
        },
    )


@router.post("/users/{user_id}/edit")
async def user_edit_post(request: Request, user_id: int, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    form = await request.form()
    form_data = dict(form)
    form_data["is_active"] = form_data.get("is_active") == "true"

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        flash(request.state.session_id, "Invalid request.", "danger")
        return RedirectResponse(f"/admin/users/{user_id}/edit", status_code=303)

    try:
        loc_id = form_data.get("location_id", "")
        form_data["location_id"] = int(loc_id) if loc_id else None
    except (ValueError, TypeError):
        form_data["location_id"] = None

    try:
        schema = UserUpdateSchema(**form_data)
    except PydanticValidationError as e:
        try:
            target_user = user_service.get_user_by_id(db, user_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        locations = location_service.get_all_locations(db, active_only=True)
        return render(
            request,
            "admin/users/edit.html",
            {
                "target_user": target_user,
                "locations": locations,
                "form_data": form_data,
                "errors": parse_errors(e),
            },
        )

    try:
        user_service.update_user(db, user_id, **schema.model_dump())
    except AppError as e:
        try:
            target_user = user_service.get_user_by_id(db, user_id)
        except AppError:
            return render(request, "errors/404.html", status_code=404)
        locations = location_service.get_all_locations(db, active_only=True)
        return render(
            request,
            "admin/users/edit.html",
            {
                "target_user": target_user,
                "locations": locations,
                "form_data": form_data,
                "errors": {"_general": e.message},
            },
        )

    admin = _require_admin(request)
    audit_service.log_action(
        db, user_id=admin["id"], action="update", target_type="user", target_id=user_id, target_label=schema.email
    )
    flash(request.state.session_id, "User updated.", "success")
    return RedirectResponse("/admin/users", status_code=303)


# --- Audit Log ---


@router.get("/audit-log")
async def audit_log_page(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    page = int(request.query_params.get("page", 1))
    per_page = 50
    offset = (page - 1) * per_page

    total = audit_service.count_audit_logs(db)
    logs = audit_service.get_audit_logs(db, limit=per_page, offset=offset)
    total_pages = (total + per_page - 1) // per_page

    return render(
        request,
        "admin/audit_log.html",
        {
            "logs": logs,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


# --- Page Visits ---


@router.get("/page-visits")
async def page_visits_page(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return render(request, "errors/403.html", status_code=403)

    page = int(request.query_params.get("page", 1))
    user_id = safe_int_or_none(request.query_params.get("user_id"))
    days = int(request.query_params.get("days", 7))
    per_page = 50
    offset = (page - 1) * per_page

    total = page_visit_service.count_visits(db, user_id=user_id, days=days)
    visits = page_visit_service.get_visits(db, limit=per_page, offset=offset, user_id=user_id, days=days)
    total_pages = (total + per_page - 1) // per_page

    popular_pages = page_visit_service.get_popular_pages(db, days=days)
    active_users = page_visit_service.get_active_users(db, days=days)
    daily_visits = page_visit_service.get_daily_visits(db, days=days, user_id=user_id)
    hourly_dist = page_visit_service.get_hourly_distribution(db, days=days, user_id=user_id)

    # Non-admin users for filter dropdown
    standard_users = user_service.get_standard_users(db, active_only=False)

    return render(
        request,
        "admin/page_visits.html",
        {
            "visits": visits,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "popular_pages": popular_pages,
            "active_users": active_users,
            "daily_visits": daily_visits,
            "hourly_dist": hourly_dist,
            "standard_users": standard_users,
            "filter_user_id": user_id,
            "filter_days": days,
        },
    )
