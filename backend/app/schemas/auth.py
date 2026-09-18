from pydantic import BaseModel, EmailStr, Field

from app.models.user import RoleEnum


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    industry: str = "general"
    size: str = "unknown"
    country: str = "unknown"


class RegisterRequest(BaseModel):
    organization: OrganizationCreate
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_full_name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    department: str | None
    organization_id: int | None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: RoleEnum = RoleEnum.employee
    department: str | None = None
