from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint(
            "registration_number", name="uq_vehicles_registration_number"
        ),
        UniqueConstraint("fleet_reference", name="uq_vehicles_fleet_reference"),
        CheckConstraint(
            "status IN ('active', 'pending_retirement', 'retired')",
            name="ck_vehicles_status",
        ),
        CheckConstraint(
            "vehicle_type IN ('roadside_van', 'flat_loader_lorry', 'patrol_van')",
            name="ck_vehicles_vehicle_type",
        ),
        CheckConstraint("current_mileage >= 0", name="ck_vehicles_current_mileage"),
        CheckConstraint("year >= 1900", name="ck_vehicles_year_min"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registration_number: Mapped[str] = mapped_column(String(20), nullable=False)
    fleet_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", server_default="active"
    )
    current_mileage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False
    )
    primary_driver_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    retirement_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    location: Mapped["Location"] = relationship(back_populates="vehicles")
    primary_driver: Mapped[Optional["User"]] = relationship(
        back_populates="primary_driver_vehicles",
        foreign_keys=[primary_driver_user_id],
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="vehicle"
    )
    mileage_records: Mapped[list["MileageRecord"]] = relationship(
        back_populates="vehicle"
    )
    retirement_requests: Mapped[list["RetirementRequest"]] = relationship(
        back_populates="vehicle"
    )

    @property
    def is_retired(self) -> bool:
        return self.status == "retired"

    @property
    def is_active_status(self) -> bool:
        return self.status == "active"

    @property
    def display_type(self) -> str:
        return self.vehicle_type.replace("_", " ").title()

    @property
    def mileage_source(self) -> dict | None:
        """Return the record that set current_mileage, computed from relationships."""
        if self.current_mileage == 0:
            return None
        best = None
        for rec in self.mileage_records:
            if not rec.is_deleted and rec.reading_value == self.current_mileage:
                if best is None or rec.reading_value > best["value"]:
                    best = {"type": "mileage_record", "id": rec.id, "value": rec.reading_value}
        for rec in self.maintenance_records:
            if not rec.is_deleted and rec.mileage_at_time == self.current_mileage:
                if best is None or rec.mileage_at_time > best["value"]:
                    best = {"type": "maintenance_record", "id": rec.id, "value": rec.mileage_at_time}
        return best

    def __repr__(self) -> str:
        return f"<Vehicle {self.registration_number} ({self.status})>"
