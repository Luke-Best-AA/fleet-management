from pydantic import BaseModel, EmailStr, field_validator


class LoginSchema(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str
    first_name: str
    last_name: str
    employee_number: str = ""
    role: str = "standard"

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in ("standard", "admin"):
            raise ValueError("Role must be standard or admin")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username is required")
        if len(v) < 3 or len(v) > 100:
            raise ValueError("Username must be between 3 and 100 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("first_name")
    @classmethod
    def first_name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("First name is required")
        if len(v) > 100:
            raise ValueError("First name must be 100 characters or fewer")
        return v

    @field_validator("last_name")
    @classmethod
    def last_name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Last name is required")
        if len(v) > 100:
            raise ValueError("Last name must be 100 characters or fewer")
        return v

    @field_validator("employee_number")
    @classmethod
    def employee_number_valid(cls, v: str) -> str:
        v = v.strip()
        if v and len(v) > 50:
            raise ValueError("Employee number must be 50 characters or fewer")
        return v


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("current_password")
    @classmethod
    def current_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Current password is required")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v

    @field_validator("new_password_confirm")
    @classmethod
    def new_passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v
