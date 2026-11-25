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
    plan_code: Optional[str] = Field("SOFIA-ERP-PRO", example="SOFIA-ERP-PRO")
    billing_cycle: Optional[str] = Field("MONTHLY", example="MONTHLY")


class TenantCreate(TenantBase):
    admin_email: str = Field(..., example="admin@constructorasur.pe")
    admin_password: str = Field(..., min_length=8, example="SuperSecret123#")
    plan_code: str = Field(..., example="SOFIA-ERP-PRO")
    billing_cycle: Optional[str] = Field("MONTHLY", example="MONTHLY")
    payment_reference: Optional[str] = Field(None, example="MP-PREF-123456")


class TenantStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(ACTIVE|SUSPENDED|ARCHIVED)$", example="SUSPENDED")
    reason: Optional[str] = Field(None, max_length=255, example="Falta de pago de suscripción mensual")
    extend_days: Optional[int] = Field(None, example=30)


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
    plan_code: Optional[str] = "SOFIA-ERP-PRO"
    billing_cycle: Optional[str] = "MONTHLY"
    subscription_expires_at: Optional[datetime] = None
    payment_status: Optional[str] = "PAID"
    last_payment_date: Optional[datetime] = None
    last_payment_reference: Optional[str] = None
    created_at: datetime
    domains: List[TenantDomainResponse] = []

    model_config = ConfigDict(from_attributes=True)
