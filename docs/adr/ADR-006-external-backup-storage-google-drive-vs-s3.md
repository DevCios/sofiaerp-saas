# ADR-006: Estrategia de Almacenamiento Externo de Backups (Google Drive vs Object Storage S3/GCS y WAL Archiving)

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Arquitecto PostgreSQL, Ingeniero DevOps & Especialista en Continuidad y DR

## Contexto y Problema
Se consulta sobre la viabilidad de utilizar **Google Drive** como proveedor de almacenamiento externo para las copias de seguridad de SOFIA ERP y el archivado de WAL (Write-Ahead Logging).

## Análisis Técnico y Evaluación de Riesgos

### 1. Backups Periódicos en Frío / Snapshots (pg_dump y Filestore)
- **Viabilidad:** **100% Viable y Recomendado.**
- **Mecanismo:** Tareas programadas en Celery o cron que generan un archivo comprimido y cifrado con GPG (`backup_sofia_tenant_<id>_YYYYMMDD.sql.gz` y comprimido del filestore) y lo transmiten a Google Drive mediante **`rclone`** utilizando una cuenta de servicio (Service Account de Google Cloud) o credenciales OAuth2 seguras.
- **Ventajas:** Aprovecha el almacenamiento corporativo ya existente de la empresa (Google Workspace), reduce a cero el costo adicional de infraestructura de almacenamiento para el MVP de 10 clientes, y mantiene las copias fuera del datacenter del servidor principal.

### 2. Archivado Continuo de WAL y Point-In-Time Recovery (PITR)
- **Viabilidad en Google Drive:** **Técnicamente No Recomendado / Riesgo Alto.**
- **Motivos Técnicos:**
  1. *Límites de API de Google Drive:* Las cuotas de llamadas a la API de Drive imponen restricciones estrictas de operaciones por segundo y cuotas de subida diaria. PostgreSQL genera segmentos WAL de 16 MB continuamente durante picos de transacciones. Superar las cuotas de la API de Drive provocaría que el comando `archive_command` de PostgreSQL falle (`non-zero exit code`), lo cual detiene el reciclaje de WAL y puede llenar el disco del servidor de base de datos hasta bloquear el sistema.
  2. *Incompatibilidad con herramientas estándar:* Motores como `wal-g`, `pgBackRest` y `barman` están diseñados para APIs de Object Storage (S3, GCS, Azure Blob) o sistemas de archivos POSIX locales. No existe conector nativo para la API de Google Drive sin recurrir a montajes FUSE tipo `rclone mount`, los cuales presentan latencias altas, inestabilidad de red y riesgo de corrupción en operaciones sincrónicas de archivado.

## Decisión Arquitectónica (Estrategia Híbrida / Tiered Backup)

1. **Nivel 1 — Backups Diarios, Semanales y de Filestore hacia Google Drive:**
   - Se aprueba el uso de **Google Drive** como repositorio externo primario para el resguardo de copias de seguridad completas de las bases de datos de los tenants y de los filestores.
   - Todo backup se cifrará simétricamente con AES-256 (GPG) antes de salir del servidor hacia Google Drive, garantizando la privacidad de los datos frente al proveedor de nube.
2. **Nivel 2 — Estrategia de WAL y PITR para el MVP (10 Clientes):**
   - **Planes Básico y Profesional:** RPO garantizado de 4 h a 24 h mediante snapshots periódicos exportados a Google Drive.
   - **Plan Empresarial (PITR):** El archivado continuo de WAL se almacena temporalmente en un volumen local SSD dedicado con retención de 48 horas. Si un cliente empresarial contrata SLA de PITR continuo en nube (< 15 minutos de RPO ante catástrofe total de datacenter), se habilitará un bucket S3 compatible ultrabarato (ej. Cloudflare R2 o Wasabi, con costo < $2/mes) exclusivo para el stream de WAL mediante `wal-g`.

## Consecuencias
- **Positivas:** Reducción drástica del costo operativo inicial; cumplimiento de la directiva de backups externos fuera del datacenter; seguridad garantizada mediante cifrado previo al envío.
- **Negativas / Mitigaciones:** Documentar claramente en los SLAs del servicio que la recuperación Point-In-Time a nivel de segundo (PITR) en nube requiere el tier con bucket S3/GCS, mientras que la recuperación estándar por snapshots en Google Drive cubre intervalos programados.
