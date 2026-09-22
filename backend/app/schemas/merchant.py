import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MerchantCreate(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=6)
    business_name: Optional[str] = None
    telco: Optional[str] = None


class MerchantOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    phone: str
    business_name: Optional[str]
    telco: Optional[str]
    consent_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True