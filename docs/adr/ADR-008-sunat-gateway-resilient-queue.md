# ADR-008: Microservicio `sofia-sunat-gateway` (Caja Negra Resiliente SUNAT Multi-App)

- **Estado:** Aprobado
- **Fecha:** 2026-11-26
- **Autor:** Equipo de Arquitectura SOFIA ERP
- **Dominio Oficial:** `https://gateway.sofiaerp.com`

---

## 1. Contexto y Problema

En Perú, los contribuyentes bajo el esquema **SEE del Contribuyente (SUNAT Directo)** enfrentan intermitencias frecuentes en los servidores SOAP/REST de SUNAT (`HTTP 500/502/503`, timeouts, cortes de red que provocan el error `1033` *"El comprobante fue registrado previamente"*). Muchas empresas recurren a OSEs comerciales (como NubeFact) pagando comisiones mensuales o por comprobante solo para evitar que sus cajas/POS se bloqueen.

SOFIA ERP necesita un servicio propio, desacoplado y multi-tenant ("Caja Negra") que:
1. Permita emitir, firmar XML UBL 2.1 localmente con `.pfx`, generar Hash/QR e imprimir comprobantes en **< 300 ms** aunque SUNAT esté caído.
2. Envíe a SUNAT de forma asíncrona con reintentos inteligentes (backoff exponencial + ventana nocturna configurable) dentro del plazo legal vigente (3 días calendario para Facturas/Notas, 7 días para Boletas).
3. Recupere automáticamente CDRs perdidos mediante `getStatusCdr` ante cortes o error `1033`.
4. Exponga una API REST limpia y un Panel Web propio (`gateway.sofiaerp.com`) utilizable tanto por **SOFIA ERP (Odoo 20)** como por **apps, POS y sistemas de terceros**.

---

## 2. Decisión Arquitectónica

Se implementa el microservicio independiente **`sunat-gateway/`** con:

- **Backend API:** Python 3.11 + FastAPI asíncrono + Pydantic v2 + SQLAlchemy 2.0 (`asyncpg`).
- **Base de Datos Aislada:** `sofia_sunat_gateway_db` en la instancia PostgreSQL existente (sin compartir tablas con `sofia_central_db` ni con tenants Odoo).
- **Cola Resiliente:** Celery + Redis (DB lógica `3`/`4` dedicada) con 4 colas especializadas (`sunat_realtime`, `sunat_retry`, `sunat_night_batch`, `sunat_webhooks`) y Celery Beat para lotes nocturnos y alertas de plazo.
- **Seguridad y Cifrado en Reposo:**
  - Todos los certificados `.pfx`, contraseñas `.pfx`, Claves SOL y secretos GRE se cifran en reposo con **Fernet (AES-128-CBC + HMAC-SHA256)** derivado de `SUNAT_VAULT_MASTER_KEY` (inyectada por entorno, nunca en Git).
  - API Keys con prefijo (`sk_live_...` / `sk_test_...`) almacenadas únicamente como hash **SHA-256**.
  - Panel Web protegido con autenticación de administrador (JWT HS256/RS256).
  - Webhooks salientes firmados con **HMAC-SHA256** (`X-Sofia-Signature`).
  - Zero Docker Socket exposure; zero puertos de Postgres/Redis expuestos a Internet.
- **Modos de Entrada Duales:**
  - **JSON simplificado** (estilo API moderna para POS/apps externas): genera XML UBL 2.1, valida, firma y encola.
  - **XML Passthrough** (ideal para SOFIA ERP / Odoo 20): recibe XML UBL 2.1 ya construido (firmado o sin firmar), firma si falta, valida y gestiona toda la cola resiliente y recuperación de CDR.

---

## 3. Consecuencias

### Positivas
- **Costo \$0 por comprobante** en SUNAT Directo con continuidad operativa equivalente a un OSE para el punto de venta.
- **Producto SaaS reutilizable:** Puede monetizarse como API independiente para terceros (`gateway.sofiaerp.com`).
- **Bajo consumo de RAM (~150–200 MB):** Apto para el VPS actual de 4 GB RAM y listo para migrar a un nodo dedicado mediante Docker Compose cuando escale.

### Riesgos y Mitigaciones
- **Pérdida de `SUNAT_VAULT_MASTER_KEY`:** Impediría descifrar `.pfx` y Claves SOL. *Mitigación:* Respaldar la clave maestra en gestor de secretos externo fuera del servidor.
- **Plazo legal de 3 días calendario:** *Mitigación:* Alertas automáticas a las 24h y 48h sin CDR + botón de recuperación manual `getStatusCdr` en el panel.
