from functools import wraps
from typing import Any

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exceptions import AuthorisationError
from app.security.csrf import validate_csrf_token


def get_current_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


def require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        return None
    return user


def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return None
    return user


async def verify_csrf(request: Request) -> bool:
    form = await request.form()
    token = form.get("csrf_token", "")
    if not validate_csrf_token(token):
        return False
    return True
