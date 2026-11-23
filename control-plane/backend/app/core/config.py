"""
Configuración centralizada de SOFIA Platform mediante Pydantic Settings.
Garantiza validación estricta de tipos y variables de entorno.
"""
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Identidad y entorno
    PROJECT_NAME: str = "SOFIA Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_SECRET_KEY: str = "temporary_insecure_key_must_be_overridden_in_production"
    
    # Dominios y CORS
    ALLOWED_HOSTS: str = "*"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",")]

    # Base de Datos PostgreSQL Central
    DATABASE_URL: str = "postgresql+asyncpg://sofia_admin:sofia_pass@localhost:5432/sofia_central_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Autenticación y Criptografía (JWT RS256)
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas
    JWT_PRIVATE_KEY_PATH: str = "/etc/sofia/keys/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "/etc/sofia/keys/jwt_public.pem"

    # Almacenamiento y Rutas del Sistema
    SOFIA_FILESTORES_DIR: str = "/var/lib/sofia/filestores"
    SOFIA_BACKUPS_DIR: str = "/var/lib/sofia/backups"
    BACKUP_STORAGE_DRIVER: str = "google_drive"
    GOOGLE_DRIVE_FOLDER_ID: str = ""

    # Control de Capacidad y Concurrencia
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
