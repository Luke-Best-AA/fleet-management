from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions import AuthenticationError, LockedOutError
from app.models.user import User
from app.security.password import hash_password, verify_password
from app.services import session as session_service


def authenticate(db: Session, username: str, password: str) -> User:
    if session_service.is_locked_out(username):
        remaining = session_service.get_lockout_remaining(username)
        raise LockedOutError(f"Account locked. Try again in {remaining // 60 + 1} minute(s).")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        if user:
            session_service.record_failed_login(username)
        else:
            session_service.record_failed_login(username)
        raise AuthenticationError("Invalid username or password")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    session_service.clear_login_attempts(username)
    return user


def login(db: Session, username: str, password: str, fingerprint: str = "") -> tuple[str, User]:
    user = authenticate(db, username, password)
    session_id = session_service.create_session(
        user.id,
        {
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
        },
        fingerprint=fingerprint,
    )
    return session_id, user


def logout(session_id: str) -> None:
    session_service.destroy_session(session_id)


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError("User not found")

    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    user.password_hash = hash_password(new_password)
    user.last_password_change_at = datetime.now(UTC)
    db.commit()

    session_service.invalidate_user_sessions(user_id)
