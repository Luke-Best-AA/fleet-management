from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AuthenticationError, LockedOutError
from app.models.deletion_request import DeletionRequest
from app.models.retirement_request import RetirementRequest
from app.schemas.auth import ChangePasswordSchema, LoginSchema, RegisterSchema
from app.security.csrf import validate_csrf_token
from app.services import auth as auth_service
from app.services import session as session_service
from app.services import user as user_service
from app.services.session import make_client_fingerprint
from app.utils.flash import flash
from app.utils.forms import parse_errors
from app.utils.template import render

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login_page(request: Request):
    if request.state.user:
        return RedirectResponse("/dashboard", status_code=302)
    return render(request, "auth/login.html")


@router.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return render(
            request,
            "auth/login.html",
            {"form_data": form_data, "errors": {"_general": "Invalid request. Please try again."}},
        )

    try:
        schema = LoginSchema(**form_data)
    except PydanticValidationError as e:
        return render(
            request,
            "auth/login.html",
            {"form_data": form_data, "errors": parse_errors(e)},
        )

    fingerprint = make_client_fingerprint(
        request.client.host, request.headers.get("user-agent", "")
    )

    try:
        session_id, user = auth_service.login(db, schema.username, schema.password, fingerprint=fingerprint)
    except LockedOutError as e:
        return render(
            request,
            "auth/login.html",
            {"form_data": form_data, "errors": {"_general": e.message}},
        )
    except AuthenticationError as e:
        return render(
            request,
            "auth/login.html",
            {"form_data": form_data, "errors": {"_general": e.message}},
        )

    welcome_msg = f"Welcome back, {user.first_name}!"
    if user.role == "admin":
        pending = (
            db.query(RetirementRequest).filter(RetirementRequest.status == "pending").count()
            + db.query(DeletionRequest).filter(DeletionRequest.status == "pending").count()
        )
        if pending > 0:
            welcome_msg += f" You have {pending} pending request{'s' if pending != 1 else ''}."
    flash(session_id, welcome_msg, "success")
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=session_service.settings.SECURE_COOKIES,
        samesite="strict",
        max_age=session_service.settings.SESSION_LIFETIME_SECONDS,
        path="/",
    )
    return response


@router.post("/logout")
async def logout_post(request: Request):
    session_id = request.state.session_id
    if session_id:
        auth_service.logout(session_id)
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie("session_id")
    return response


@router.get("/register")
async def register_page(request: Request):
    if request.state.user:
        return RedirectResponse("/dashboard", status_code=302)
    return render(request, "auth/register.html")


@router.post("/register")
async def register_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return render(
            request,
            "auth/register.html",
            {"form_data": form_data, "errors": {"_general": "Invalid request. Please try again."}},
        )

    try:
        schema = RegisterSchema(**form_data)
    except PydanticValidationError as e:
        return render(
            request,
            "auth/register.html",
            {"form_data": form_data, "errors": parse_errors(e)},
        )

    try:
        user_service.create_user(
            db,
            username=schema.username,
            email=schema.email,
            password=schema.password,
            first_name=schema.first_name,
            last_name=schema.last_name,
            role="standard",
            employee_number=schema.employee_number,
        )
    except Exception as e:
        return render(
            request,
            "auth/register.html",
            {"form_data": form_data, "errors": {"_general": str(e)}},
        )

    # Log the user in automatically
    fingerprint = make_client_fingerprint(
        request.client.host, request.headers.get("user-agent", "")
    )
    session_id, user = auth_service.login(db, schema.username, schema.password, fingerprint=fingerprint)
    flash(session_id, "Registration successful! Welcome.", "success")
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=session_service.settings.SECURE_COOKIES,
        samesite="strict",
        max_age=session_service.settings.SESSION_LIFETIME_SECONDS,
        path="/",
    )
    return response


@router.get("/change-password")
async def change_password_page(request: Request):
    if not request.state.user:
        return RedirectResponse("/auth/login", status_code=302)
    return render(request, "auth/change_password.html")


@router.post("/change-password")
async def change_password_post(request: Request, db: Session = Depends(get_db)):
    if not request.state.user:
        return RedirectResponse("/auth/login", status_code=302)

    form = await request.form()
    form_data = dict(form)

    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return render(
            request,
            "auth/change_password.html",
            {"errors": {"_general": "Invalid request. Please try again."}},
        )

    try:
        schema = ChangePasswordSchema(**form_data)
    except PydanticValidationError as e:
        return render(
            request,
            "auth/change_password.html",
            {"errors": parse_errors(e)},
        )

    try:
        auth_service.change_password(
            db, request.state.user["id"], schema.current_password, schema.new_password
        )
    except AuthenticationError as e:
        return render(
            request,
            "auth/change_password.html",
            {"errors": {"current_password": e.message}},
        )

    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie("session_id")
    return response
