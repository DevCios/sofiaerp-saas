"""
Modelos ORM para Tenants y Dominios Personalizados.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    database_name: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    filestore_path: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # PROVISIONING, ACTIVE, SUSPENDED, ARCHIVED
    status: Mapped[str] = mapped_column(String(30), default="PROVISIONING", nullable=False, index=True)
    
    # SHARED_PROTECTED, DEDICATED
    runtime_mode: Mapped[str] = mapped_column(String(30), default="SHARED_PROTECTED", nullable=False)
    dedicated_host: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    domains: Mapped[list["TenantDomain"]] = relationship(
        "TenantDomain", back_populates="tenant", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["UserTenantMembership"]] = relationship(
        "UserTenantMembership", back_populates="tenant", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="tenant"
    )


class TenantDomain(Base):
    __tablename__ = "tenant_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # PENDING_DNS, VERIFIED, SSL_ACTIVE, REVOKED
    status: Mapped[str] = mapped_column(String(30), default="PENDING_DNS", nullable=False)
    ssl_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="domains")
