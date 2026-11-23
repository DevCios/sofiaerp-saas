"""
Esquemas Pydantic v2 para validación de datos de Tenants y Dominios.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TenantBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=150, example="Constructora del Sur S.A.C.")
    slug: str = Field(..., min_length=3, max_length=63, pattern=r"^[a-z0-9-]+$", example="constructora-sur")
    runtime_mode: Optional[str] = Field("SHARED_PROTECTED", example="SHARED_PROTECTED")


class TenantCreate(TenantBase):
    admin_email: str = Field(..., example="admin@constructorasur.pe")
    admin_password: str = Field(..., min_length=8, example="SuperSecret123#")
    plan_code: str = Field(..., example="SOFIA-ERP-PRO")


class TenantDomainBase(BaseModel):
    domain: str = Field(..., min_length=4, max_length=255, example="erp.constructorasur.pe")
    is_primary: bool = Field(False)


class TenantDomainCreate(TenantDomainBase):
    pass


class TenantDomainResponse(TenantDomainBase):
    id: UUID
    tenant_id: UUID
    verification_token: str
    status: str
    ssl_expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantResponse(TenantBase):
    id: UUID
    database_name: str
    status: str
    created_at: datetime
    domains: List[TenantDomainResponse] = []

    model_config = ConfigDict(from_attributes=True)
