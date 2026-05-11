from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MaintenanceCategory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "maintenance_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_maintenance_categories_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    maintenance_records: Mapped[list[MaintenanceRecord]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<MaintenanceCategory {self.name}>"


class MaintenanceRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "maintenance_records"
    __table_args__ = (
        CheckConstraint("mileage_at_time >= 0", name="ck_maintenance_records_mileage_at_time"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="ck_maintenance_records_cost"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("maintenance_categories.id"), nullable=False)
    logged_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    mileage_at_time: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    vehicle: Mapped[Vehicle] = relationship(back_populates="maintenance_records")
    category: Mapped[MaintenanceCategory] = relationship(back_populates="maintenance_records")
    logged_by: Mapped[User] = relationship(
        back_populates="maintenance_records",
        foreign_keys=[logged_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<MaintenanceRecord {self.id} vehicle={self.vehicle_id}>"
