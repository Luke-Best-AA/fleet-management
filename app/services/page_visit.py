from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Date, cast, func
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


def get_daily_visits(db: Session, *, days: int = 30, user_id: int | None = None) -> list[tuple[str, int]]:
    """Returns list of (date_string, count) for each day in the period."""
    since = datetime.now() - timedelta(days=days)
    q = db.query(
        cast(PageVisit.visited_at, Date).label("day"),
        func.count(PageVisit.id).label("visits"),
    ).filter(PageVisit.visited_at >= since)
    if user_id:
        q = q.filter(PageVisit.user_id == user_id)
    rows = q.group_by("day").order_by("day").all()
    return [(row.day.strftime("%d %b"), row.visits) for row in rows]


def get_hourly_distribution(db: Session, *, days: int = 30, user_id: int | None = None) -> list[tuple[int, int]]:
    """Returns list of (hour_0_to_23, count) for visit distribution by hour."""
    since = datetime.now() - timedelta(days=days)
    hour_expr = func.extract("hour", PageVisit.visited_at)
    q = db.query(hour_expr.label("hour"), func.count(PageVisit.id).label("visits")).filter(
        PageVisit.visited_at >= since
    )
    if user_id:
        q = q.filter(PageVisit.user_id == user_id)
    rows = q.group_by("hour").order_by("hour").all()
    result = {int(r.hour): r.visits for r in rows}
    return [(h, result.get(h, 0)) for h in range(24)]
