from pydantic import BaseModel, EmailStr, field_validator


class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "standard"
    employee_number: str = ""
    location_id: int | None = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 3 or len(v) > 100:
            raise ValueError("Username must be between 3 and 100 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in ("admin", "standard"):
            raise ValueError("Role must be admin or standard")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        return v


class UserUpdateSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    employee_number: str = ""
    location_id: int | None = None
    is_active: bool = True

    @field_validator("first_name", "last_name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        return v
