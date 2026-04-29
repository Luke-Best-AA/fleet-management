import json
import secrets
import uuid

import redis

from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

SESSION_PREFIX = "session:"
USER_SESSION_PREFIX = "user_session:"
FLASH_PREFIX = "flash:"
LOGIN_ATTEMPTS_PREFIX = "login_attempts:"


def create_session(user_id: int, user_data: dict) -> str:
    invalidate_user_sessions(user_id)
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_id,
        "username": user_data["username"],
        "role": user_data["role"],
        "first_name": user_data["first_name"],
    }
    redis_client.setex(
        f"{SESSION_PREFIX}{session_id}",
        settings.SESSION_LIFETIME_SECONDS,
        json.dumps(session_data),
    )
    redis_client.setex(
        f"{USER_SESSION_PREFIX}{user_id}",
        settings.SESSION_LIFETIME_SECONDS,
        session_id,
    )
    return session_id


def get_session(session_id: str) -> dict | None:
    if not session_id:
        return None
    data = redis_client.get(f"{SESSION_PREFIX}{session_id}")
    if data:
        return json.loads(data)
    return None


def refresh_session(session_id: str, user_id: int | None = None) -> None:
    """Extend the TTL of an active session so it doesn't expire during use."""
    if not session_id:
        return
    redis_client.expire(
        f"{SESSION_PREFIX}{session_id}",
        settings.SESSION_LIFETIME_SECONDS,
    )
    if user_id:
        redis_client.expire(
            f"{USER_SESSION_PREFIX}{user_id}",
            settings.SESSION_LIFETIME_SECONDS,
        )


def destroy_session(session_id: str) -> None:
    if not session_id:
        return
    data = get_session(session_id)
    if data:
        user_id = data.get("user_id")
        if user_id:
            redis_client.delete(f"{USER_SESSION_PREFIX}{user_id}")
    redis_client.delete(f"{SESSION_PREFIX}{session_id}")


def invalidate_user_sessions(user_id: int) -> None:
    old_session_id = redis_client.get(f"{USER_SESSION_PREFIX}{user_id}")
    if old_session_id:
        redis_client.delete(f"{SESSION_PREFIX}{old_session_id}")
        redis_client.delete(f"{USER_SESSION_PREFIX}{user_id}")


# Flash messages

def add_flash(session_id: str, message: str, category: str = "info") -> None:
    if not session_id:
        return
    flash_data = json.dumps({"message": message, "category": category})
    key = f"{FLASH_PREFIX}{session_id}"
    redis_client.rpush(key, flash_data)
    redis_client.expire(key, 300)


def get_flashes(session_id: str) -> list[dict]:
    if not session_id:
        return []
    key = f"{FLASH_PREFIX}{session_id}"
    flashes = []
    while True:
        data = redis_client.lpop(key)
        if data is None:
            break
        flashes.append(json.loads(data))
    return flashes


# Lockout

def record_failed_login(username: str) -> int:
    key = f"{LOGIN_ATTEMPTS_PREFIX}{username}"
    count = redis_client.incr(key)
    redis_client.expire(key, settings.LOCKOUT_DURATION_SECONDS)
    return count


def is_locked_out(username: str) -> bool:
    key = f"{LOGIN_ATTEMPTS_PREFIX}{username}"
    attempts = redis_client.get(key)
    if attempts and int(attempts) >= settings.MAX_LOGIN_ATTEMPTS:
        return True
    return False


def get_lockout_remaining(username: str) -> int:
    key = f"{LOGIN_ATTEMPTS_PREFIX}{username}"
    ttl = redis_client.ttl(key)
    return max(0, ttl)


def clear_login_attempts(username: str) -> None:
    redis_client.delete(f"{LOGIN_ATTEMPTS_PREFIX}{username}")
