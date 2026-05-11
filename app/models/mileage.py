from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MileageRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mileage_records"
    __table_args__ = (
        CheckConstraint("reading_value >= 0", name="ck_mileage_records_reading_value"),
        CheckConstraint(
            "(is_admin_override = false AND override_reason IS NULL) OR "
            "(is_admin_override = true AND override_reason IS NOT NULL)",
            name="ck_mileage_records_override_reason",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reading_value: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_admin_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    vehicle: Mapped[Vehicle] = relationship(back_populates="mileage_records")
    recorded_by: Mapped[User] = relationship(
        back_populates="mileage_records",
        foreign_keys=[recorded_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<MileageRecord {self.id} vehicle={self.vehicle_id} value={self.reading_value}>"
