from pydantic import BaseModel, field_validator

TARGET_TYPES = ("maintenance_record", "mileage_record")


class RetirementRequestCreateSchema(BaseModel):
    vehicle_id: int
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Reason is required")
        if len(v) < 10:
            raise ValueError("Reason must be at least 10 characters")
        if len(v) > 2000:
            raise ValueError("Reason must be 2000 characters or fewer")
        return v


class RetirementRequestReviewSchema(BaseModel):
    action: str
    review_notes: str = ""

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("Action must be approve or reject")
        return v


class DeletionRequestCreateSchema(BaseModel):
    target_type: str
    target_id: int
    reason: str

    @field_validator("target_type")
    @classmethod
    def target_type_valid(cls, v: str) -> str:
        if v not in TARGET_TYPES:
            raise ValueError(f"Target type must be one of: {', '.join(TARGET_TYPES)}")
        return v

    @field_validator("reason")
    @classmethod
    def reason_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Reason is required")
        if len(v) > 2000:
            raise ValueError("Reason must be 2000 characters or fewer")
        return v


class DeletionRequestReviewSchema(BaseModel):
    action: str
    review_notes: str = ""

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("Action must be approve or reject")
        return v
