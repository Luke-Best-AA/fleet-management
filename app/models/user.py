from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("employee_number", name="uq_users_employee_number"),
        CheckConstraint("role IN ('admin', 'standard')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    employee_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_password_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    location: Mapped[Location | None] = relationship(back_populates="users")

    primary_driver_vehicles: Mapped[list[Vehicle]] = relationship(
        back_populates="primary_driver",
        foreign_keys="Vehicle.primary_driver_user_id",
    )
    maintenance_records: Mapped[list[MaintenanceRecord]] = relationship(
        back_populates="logged_by",
        foreign_keys="MaintenanceRecord.logged_by_user_id",
    )
    mileage_records: Mapped[list[MileageRecord]] = relationship(
        back_populates="recorded_by",
        foreign_keys="MileageRecord.recorded_by_user_id",
    )
    requested_retirement_requests: Mapped[list[RetirementRequest]] = relationship(
        back_populates="requested_by",
        foreign_keys="RetirementRequest.requested_by_user_id",
    )
    reviewed_retirement_requests: Mapped[list[RetirementRequest]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="RetirementRequest.reviewed_by_user_id",
    )
    requested_deletion_requests: Mapped[list[DeletionRequest]] = relationship(
        back_populates="requested_by",
        foreign_keys="DeletionRequest.requested_by_user_id",
    )
    reviewed_deletion_requests: Mapped[list[DeletionRequest]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="DeletionRequest.reviewed_by_user_id",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
