import hmac
import secrets
import time

from app.config import settings


def generate_csrf_token() -> str:
    timestamp = str(int(time.time()))
    token = secrets.token_hex(16)
    message = f"{timestamp}:{token}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(), message.encode(), "sha256"
    ).hexdigest()
    return f"{message}:{signature}"


def validate_csrf_token(csrf_token: str, max_age: int = 3600) -> bool:
    if not csrf_token:
        return False
    try:
        parts = csrf_token.split(":")
        if len(parts) != 3:
            return False
        timestamp, token, signature = parts
        if int(time.time()) - int(timestamp) > max_age:
            return False
        message = f"{timestamp}:{token}"
        expected = hmac.new(
            settings.SECRET_KEY.encode(), message.encode(), "sha256"
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False
