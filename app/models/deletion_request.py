from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class DeletionRequest(Base, TimestampMixin):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('maintenance_record', 'mileage_record')",
            name="ck_deletion_requests_target_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_deletion_requests_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requested_by: Mapped[User] = relationship(
        back_populates="requested_deletion_requests",
        foreign_keys=[requested_by_user_id],
    )
    reviewed_by: Mapped[User | None] = relationship(
        back_populates="reviewed_deletion_requests",
        foreign_keys=[reviewed_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<DeletionRequest {self.id} {self.target_type}:{self.target_id} status={self.status}>"
