from sqlalchemy.orm import Session

from app.exceptions import (
    AuthorisationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.models.user import User
from app.security.password import hash_password


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    return user


def get_all_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.username).all()


def get_standard_users(db: Session, active_only: bool = True) -> list[User]:
    q = db.query(User).filter(User.role == "standard")
    if active_only:
        q = q.filter(User.is_active == True)
    return q.order_by(User.username).all()


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "standard",
    employee_number: str = "",
    location_id: int | None = None,
    requesting_user_role: str | None = None,
) -> User:
    if role == "admin" and requesting_user_role not in ("admin", "self_register"):
        raise AuthorisationError("Only admins can create admin accounts")

    if db.query(User).filter(User.username == username).first():
        raise ConflictError("Username already taken")

    if db.query(User).filter(User.email == email).first():
        raise ConflictError("Email already in use")

    if employee_number:
        if db.query(User).filter(User.employee_number == employee_number).first():
            raise ConflictError("Employee number already in use")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        employee_number=employee_number or None,
        location_id=location_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: int,
    first_name: str,
    last_name: str,
    email: str,
    employee_number: str = "",
    location_id: int | None = None,
    is_active: bool = True,
) -> User:
    user = get_user_by_id(db, user_id)

    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        raise ConflictError("Email already in use")

    if employee_number:
        existing = (
            db.query(User)
            .filter(User.employee_number == employee_number, User.id != user_id)
            .first()
        )
        if existing:
            raise ConflictError("Employee number already in use")

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.employee_number = employee_number or None
    user.location_id = location_id
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def update_profile(
    db: Session,
    user_id: int,
    first_name: str,
    last_name: str,
    email: str,
) -> User:
    user = get_user_by_id(db, user_id)

    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        raise ConflictError("Email already in use")

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    db.commit()
    db.refresh(user)
    return user
