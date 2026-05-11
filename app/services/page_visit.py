from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.page_visit import PageVisit


def record_visit(db: Session, *, user_id: int, path: str, method: str = "GET") -> None:
    entry = PageVisit(user_id=user_id, path=path, method=method)
    db.add(entry)
    db.commit()


def get_visits(
    db: Session,
    *,
    limit: int = 200,
    offset: int = 0,
    user_id: int | None = None,
    days: int | None = None,
) -> list[PageVisit]:
    q = db.query(PageVisit)
    if user_id:
        q = q.filter(PageVisit.user_id == user_id)
    if days:
        since = datetime.now() - timedelta(days=days)
        q = q.filter(PageVisit.visited_at >= since)
    return q.order_by(PageVisit.visited_at.desc()).limit(limit).offset(offset).all()


def count_visits(db: Session, *, user_id: int | None = None, days: int | None = None) -> int:
    q = db.query(PageVisit)
    if user_id:
        q = q.filter(PageVisit.user_id == user_id)
    if days:
        since = datetime.now() - timedelta(days=days)
        q = q.filter(PageVisit.visited_at >= since)
    return q.count()


def get_popular_pages(db: Session, *, days: int = 30, limit: int = 20) -> list[tuple[str, int]]:
    since = datetime.now() - timedelta(days=days)
    return (
        db.query(PageVisit.path, func.count(PageVisit.id).label("visits"))
        .filter(PageVisit.visited_at >= since)
        .group_by(PageVisit.path)
        .order_by(func.count(PageVisit.id).desc())
        .limit(limit)
        .all()
    )


def get_active_users(db: Session, *, days: int = 30, limit: int = 20) -> list[tuple]:
    """Returns list of (user_id, username, visit_count) for most active non-admin users."""
    from app.models.user import User

    since = datetime.now() - timedelta(days=days)
    return (
        db.query(User.id, User.username, func.count(PageVisit.id).label("visits"))
        .join(PageVisit, PageVisit.user_id == User.id)
        .filter(PageVisit.visited_at >= since)
        .filter(User.role != "admin")
        .group_by(User.id, User.username)
        .order_by(func.count(PageVisit.id).desc())
        .limit(limit)
        .all()
    )
