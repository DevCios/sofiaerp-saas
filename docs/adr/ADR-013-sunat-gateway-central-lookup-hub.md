# ADR-013: Hub Central de Consultas Fiscales Perú (RUC, DNI y Tipo de Cambio SUNAT) en Sofia Gateway

- **Estado:** Aceptado
- **Fecha:** 2026-11-27
- **Componentes:** `sunat-gateway` (`gateway.sofiaerp.com` / `apisunat.pro`) y `products/sofia-erp/addons/l10n_pe_sunat`
- **Relacionado con:** `ADR-008`, `ADR-010`, `ADR-011`, `ADR-012`

---

## 1. Contexto

Actualmente cada tenant de SOFIA ERP o aplicación externa necesita consultar:
- Padrón RUC (SUNAT) para autocompletar razón social, dirección, ubigeo, estado y condición.
- Padrón DNI (RENIEC) para autocompletar nombres completos en Boletas/POS.
- Tipo de Cambio oficial SUNAT (USD → PEN compra/venta) de forma diaria para contabilidad y facturación en dólares.

Hacer estas llamadas desde cada tenant o app multiplica los costos de APIs externas, duplica tokens y expone al POS/ERP a caídas de terceros.

---

## 2. Decisión Arquitectónica

Centralizar todas las consultas en **`sofia-sunat-gateway`** con **caché compartido en PostgreSQL** y **sincronización diaria automática**:

1. **Modelos de caché persistente en `sofia_sunat_gateway_db`:**
   - `identity_cache`: almacena consultas `RUC` (TTL 7 días) y `DNI` (TTL 30 días) en JSONB normalizado.
   - `exchange_rates`: almacena el tipo de cambio oficial SUNAT por fecha (`rate_date`, `currency='USD'`, `buy_rate`, `sell_rate`, `source`).
2. **Servicio multi-fuente resiliente (`app/services/lookup_service.py`):**
   - **RUC / DNI:** consulta primero caché vigente; si expiró o no existe, consulta `apis.net.pe` / `apisperu` (configurable vía `LOOKUP_API_TOKEN` / `APIS_NET_PE_TOKEN`) y guarda en caché; si el proveedor externo falla, devuelve el último registro cacheado (`stale_fallback=True`) en lugar de romper el POS.
   - **Tipo de Cambio SUNAT:** consulta la API oficial SUNAT (`api.apis.net.pe/v1/tipo-cambio-sunat` / `api.decolecta.com` / `e-consulta.sunat.gob.pe`) con fallback automático al último día hábil almacenado en fines de semana y feriados.
3. **Automatización diaria (Celery Beat):**
   - Tarea `sync_daily_exchange_rate_task` ejecutada cada mañana (07:30 AM hora Lima) y también al arranque/demanda.
4. **Exposición unificada:**
   - **REST API:** `GET /api/v1/lookup/ruc/{ruc}`, `GET /api/v1/lookup/dni/{dni}`, `GET /api/v1/lookup/exchange-rate`.
   - **Remote MCP (`/mcp`) y `/openapi-ai.json`:** 3 nuevas herramientas (`lookup_ruc`, `lookup_dni`, `get_exchange_rate`).
   - **SOFIA ERP (Odoo 20):** `l10n_pe_sunat` consume el Gateway por red interna Docker (`http://sunat-gateway-api:8010/api/v1/lookup/...`) con `X-Internal-Service-Key` para RUC, DNI y cron diario de `res.currency.rate` (USD/PEN).
