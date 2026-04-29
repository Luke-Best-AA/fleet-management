from pydantic import BaseModel, field_validator


VEHICLE_TYPES = ("roadside_van", "flat_loader_lorry", "patrol_van")
VEHICLE_STATUSES = ("active", "pending_retirement", "retired")


class VehicleCreateSchema(BaseModel):
    registration_number: str
    fleet_reference: str
    vehicle_type: str
    make: str
    model: str
    year: int
    current_mileage: int = 0
    location_id: int
    primary_driver_user_id: int | None = None

    @field_validator("registration_number")
    @classmethod
    def reg_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Registration number is required")
        if len(v) > 20:
            raise ValueError("Registration number must be 20 characters or fewer")
        return v

    @field_validator("fleet_reference")
    @classmethod
    def fleet_ref_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Fleet reference is required")
        if len(v) > 50:
            raise ValueError("Fleet reference must be 50 characters or fewer")
        return v

    @field_validator("vehicle_type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v not in VEHICLE_TYPES:
            raise ValueError(f"Vehicle type must be one of: {', '.join(VEHICLE_TYPES)}")
        return v

    @field_validator("make", "model")
    @classmethod
    def make_model_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        if len(v) > 100:
            raise ValueError("Must be 100 characters or fewer")
        return v

    @field_validator("year")
    @classmethod
    def year_valid(cls, v: int) -> int:
        if v < 1900 or v > 2100:
            raise ValueError("Year must be between 1900 and 2100")
        return v

    @field_validator("current_mileage")
    @classmethod
    def mileage_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Mileage cannot be negative")
        return v


class VehicleUpdateSchema(BaseModel):
    registration_number: str
    fleet_reference: str
    vehicle_type: str
    make: str
    model: str
    year: int
    location_id: int
    primary_driver_user_id: int | None = None

    @field_validator("registration_number")
    @classmethod
    def reg_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Registration number is required")
        return v

    @field_validator("fleet_reference")
    @classmethod
    def fleet_ref_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Fleet reference is required")
        return v

    @field_validator("vehicle_type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v not in VEHICLE_TYPES:
            raise ValueError(f"Vehicle type must be one of: {', '.join(VEHICLE_TYPES)}")
        return v

    @field_validator("make", "model")
    @classmethod
    def make_model_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        return v

    @field_validator("year")
    @classmethod
    def year_valid(cls, v: int) -> int:
        if v < 1900 or v > 2100:
            raise ValueError("Year must be between 1900 and 2100")
        return v
