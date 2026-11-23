"""
Modelos ORM para Catálogo de Productos, Planes Comerciales y Suscripciones.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plans: Mapped[list["ProductPlan"]] = relationship("ProductPlan", back_populates="product")


class ProductPlan(Base):
    __tablename__ = "product_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # BASIC, PROFESSIONAL, ENTERPRISE
    tier: Mapped[str] = mapped_column(String(30), nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_concurrent_sessions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    storage_gb_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="plans")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_plans.id", ondelete="RESTRICT"), nullable=False
    )
    
    # TRIAL, ACTIVE, PAST_DUE, SUSPENDED, CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="TRIAL", nullable=False, index=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    extra_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_storage_gb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")
    plan: Mapped["ProductPlan"] = relationship("ProductPlan", back_populates="subscriptions")
