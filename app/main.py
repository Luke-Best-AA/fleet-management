import logging
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.deletion_request import DeletionRequest  # noqa: F401

# Import all models so Base.metadata sees them
from app.models.location import Location  # noqa: F401
from app.models.maintenance import MaintenanceCategory, MaintenanceRecord  # noqa: F401
from app.models.mileage import MileageRecord  # noqa: F401
from app.models.page_visit import PageVisit  # noqa: F401
from app.models.retirement_request import RetirementRequest  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.services.session import get_session, make_client_fingerprint, refresh_session
from app.utils.template import render


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger = logging.getLogger("fleet.session")
        session_id = request.cookies.get("session_id")
        session_data = None

        if session_id:
            session_data = get_session(session_id)
            if not session_data:
                logger.warning(
                    "Session cookie present but Redis key missing: %s... (path=%s)",
                    session_id[:8],
                    request.url.path,
                )
            elif session_data.get("fingerprint"):
                expected = session_data["fingerprint"]
                actual = make_client_fingerprint(request.client.host, request.headers.get("user-agent", ""))
                if actual != expected:
                    logger.warning(
                        "Session fingerprint mismatch for %s... (path=%s)",
                        session_id[:8],
                        request.url.path,
                    )
                    session_data = None

        request.state.session_id = session_id if session_data else None
        request.state.session = session_data or {}
        request.state.user = None

        if session_data and "user_id" in session_data:
            request.state.user = {
                "id": session_data["user_id"],
                "username": session_data["username"],
                "role": session_data["role"],
                "first_name": session_data["first_name"],
            }
            # Refresh session TTL on each request so active users stay logged in
            refresh_session(session_id, session_data["user_id"])

        response = await call_next(request)

        # Refresh the cookie expiry on each authenticated request (sliding window)
        if session_data and session_id:
            response.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                secure=settings.SECURE_COOKIES,
                samesite="strict",
                max_age=settings.SESSION_LIFETIME_SECONDS,
                path="/",
            )
        elif session_id and not session_data:
            # Cookie exists but session is gone — clear the stale cookie
            response.delete_cookie("session_id", path="/")

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security response headers to mitigate common attacks."""

    async def dispatch(self, request: Request, call_next):
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'self'; "
            "form-action 'self'"
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        return response


# Paths excluded from page-visit tracking
_VISIT_SKIP_PREFIXES = ("/static", "/api", "/auth", "/favicon")


class PageVisitMiddleware(BaseHTTPMiddleware):
    """Records page visits for authenticated non-admin users."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only track successful GET page loads for non-admin users
        if (
            request.method == "GET"
            and request.state.user
            and request.state.user.get("role") != "admin"
            and response.status_code == 200
            and not request.url.path.startswith(_VISIT_SKIP_PREFIXES)
        ):
            try:
                from app.db.session import SessionLocal
                from app.services.page_visit import record_visit

                db = SessionLocal()
                try:
                    record_visit(db, user_id=request.state.user["id"], path=request.url.path)
                finally:
                    db.close()
            except Exception:  # noqa: S110  # nosec B110
                pass  # Never break page loads for analytics

        return response


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.add_middleware(PageVisitMiddleware)
    app.add_middleware(SessionMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Import and include routers
    from app.routes.api.inline import router as api_router
    from app.routes.web.admin import router as admin_router
    from app.routes.web.auth import router as auth_router
    from app.routes.web.dashboard import router as dashboard_router
    from app.routes.web.maintenance import router as maintenance_router
    from app.routes.web.mileage import router as mileage_router
    from app.routes.web.requests import router as requests_router
    from app.routes.web.vehicles import router as vehicles_router

    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(vehicles_router)
    app.include_router(maintenance_router)
    app.include_router(mileage_router)
    app.include_router(requests_router)
    app.include_router(admin_router)
    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        if request.state.user:
            return RedirectResponse("/dashboard", status_code=302)
        return RedirectResponse("/auth/login", status_code=302)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return render(request, "errors/404.html", status_code=404)

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        return render(request, "errors/500.html", status_code=500)

    return app


app = create_app()
