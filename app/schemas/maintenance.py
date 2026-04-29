from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator


class MaintenanceCategoryCreateSchema(BaseModel):
    name: str
    description: str = ""
    requires_notes: bool = False

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 100:
            raise ValueError("Name must be 100 characters or fewer")
        return v


class MaintenanceCategoryUpdateSchema(MaintenanceCategoryCreateSchema):
    is_active: bool = True


class MaintenanceRecordCreateSchema(BaseModel):
    vehicle_id: int
    category_id: int
    maintenance_date: date
    mileage_at_time: int
    notes: str = ""
    cost: Decimal | None = None

    @field_validator("mileage_at_time")
    @classmethod
    def mileage_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Mileage cannot be negative")
        return v

    @field_validator("cost")
    @classmethod
    def cost_valid(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Cost cannot be negative")
        return v


class MaintenanceRecordUpdateSchema(BaseModel):
    category_id: int
    maintenance_date: date
    mileage_at_time: int
    notes: str = ""
    cost: Decimal | None = None

    @field_validator("mileage_at_time")
    @classmethod
    def mileage_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Mileage cannot be negative")
        return v

    @field_validator("cost")
    @classmethod
    def cost_valid(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Cost cannot be negative")
        return v
