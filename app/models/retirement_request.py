from __future__ import annotations

from datetime import datetime
from typing import Optional

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


class RetirementRequest(Base, TimestampMixin):
    __tablename__ = "retirement_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_retirement_requests_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id"), nullable=False
    )
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="retirement_requests")
    requested_by: Mapped["User"] = relationship(
        back_populates="requested_retirement_requests",
        foreign_keys=[requested_by_user_id],
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(
        back_populates="reviewed_retirement_requests",
        foreign_keys=[reviewed_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<RetirementRequest {self.id} vehicle={self.vehicle_id} status={self.status}>"
