# Referencia Técnica: Estrategia de Backups y Google Drive (ADR-006)

## 1. Arquitectura Híbrida de Respaldos

```text
┌────────────────────────────────────────────────────────┐
│ Servidor de Producción SOFIA ERP (PostgreSQL 16)       │
└──────────────────────────┬─────────────────────────────┘
                           │
    ┌──────────────────────┴──────────────────────┐
    ▼                                             ▼
[ Nivel 1: Snapshots Periódicos ]          [ Nivel 2: WAL Streaming ]
  - Volcados pg_dump -F c                   - Segmentos WAL (16 MB c/u)
  - Filestore comprimido (tar.gz)           - Almacenamiento SSD local (48h)
  - Cifrado GPG simétrico (AES-256)         - wal-g hacia bucket S3 opcional
  - Sincronización rclone hacia:              (Solo para planes Enterprise
    Google Drive (Cero costo adicional)        con RPO < 15 min)
```

## 2. Pipeline de Envío a Google Drive mediante `rclone`

1. **Configuración de `rclone`:**
   - Ubicación: `/etc/sofia/rclone/rclone.conf` (montado en modo solo lectura en el worker de Celery).
   - Tipo de autenticación: Service Account JSON o Client ID/Secret OAuth2 de Google Cloud.
2. **Procedimiento de Ejecución:**
   - La tarea Celery ejecuta `pg_dump` con compresión máxima.
   - Aplica cifrado con contraseña segura mediante GPG:
     `gpg --symmetric --cipher-algo AES256 --batch --passphrase "$BACKUP_GPG_KEY" -o backup.sql.gz.gpg backup.sql.gz`
   - Transfiere el archivo cifrado a la carpeta designada:
     `rclone copy backup.sql.gz.gpg gdrive:sofia_backups/tenants/<tenant_slug>/`
   - Elimina el archivo temporal local para no saturar el almacenamiento NVMe del servidor.

## 3. Limitaciones Críticas de Google Drive frente a WAL Archiving
- Google Drive impone cuotas de llamadas API por segundo y cuotas de subida diaria.
- **Prohibido:** Configurar `archive_command = 'rclone copy %p gdrive:...'` directamente en `postgresql.conf`. Provoca saturación de cuotas, fallos en el archivado y llenado catastrófico del disco del servidor.
