from pydantic import BaseModel, field_validator


class MileageCreateSchema(BaseModel):
    vehicle_id: int
    reading_value: int
    is_admin_override: bool = False
    override_reason: str = ""

    @field_validator("reading_value")
    @classmethod
    def reading_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Reading value cannot be negative")
        return v

    @field_validator("override_reason")
    @classmethod
    def override_reason_valid(cls, v: str) -> str:
        return v.strip()


class MileageUpdateSchema(BaseModel):
    reading_value: int
    is_admin_override: bool = False
    override_reason: str = ""

    @field_validator("reading_value")
    @classmethod
    def reading_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Reading value cannot be negative")
        return v
