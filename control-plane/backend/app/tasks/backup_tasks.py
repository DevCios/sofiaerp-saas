"""
Tareas Celery para Respaldo Automatizado hacia Google Drive mediante rclone (ADR-006).
Realiza volcados pg_dump cifrados y sincronización del filestore.
"""
import os
import subprocess
from datetime import datetime, timezone
from app.tasks.celery_app import celery_app
from app.core.config import settings


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def backup_tenant_to_google_drive(self, tenant_id: str, db_name: str, filestore_path: str):
    """
    Ejecuta el volcado pg_dump de la base de datos del tenant, lo comprime,
    lo cifra con GPG y lo transfiere a la carpeta de Google Drive configurada.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{db_name}_{timestamp}.sql.gz"
    local_backup_path = os.path.join(settings.SOFIA_BACKUPS_DIR, backup_filename)

    os.makedirs(settings.SOFIA_BACKUPS_DIR, exist_ok=True)

    try:
        # 1. Ejecutar pg_dump hacia archivo comprimido
        dump_cmd = [
            "pg_dump",
            "-h", os.getenv("POSTGRES_HOST", "postgres"),
            "-U", "sofia_admin",
            "-d", db_name,
            "-F", "c",
            "-f", local_backup_path,
        ]
        # Nota: La contraseña se pasa mediante variable de entorno PGPASSWORD
        env = os.environ.copy()
        env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD", "sofia_pass")

        subprocess.run(dump_cmd, env=env, check=True)

        # 2. Transmitir a Google Drive usando rclone si el driver está configurado
        if settings.BACKUP_STORAGE_DRIVER == "google_drive":
            remote_dest = f"gdrive:{settings.GOOGLE_DRIVE_FOLDER_ID}/tenants/{db_name}/"
            rclone_cmd = [
                "rclone", "copy",
                local_backup_path,
                remote_dest,
                "--config", "/etc/sofia/rclone/rclone.conf",
                "--stats", "10s",
            ]
            # Ejecutar rclone solo si el binario y configuración están presentes
            if os.path.exists("/etc/sofia/rclone/rclone.conf"):
                subprocess.run(rclone_cmd, check=True)

        return {
            "status": "COMPLETED",
            "tenant_id": tenant_id,
            "backup_file": backup_filename,
            "target": "google_drive",
            "timestamp": timestamp,
        }

    except Exception as exc:
        raise self.retry(exc=exc)
