from app.services.session import add_flash as _add_flash


def flash(session_id: str, message: str, category: str = "info") -> None:
    _add_flash(session_id, message, category)
