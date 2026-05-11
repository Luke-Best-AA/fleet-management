from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.security.csrf import generate_csrf_token
from app.services.session import get_flashes

templates = Jinja2Templates(directory="app/templates")


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
    }
    if context:
        ctx.update(context)

    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
