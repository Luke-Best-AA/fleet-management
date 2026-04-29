import re

from pydantic import BaseModel, field_validator


VEHICLE_TYPES = ("roadside_van", "flat_loader_lorry", "patrol_van")
VEHICLE_STATUSES = ("active", "pending_retirement", "retired")

UK_PLATE_PATTERN = re.compile(
    r"(^[A-Z]{2}[0-9]{2}\s?[A-Z]{3}$)|"       # Current (AB51 ABC)
    r"(^[A-Z][0-9]{1,3}\s?[A-Z]{3}$)|"         # Prefix (A123 ABC)
    r"(^[A-Z]{3}\s?[0-9]{1,3}[A-Z]$)|"         # Suffix (ABC 123A)
    r"(^[0-9]{1,4}\s?[A-Z]{1,2}$)|"            # Dateless Long Number Prefix
    r"(^[0-9]{1,3}\s?[A-Z]{1,3}$)|"            # Dateless Short Number Prefix
    r"(^[A-Z]{1,2}\s?[0-9]{1,4}$)|"            # Dateless Long Number Suffix
    r"(^[A-Z]{1,3}\s?[0-9]{1,3}$)|"            # Dateless Short Number Suffix
    r"(^[A-Z]{1,3}\s?[0-9]{1,4}$)|"            # Northern Ireland
    r"(^[0-9]{3}\s?[DX]{1}\s?[0-9]{3}$)",      # Diplomatic
    re.IGNORECASE,
)


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
        if not UK_PLATE_PATTERN.match(v):
            raise ValueError("Enter a valid UK registration number (e.g. AB12 CDE)")
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
            raise ValueError("Please select a valid vehicle type")
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
        if not UK_PLATE_PATTERN.match(v):
            raise ValueError("Enter a valid UK registration number (e.g. AB12 CDE)")
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
            raise ValueError("Please select a valid vehicle type")
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
