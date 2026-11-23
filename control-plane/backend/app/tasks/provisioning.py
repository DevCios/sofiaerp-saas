"""
Tareas Celery de Aprovisionamiento Seguro de Tenants (ADR-005).
Crea base de datos PostgreSQL, inicializa filestore y actualiza estado sin exponer Docker socket.
"""
import os
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.services.provisioning_service import ProvisioningService, ProvisioningError


def dispatch_tenant_provisioning(tenant_id: str, db_name: str, filestore_path: str):
    """Encola la tarea de aprovisionamiento en Celery."""
    provision_tenant_task.delay(tenant_id, db_name, filestore_path)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def provision_tenant_task(self, tenant_id: str, db_name: str, filestore_path: str):
    """
    Orquestador asíncrono de aprovisionamiento:
    1. Crea la base de datos PostgreSQL de forma aislada con cuota de conexiones.
    2. Crea el directorio de filestore con permisos 0750.
    """
    try:
        slug = db_name.replace("sofia_tenant_", "").replace("_", "-")
        result = ProvisioningService.provision_tenant_pipeline(
            slug=slug,
            base_filestore_dir=settings.SOFIA_FILESTORES_DIR,
            pg_host=os.getenv("POSTGRES_HOST", "postgres"),
            pg_port=int(os.getenv("POSTGRES_PORT", 5432)),
            admin_user=os.getenv("POSTGRES_USER", "sofia_admin"),
            admin_password=os.getenv("POSTGRES_PASSWORD", "sofia_pass"),
            owner_user=os.getenv("ODOO_DB_USER", "odoo_runtime_user"),
        )
        return {
            "status": "SUCCESS",
            "tenant_id": tenant_id,
            "pipeline_result": result,
        }
    except ProvisioningError as exc:
        raise self.retry(exc=exc)
