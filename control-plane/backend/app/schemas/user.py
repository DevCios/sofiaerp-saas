"""
Esquemas Pydantic v2 para Usuarios y Tokens de Autenticación.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(..., example="usuario@empresa.pe")
    full_name: str = Field(..., min_length=2, max_length=150, example="Carlos Mendoza")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="ContrasenaSegura#2026")


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None
    mfa_code: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_superadmin: bool
    mfa_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: Optional[UUID] = None
    roles: List[str] = []


class TokenPayload(BaseModel):
    sub: str
    tenant_id: Optional[str] = None
    roles: List[str] = []
    exp: int
