from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# ---- Tenant ----
class TenantCreate(BaseModel):
    name: str

class TenantOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}  # lets pydantic read from SQLAlchemy objects


# ---- Customer ----
class CustomerCreate(BaseModel):
    tenant_id: UUID
    name: str
    mobile_no: str
    email: EmailStr
    passport_id: Optional[str] = None
    license_number: str
    license_expiry: date

class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    mobile_no: str
    email: str
    license_number: str
    license_expiry: date
    model_config = {"from_attributes": True}