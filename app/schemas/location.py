from pydantic import BaseModel, field_validator


class LocationCreateSchema(BaseModel):
    name: str
    code: str
    region: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    city: str = ""
    postcode: str = ""

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 150:
            raise ValueError("Name must be 150 characters or fewer")
        return v

    @field_validator("code")
    @classmethod
    def code_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Code is required")
        if len(v) > 50:
            raise ValueError("Code must be 50 characters or fewer")
        return v

    @field_validator("postcode")
    @classmethod
    def postcode_valid(cls, v: str) -> str:
        v = v.strip()
        if v and len(v) > 20:
            raise ValueError("Postcode must be 20 characters or fewer")
        return v


class LocationUpdateSchema(LocationCreateSchema):
    is_active: bool = True
