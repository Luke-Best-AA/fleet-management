from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.security.csrf import generate_csrf_token
from app.services.session import get_flashes

templates = Jinja2Templates(directory="app/templates")

# Paths that should never appear as a ?next= target
_NO_RETURN_PREFIXES = ("/auth/login", "/auth/logout", "/auth/register")


def login_redirect(request: Request, *, status_code: int = 302) -> RedirectResponse:
    """Redirect to login, preserving the current path as ?next= for return."""
    path = request.url.path
    if path and not path.startswith(_NO_RETURN_PREFIXES) and path != "/":
        return RedirectResponse(f"/auth/login?next={quote(path)}", status_code=status_code)
    return RedirectResponse("/auth/login", status_code=status_code)


def render(
    request: Request,
    template_name: str,
    context: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    session_id = getattr(request.state, "session_id", None)
    user = getattr(request.state, "user", None)

    ctx = {
        "request": request,
        "user": user,
        "flashes": get_flashes(session_id) if session_id else [],
        "csrf_token": generate_csrf_token(),
        "csp_nonce": getattr(request.state, "csp_nonce", ""),
    }
    if context:
        ctx.update(context)

    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
