from pydantic import BaseModel


class ModuleStatus(BaseModel):
    key: str
    name: str
    description: str
    maturity: str
    enabled: bool


class ModuleToggleRequest(BaseModel):
    enabled: bool


class OrganizationOut(BaseModel):
    id: int
    name: str
    industry: str
    size: str
    country: str

    class Config:
        from_attributes = True
