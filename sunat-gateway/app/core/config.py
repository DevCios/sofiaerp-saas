# -*- coding: utf-8 -*-
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "API SUNAT"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"
    PUBLIC_BASE_URL: str = "https://apisunat.pro"

    # Base de datos aislada para el Gateway
    DATABASE_URL: str = "postgresql+asyncpg://sofia_admin:changeme@postgres:5432/sofia_sunat_gateway_db"
    SYNC_DATABASE_URL: str = "postgresql://sofia_admin:changeme@postgres:5432/sofia_sunat_gateway_db"

    # Redis / Celery (DBs lógicas dedicadas 3 y 4 para no colisionar con Control Plane 0/1/2)
    REDIS_URL: str = "redis://redis:6379/3"
    CELERY_BROKER_URL: str = "redis://redis:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/4"

    # Seguridad y Vault de secretos (.pfx / Claves SOL / GRE)
    SUNAT_VAULT_MASTER_KEY: str = "CHANGE_ME_GENERATE_32_BYTE_URLSAFE_KEY_IN_PROD"
    GATEWAY_JWT_SECRET: str = "CHANGE_ME_GATEWAY_JWT_SECRET_IN_PROD"
    INTERNAL_SERVICE_KEY: str = "sofia_internal_mesh_key_change_in_prod"
    GATEWAY_ADMIN_EMAIL: str = "admin@sofiaerp.com"
    GATEWAY_ADMIN_PASSWORD: str = "SofiaGateway2026!"
    JWT_EXPIRE_MINUTES: int = 720
    STRICT_SECRET_VALIDATION: bool = False
    SYNC_DISPATCH_TIMEOUT_SECONDS: int = 12

    # Almacenamiento persistente de XML firmados y CDRs (.zip)
    STORAGE_DIR: str = "/var/lib/sofia-sunat/storage"

    # Ventana nocturna (hora de Lima UTC-5)
    LIMA_TZ: str = "America/Lima"
    DEFAULT_NIGHT_WINDOW_START: int = 1   # 01:00 AM
    DEFAULT_NIGHT_WINDOW_END: int = 5     # 05:00 AM

    # Endpoints oficiales SUNAT SOAP & REST
    SUNAT_BILL_BETA_URL: str = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"
    SUNAT_BILL_PROD_URL: str = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService"
    SUNAT_CDR_PROD_URL: str = "https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"
    SUNAT_GRE_TOKEN_URL: str = "https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    SUNAT_GRE_API_URL: str = "https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes"
    SUNAT_TIMEOUT_SECONDS: int = 25

    # Mercado Pago (Suscripciones y recargas de planes comerciales)
    MP_ACCESS_TOKEN: str = ""
    MP_WEBHOOK_SECRET: str = ""

    # SSO con SOFIA Control Plane (red interna Docker + validación JWKS RS256)
    SOFIA_CONTROL_PLANE_URL: str = "http://control-plane-api:8000"

    # Hub Central de Consultas Perú (RUC, DNI, Tipo de Cambio SUNAT)
    DECOLECTA_TOKEN: str = ""
    APIS_NET_PE_TOKEN: str = ""
    APISPERU_TOKEN: str = ""
    RUC_CACHE_TTL_DAYS: int = 7
    DNI_CACHE_TTL_DAYS: int = 30

    def get_insecure_secret_warnings(self) -> list[str]:
        """Detecta secretos por defecto inseguros en entorno de producción."""
        warnings: list[str] = []
        checks = {
            "SUNAT_VAULT_MASTER_KEY": self.SUNAT_VAULT_MASTER_KEY,
            "GATEWAY_JWT_SECRET": self.GATEWAY_JWT_SECRET,
            "INTERNAL_SERVICE_KEY": self.INTERNAL_SERVICE_KEY,
            "GATEWAY_ADMIN_PASSWORD": self.GATEWAY_ADMIN_PASSWORD,
        }
        markers = ("change_me", "change_in_prod", "sofiaadmin2026", "sofiagateway2026", "changeme")
        for key, val in checks.items():
            low = (val or "").lower()
            if not val or any(m in low for m in markers):
                warnings.append(f"{key} usa un valor por defecto inseguro; sobrescríbelo en .env")
        return warnings


@lru_cache()
def get_settings() -> Settings:
    return Settings()
