import base64
import hmac
import secrets
import struct
import time

from app.config import settings


def _encode_ts(ts: int) -> str:
    """Encode a timestamp as url-safe base64 to avoid plain-text disclosure."""
    return base64.urlsafe_b64encode(struct.pack(">I", ts)).decode().rstrip("=")


def _decode_ts(encoded: str) -> int:
    """Decode a url-safe base64 timestamp."""
    padded = encoded + "=" * (-len(encoded) % 4)
    return struct.unpack(">I", base64.urlsafe_b64decode(padded))[0]


def generate_csrf_token() -> str:
    ts = _encode_ts(int(time.time()))
    token = secrets.token_hex(16)
    message = f"{ts}:{token}"
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), "sha256").hexdigest()
    return f"{message}:{signature}"


def validate_csrf_token(csrf_token: str, max_age: int = 3600) -> bool:
    if not csrf_token:
        return False
    try:
        parts = csrf_token.split(":")
        if len(parts) != 3:
            return False
        ts_encoded, token, signature = parts
        timestamp = _decode_ts(ts_encoded)
        if int(time.time()) - timestamp > max_age:
            return False
        message = f"{ts_encoded}:{token}"
        expected = hmac.new(settings.SECRET_KEY.encode(), message.encode(), "sha256").hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError, struct.error):
        return False
