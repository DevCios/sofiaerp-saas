# Playbook de Ejecución por Fases (Fases 1 a 7)

Este playbook describe las metas, entregables obligatorios y puntos de validación para cada fase de desarrollo de SOFIA ERP.

---

## FASE 1 — FOUNDATION (Completada)
- **Metas:** Repositorio Git inicializado, topología Docker Compose con 3 redes aisladas, Nginx edge proxy con cabeceras de seguridad y `X-Odoo-dbfilter`, base del Control Plane en FastAPI, SQLAlchemy 2.0, modelos ORM de Tenants/Usuarios/Planes, Celery para tareas asíncronas, suite de pruebas inicial y CI/CD en GitHub Actions.

---

## FASE 2 — IDENTITY & TENANT MANAGEMENT
- **Metas:**
  1. Servidor de Identidad completo con OAuth 2.0 y OpenID Connect (PKCE).
  2. Implementación de MFA (RFC 6238 TOTP con QR y códigos de recuperación).
  3. Tenant Resolver dinámico con soporte de subdominios (`<tenant>.erp.sofiaerp.com`).
  4. Validador de Dominios Personalizados: verificación DNS TXT (`_sofia-challenge`) y CNAME con `dnspython`.
  5. Automatización de certificados Let's Encrypt para dominios verificados.
  6. Medición y control de concurrencia atómica en Redis con expiración de sesiones por inactividad.

---

## FASE 3 — ODOO RUNTIME & APROVISIONAMIENTO
- **Metas:**
  1. Integración profunda del módulo puente `sofia_auth_bridge` en Odoo 20.
  2. Automatización del aprovisionamiento de Odoo: creación de base de datos PostgreSQL, ejecución de `odoo -i base --no-http`, configuración de secuencias y sembrado de datos de prueba.
  3. Aislamiento físico de filestore en volumen montado con permisos 0750.
  4. Monitoreo de memoria y reciclaje de workers en el pool compartido.

---

## FASE 4 — SUNAT, GUÍAS DE REMISIÓN (GRE) & ENTITLEMENTS
- **Metas:**
  1. Integración y certificación del módulo de Facturación Electrónica para Odoo 20 (Facturas, Boletas, Notas de Crédito y Débito).
  2. Integración de Guías de Remisión Electrónica Remitente y Transportista (GRE).
  3. Cifrado y almacenamiento seguro de certificados digitales `.pfx` en base de datos.
  4. Evaluador de capacidades (*Entitlements*): `custom_domain`, `custom_logo`, `custom_colors`, `white_label`.
  5. Degradación elegante de capacidades sin destrucción de configuraciones previas.

---

## FASE 5 — COMERCIALIZACIÓN & BILLING
- **Metas:**
  1. Motor de facturación comercial SaaS de SOFIA Platform (emisión de cobros recurrentes de suscripciones, almacenamiento extra y usuarios adicionales).
  2. Control de morosidad y máquina de estados de suscripción (`ACTIVE`, `PAST_DUE`, `SUSPENDED`).
  3. Portal Web del Cliente en Next.js / Tailwind CSS (Selector de empresas, visualización de consumo, perfiles y dispositivos).
  4. Pruebas de estrés y concurrencia simulando los 10 clientes comerciales.

---

## FASE 6 — OPERACIONES, OBSERVABILIDAD & DR
- **Metas:**
  1. Pipeline automatizado de backups en Celery con cifrado GPG y sincronización hacia Google Drive mediante `rclone`.
  2. Simulación y prueba formal de restauración de base de datos y filestore ante desastre.
  3. Despliegue del stack de observabilidad: Prometheus, Grafana, Loki y Alertmanager.
  4. Dashboards de salud por tenant, consumo de CPU/RAM, conexiones PostgreSQL y almacenamiento.
  5. Auditoría final de ciberseguridad y plan de onboarding comercial de los 10 clientes.

---

## FASE 7 — EVOLUCIÓN MULTIPRODUCTO
- **Metas:**
  1. Incorporación de nuevas líneas comerciales: *SOFIA Industrial Services* y *SOFIA Quality*.
  2. Multi-Version Runtime Manager y Migration Lab para transiciones de versiones mayores de Odoo.
  3. Soporte para Dedicated Runtimes (contenedores exclusivos para clientes empresariales).
