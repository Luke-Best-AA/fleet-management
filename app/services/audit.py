from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int | None = None,
    target_label: str | None = None,
    details: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        details=details,
    )
    db.add(entry)
    db.commit()
    return entry


def get_audit_logs(db: Session, limit: int = 200, offset: int = 0) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def count_audit_logs(db: Session) -> int:
    return db.query(AuditLog).count()
