# Reglas de Trabajo Obligatorias del Proyecto SOFIA ERP

Este proyecto opera bajo el Skill y Runbook obligatorio: **`sofia-erp-architect`** localizado en `.agent/skills/sofia-erp-architect/SKILL.md`.

## Directrices Mandatorias para Cualquier Agente / Ingeniero

1. **Actuar como Equipo Multidisciplinario Senior:**
   - Arquitectura SaaS & Software.
   - Python 3.11 / FastAPI asíncrono, SQLAlchemy 2.0, Pydantic v2, Celery.
   - Odoo Community 20 (sin dependencias de Enterprise).
   - Localización Fiscal SUNAT (Perú) con UBL 2.1 y Guías de Remisión Electrónica (GRE 09/31).
   - PostgreSQL 16 con PgBouncer en modo de transacción.
   - DevOps, Linux, Nginx edge gateway y Docker Compose con redes aisladas.
   - Ciberseguridad, OIDC con PKCE, tokens JWT RS256 asimétricos con JWKS y MFA (TOTP).
   - Continuidad de servicio y resiliencia offline ante caídas del Control Plane.
   - Respaldo híbrido a Google Drive mediante `rclone` (ADR-006).

2. **Reglas de Seguridad Inquebrantables:**
   - **Prohibido exponer Docker Socket (`/var/run/docker.sock`)** a contenedores web.
   - **Prohibido exponer puertos de datos** (Postgres, Redis, PgBouncer, Celery) a Internet (`0.0.0.0`).
   - **Prohibido almacenar secretos** en el código o repositorio Git.
   - **Aislamiento Database-per-Tenant y Filestore Físico Separado:** Cada cliente tiene su propia base de datos física (`sofia_tenant_<slug>`).
   - **Protección contra Host Header Injection:** Nginx forzará siempre `X-Odoo-dbfilter` validado en base de datos.

3. **Metodología:**
   - Documentar antes de codificar.
   - Registrar cambios arquitectónicos mediante ADRs en `docs/adr/`.
   - Mantener pruebas automatizadas unitarias en `control-plane/backend/tests/`.
