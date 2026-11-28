#!/usr/bin/env bash
# ==============================================================================
# SOFIA ERP — Backup Diario Completo de Producción (BDs + XML/CDR SUNAT)
# Uso recomendado en crontab (02:30 AM hora Lima):
#   30 2 * * * /opt/sofiaerp/infrastructure/docker/backups/backup_platform.sh >> /var/log/sofia-backup.log 2>&1
# ==============================================================================
set -euo pipefail

BACKUP_ROOT="/var/backups/sofiaerp"
STAMP="$(date +%Y-%m-%d_%H%M)"
DAY_DIR="${BACKUP_ROOT}/${STAMP}"
RETENTION_DAYS=14
PG_USER="${POSTGRES_USER:-sofia_admin}"

mkdir -p "${DAY_DIR}"
echo "[$(date -Iseconds)] Iniciando backup completo SOFIA ERP en ${DAY_DIR}"

# 1. Respaldo de bases de datos críticas (Control Plane + Sofia Gateway)
for db in sofia_central_db sofia_sunat_gateway_db; do
  echo "  -> pg_dump ${db}"
  docker exec sofia-postgres pg_dump -U "${PG_USER}" -d "${db}" | gzip -9 > "${DAY_DIR}/${db}.sql.gz"
done

# 2. Respaldo de todas las bases de datos de tenants Odoo 20
for db in $(docker exec sofia-postgres psql -U "${PG_USER}" -d postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'sofia_tenant_%';"); do
  echo "  -> pg_dump ${db}"
  docker exec sofia-postgres pg_dump -U "${PG_USER}" -d "${db}" | gzip -9 > "${DAY_DIR}/${db}.sql.gz"
done

# 3. Respaldo de XML firmados y CDRs SUNAT (obligación legal 5 años)
echo "  -> tar sofia_sunat_storage (XML + CDR)"
docker exec sofia-sunat-gateway-api tar -czf - -C /var/lib/sofia-sunat storage > "${DAY_DIR}/sofia_sunat_storage.tar.gz"

# 3B. Respaldo de Filestore Odoo 20 (imágenes de productos, logos y adjuntos de todos los tenants y Mercado Wanka)
echo "  -> tar sofia_filestores (Odoo /var/lib/odoo, excluyendo sessions)"
docker exec sofia-odoo-runtime-shared tar --exclude='./sessions' -czf - -C /var/lib/odoo . > "${DAY_DIR}/sofia_odoo_filestores.tar.gz"

# 4. Sincronización opcional hacia Google Drive si rclone + service_account.json están presentes
RCLONE_CONF="/opt/sofiaerp/infrastructure/docker/backups/rclone.conf"
SA_JSON="/opt/sofiaerp/infrastructure/docker/backups/service_account.json"
if command -v rclone >/dev/null 2>&1 && [[ -f "${RCLONE_CONF}" ]] && [[ -f "${SA_JSON}" ]]; then
  echo "  -> Subiendo backup a Google Drive vía rclone..."
  rclone copy "${DAY_DIR}" "gdrive:sofia-backups/${STAMP}" --config "${RCLONE_CONF}"
fi

# 5. Rotación local (conservar últimos 14 días)
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +
echo "[$(date -Iseconds)] Backup completado correctamente."
