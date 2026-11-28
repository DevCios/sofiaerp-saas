# -*- coding: utf-8 -*-
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DispatchPolicy(str, enum.Enum):
    INSTANT_WITH_RETRY = "INSTANT_WITH_RETRY"
    SCHEDULED_NIGHT = "SCHEDULED_NIGHT"
    HYBRID_BOLETA_SUMMARY = "HYBRID_BOLETA_SUMMARY"


class DocumentStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SIGNED_LOCAL = "SIGNED_LOCAL"
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_OBS = "ACCEPTED_WITH_OBS"
    REJECTED = "REJECTED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RECOVERING_CDR = "RECOVERING_CDR"
    EXPIRED_ALERT = "EXPIRED_ALERT"


class Workspace(Base):
    """Espacio de trabajo aislado para clientes comerciales self-service (ADR-012)."""
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    plan_name: Mapped[str] = mapped_column(String(40), default="FREE", nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    source: Mapped[str] = mapped_column(String(24), default="external", nullable=False)  # external | sofia_erp
    billing_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GatewayUser(Base):
    """Usuario registrado self-service perteneciente a un Workspace."""
    __tablename__ = "gateway_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(24), default="local", nullable=False)  # local | sofia_sso
    role: Mapped[str] = mapped_column(String(32), default="workspace_owner", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkspaceMember(Base):
    """Membresía N:M entre GatewayUser y Workspace para soporte Multi-Workspace."""
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_workspace_member_user_ws"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("gateway_users.id"), index=True, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="owner", nullable=False)  # owner | admin | member
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkspaceInvitation(Base):
    """Invitación por correo / enlace seguro para sumarse a un Workspace con rol member o admin."""
    __tablename__ = "workspace_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="member", nullable=False)  # member | admin
    token: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    invited_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True, nullable=False)  # PENDING | ACCEPTED | REVOKED
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class BillingOrder(Base):
    """Orden de compra / recarga de plan vía Mercado Pago Checkout Pro."""
    __tablename__ = "billing_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False)
    quota_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_pen: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True, nullable=False)  # PENDING | PAID | FAILED
    mp_preference_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mp_payment_id: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)


class Issuer(Base):
    """Empresa Emisora (RUC) registrada en la Caja Negra SUNAT."""
    __tablename__ = "issuers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=True)
    ruc: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ubigeo: Mapped[str | None] = mapped_column(String(6), nullable=True)
    establishment_code: Mapped[str] = mapped_column(String(4), default="0000", nullable=False)

    # Entorno y política de envío
    is_beta: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_nrus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispatch_policy: Mapped[DispatchPolicy] = mapped_column(
        Enum(DispatchPolicy), default=DispatchPolicy.INSTANT_WITH_RETRY, nullable=False
    )
    night_window_start: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    night_window_end: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Secretos cifrados en reposo (Fernet AES)
    sol_username_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sol_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    pfx_content_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    pfx_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cert_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cert_is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # GRE 2.0 (OAuth2 SUNAT API REST)
    gre_client_id_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    gre_client_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_name: Mapped[str] = mapped_column(String(40), default="STARTER", nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="issuer")


class ApiClient(Base):
    """Aplicación cliente (SOFIA ERP, POS externo, Ecommerce) con API Key y Webhook."""
    __tablename__ = "api_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_rucs: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # None = todos los RUCs

    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base):
    """Comprobante Electrónico gestionado por la Caja Negra."""
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("issuer_ruc", "doc_type", "serie", "correlativo", name="uq_sunat_doc_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issuer_id: Mapped[str] = mapped_column(String(36), ForeignKey("issuers.id"), index=True, nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_clients.id"), nullable=True)

    issuer_ruc: Mapped[str] = mapped_column(String(11), index=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(2), index=True, nullable=False)  # 01, 03, 07, 08, 09, 31, RA, RC
    serie: Mapped[str] = mapped_column(String(10), nullable=False)
    correlativo: Mapped[str] = mapped_column(String(12), nullable=False)
    issue_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    igv_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    customer_doc_type: Mapped[str | None] = mapped_column(String(2), nullable=True)
    customer_doc_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    external_ref: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.RECEIVED, index=True, nullable=False
    )

    # Firma local instantánea + almacenamiento
    xml_filename: Mapped[str] = mapped_column(String(120), nullable=False)
    xml_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cdr_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    digest_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    qr_string: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Respuesta SUNAT
    sunat_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sunat_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sunat_notes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sunat_ticket: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Control de reintentos y vencimiento legal (3 días calendario)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    alert_sent_24h: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alert_sent_48h: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    issuer: Mapped["Issuer"] = relationship("Issuer", back_populates="documents")
    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="document", cascade="all, delete-orphan"
    )


class DeliveryAttempt(Base):
    """Bitácora auditable de cada intento de envío o recuperación getStatusCdr."""
    __tablename__ = "delivery_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(40), default="sendBill", nullable=False)  # sendBill, getStatusCdr, sendGRE
    endpoint_url: Mapped[str] = mapped_column(String(300), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sunat_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sunat_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="attempts")


class WebhookLog(Base):
    """Historial de notificaciones webhook firmadas enviadas a apps cliente."""
    __tablename__ = "webhook_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_clients.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ApiRequestLog(Base):
    """Bitácora auditable de peticiones REST y herramientas MCP (ADR-011)."""
    __tablename__ = "api_request_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="REST", index=True, nullable=False)  # REST | MCP
    method: Mapped[str] = mapped_column(String(12), default="POST", nullable=False)
    action: Mapped[str] = mapped_column(String(160), index=True, nullable=False)  # ej. /api/v1/documents/emit o mcp:emit_document
    issuer_ruc: Mapped[str | None] = mapped_column(String(11), index=True, nullable=True)
    client_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)


class OAuthClient(Base):
    """Cliente OAuth 2.1 registrado dinámicamente (RFC 7591) para Claude.ai / ChatGPT Connectors."""
    __tablename__ = "oauth_clients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(160), default="MCP AI Client", nullable=False)
    redirect_uris: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    token_endpoint_auth_method: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OAuthAuthCode(Base):
    """Código de autorización OAuth 2.1 PKCE (un solo uso, TTL 5 min)."""
    __tablename__ = "oauth_auth_codes"

    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(256), nullable=False)
    code_challenge_method: Mapped[str] = mapped_column(String(16), default="S256", nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    allowed_rucs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IdentityCache(Base):
    """Caché compartido de consultas RUC (SUNAT) y DNI (RENIEC) (ADR-013)."""
    __tablename__ = "identity_cache"
    __table_args__ = (
        UniqueConstraint("doc_type", "doc_number", name="uq_identity_cache_doc"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type: Mapped[str] = mapped_column(String(8), index=True, nullable=False)  # RUC | DNI
    doc_number: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="apis.net.pe", nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)


class ExchangeRate(Base):
    """Historial oficial diario de Tipo de Cambio SUNAT (USD -> PEN) (ADR-013)."""
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("rate_date", "currency", name="uq_exchange_rate_date_curr"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rate_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # YYYY-MM-DD (Lima)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    buy_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    sell_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="sunat", nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
