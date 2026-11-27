# Reglas de Trabajo Obligatorias del Proyecto SOFIA ERP

Este proyecto opera bajo el Skill y Runbook obligatorio: **`sofia-erp-architect`** localizado en `.agent/skills/sofia-erp-architect/SKILL.md`.

## Directrices Mandatorias para Cualquier Agente / Ingeniero

1. **Actuar como Equipo Multidisciplinario Senior:**
   - Arquitectura SaaS & Software.
   - Python 3.11 / FastAPI asíncrono, SQLAlchemy 2.0, Pydantic v2, Celery.
   - Odoo Community 20 (sin dependencias de Enterprise, siguiendo estrictamente `references/odoo-20-engineering-standards.md`).
   - Localización Fiscal SUNAT (Perú) con UBL 2.1, Guías de Remisión Electrónica (GRE 09/31) y `sofia-sunat-gateway` (`gateway.sofiaerp.com`).
   - Especialista Senior UI/UX de eCommerce de Alta Conversión y Operación Funcional/Administrativa de Marketplace Multi-Vendedor (**Mercado Wanka** `addons_mw`: comisiones `5% + S/ 0.50`, facturación solo por comisión, custodia Escrow, KYC bancario, Mercado Pago HMAC, Outbox asíncrono e INDECOPI — `references/marketplace-ui-ux-and-ops.md`).
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

3. **Metodología y Estándar Visual (UI/UX):**
   - Documentar antes de codificar.
   - Registrar cambios arquitectónicos mediante ADRs en `docs/adr/`.
   - Mantener pruebas automatizadas unitarias en `control-plane/backend/tests/` y `sunat-gateway/tests/`.
   - **Design System Obligatorio (Odoo 20):** Todo desarrollo frontend en `sofiaerp.com` (Control Plane, Sofia Gateway, Website/Portal y módulos web) debe seguir la paleta y layout oficial de **Odoo 20** documentado en `docs/design-system-odoo20.md` (Navbar `#66598F`, Primario `#714B67`, Teal `#017E84`, fondo `#F6F7F9`, superficies `#FFFFFF`, KPIs pastel).
