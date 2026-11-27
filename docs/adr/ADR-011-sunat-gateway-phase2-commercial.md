# ADR-011: Sofia SUNAT Gateway — Fase 2 Comercial (OAuth 2.1 PKCE, Logs API/MCP, Cuotas y Docs Portal)

- **Estado:** Aceptado
- **Fecha:** 2026-11-27
- **Componente:** `sunat-gateway` (`gateway.sofiaerp.com`)
- **Relacionado con:** `ADR-008`, `ADR-010`

---

## 1. Contexto

Tras habilitar el servidor Remote MCP (`/mcp`) y `/openapi-ai.json` en Fase 1 (`ADR-010`), se requiere elevar `gateway.sofiaerp.com` a nivel de plataforma comercial *Developer-First* (comparable a `apisunat.net` / Stripe) para soportar:
1. Conexión **1-clic sin copiar API Keys** desde **Claude.ai** y **ChatGPT Connectors** mediante **OAuth 2.1 + PKCE (`S256`)** y **Dynamic Client Registration (RFC 7591)**.
2. **Observabilidad completa** de peticiones HTTP/REST y llamadas de herramientas MCP (`ApiRequestLog`).
3. **Control de cuota mensual de comprobantes** por empresa emisora (`Issuer.monthly_quota`, `Issuer.plan_name`) con visualización en barra segmentada.
4. **Portal de Documentación Interactiva (`/docs-portal`)** con guías, ejemplos cURL/Python/MCP y referencia OpenAPI dinámica cargada desde `/openapi-ai.json`.

---

## 2. Decisiones Técnicas

1. **OAuth 2.1 + PKCE para MCP (`sunat-gateway/app/api/oauth_mcp.py`):**
   - `GET /.well-known/oauth-protected-resource` (RFC 9728) apuntando a `gateway.sofiaerp.com`.
   - `GET /.well-known/oauth-authorization-server` (RFC 8414) declarando `code_challenge_methods_supported: ["S256"]`.
   - `POST /oauth/register` (RFC 7591) persistiendo clientes OAuth en la tabla `oauth_clients`.
   - `GET /oauth/authorize` y `POST /oauth/authorize`: pantalla de consentimiento con Design System Odoo 20 donde el usuario se autentica (cuenta admin Gateway o API Key `sk_live_...`), selecciona el RUC permitido (o todos) y autoriza la emisión de un código PKCE de 5 minutos (`oauth_auth_codes`, de un solo uso).
   - `POST /oauth/token`: valida `code_verifier` contra `code_challenge` (`SHA-256` base64url) y emite un JWT `access_token` (`scope="mcp:sunat"`, `allowed_rucs=[...]`, TTL 30 días) reconocido directamente por `get_api_client_or_admin`.
2. **Auditoría API/MCP y Cuotas Mensuales:**
   - Nueva tabla `api_request_logs` con `source` (`MCP` / `REST`), `action`, `issuer_ruc`, `client_label`, `status_code`, `latency_ms`, `error_summary`.
   - Nuevas columnas en `issuers`: `plan_name` (default `'STARTER'`) y `monthly_quota` (default `500`), aplicadas mediante `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` idempotente en `lifespan`.
   - Nuevos endpoints: `GET /api/v1/logs` y `GET /api/v1/quota`.
3. **Portal de Documentación (`/docs-portal`):**
   - Interfaz limpia de 3 columnas (Sidebar + Contenido + "En esta página") respetando el Design System Odoo 20, con pestañas **Guía**, **Ejemplos** y **Referencia API** (autogenerada desde `/openapi-ai.json`), lista para operar en `gateway.sofiaerp.com/docs-portal` o exponerse bajo `docs.sofiaerp.com`.
