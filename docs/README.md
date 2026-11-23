# SOFIA ERP — Arquitectura y Documentación Técnica

Bienvenido al repositorio central de **SOFIA ERP**, una plataforma SaaS multiproducto, multi-tenant y de alta resiliencia diseñada para el mercado empresarial.

## Estructura del Repositorio

- `docs/architecture/`: Especificaciones de arquitectura de sistemas, seguridad y redes.
- `docs/adr/`: Architecture Decision Records (Registros de Decisiones Arquitectónicas).
- `docs/specs/`: Especificaciones funcionales y contratos de API.
- `control-plane/`: SOFIA Platform (FastAPI, SQLAlchemy, Celery, Alembic).
- `runtime/`: Configuraciones de ejecución de productos (Odoo Community, Addons, Nginx).
- `deploy/`: Automatización de infraestructura (Docker Compose, scripts de aprovisionamiento, hardening).

## Índice de ADRs (Architecture Decision Records)
- [ADR-001: Separación de Planos (Control Plane, Runtime Plane, Data Plane)](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/adr/ADR-001-control-plane-runtime-plane-separation.md)
- [ADR-002: Estrategia de Multi-Tenancy y Aislamiento de Base de Datos y Filestore](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/adr/ADR-002-multi-tenant-database-isolation.md)
- [ADR-003: Compatibilidad de Versiones de Odoo y Ecosistema de Módulos (SUNAT / OCA)](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/adr/ADR-003-odoo-runtime-versioning-and-oca-compatibility.md)
- [ADR-004: Identidad Centralizada (OIDC) y Resiliencia Operativa Offline](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/adr/ADR-004-central-identity-oidc-offline-resilience.md)
- [ADR-005: Aprovisionamiento Seguro sin Exposición del Docker Socket](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/adr/ADR-005-secure-provisioning-without-docker-socket-exposure.md)
