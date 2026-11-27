# ADR-010: Conectores de IA (Remote MCP & OpenAPI AI) para Sofia SUNAT Gateway

- **Estado:** Aceptado (Fase 1)
- **Fecha:** 2026-11-27
- **Componente:** `sunat-gateway` (`gateway.sofiaerp.com`)
- **Relacionado con:** `ADR-008` (Sofia SUNAT Gateway — Caja Negra)

---

## 1. Contexto

Los usuarios y desarrolladores que integran facturación electrónica SUNAT cada vez operan más desde asistentes de IA (**Claude, ChatGPT, Cursor, VS Code Copilot, Gemini CLI**) y plataformas de automatización (**n8n, Make, Zapier**).

`sofia-sunat-gateway` ya cuenta con:
- Motor UBL 2.1 + firma XMLDSig + SOAP SUNAT + anti-`1033` + cola resiliente Celery.
- Aislamiento multi-tenant por `ApiClient.allowed_rucs` (`sk_live_...`).
- Idempotencia estricta por `(issuer_ruc, doc_type, serie, correlativo)`.

Se requiere exponer estas capacidades de forma nativa para asistentes de IA sin agregar dependencias pesadas ni relajar los controles de seguridad tributaria.

---

## 2. Decisión Arquitectónica

1. **Endpoint Remote MCP (`POST /mcp` y `GET /mcp`)** implementado de forma nativa sobre FastAPI siguiendo el estándar **Model Context Protocol (JSON-RPC 2.0 / Streamable HTTP `2025-03-26`)**:
   - Métodos soportados: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
   - Autenticación obligatoria mediante `Authorization: Bearer <sk_live_...>` o `X-API-Key: <sk_live_...>` reutilizando `get_api_client_or_admin` y `assert_ruc_access`.
2. **Herramientas MCP (Tools) expuestas en Fase 1:**
   - `calculate_totals_igv`: calcula subtotal, IGV (18%/10%/exonerado/inafecto) y total antes de emitir (solo lectura, sin enviar a SUNAT).
   - `explain_sunat_error`: traduce códigos de error/observación SUNAT (`0`, `1033`, `2017`, `2325`, `4000+`, etc.) a causa y acción correctiva.
   - `list_issuers`: lista los RUCs autorizados para la API Key (indicando si están en `BETA` o `PRODUCCIÓN`).
   - `list_documents`: consulta los últimos comprobantes emitidos (filtrable por RUC y estado).
   - `lookup_document`: consulta estado SUNAT, código CDR y URLs XML/CDR de un comprobante por `(issuer_ruc, doc_type, serie, correlativo)`.
   - `emit_document`: emite una Factura (`01`), Boleta (`03`) o Nota (`07`/`08`) usando la misma validación fiscal anti-rechazos, idempotencia y firma del Gateway.
3. **Esquema OpenAPI curado para IA (`GET /openapi-ai.json`)**:
   - Expone una especificación OpenAPI 3.1 limpia y acotada para **ChatGPT Custom GPT Actions**, **n8n**, **Make** y **Postman**.
4. **Panel Web `gateway.sofiaerp.com` — Pestaña `Conectores IA (MCP)`**:
   - Permite copiar la URL MCP, el esquema OpenAPI AI, snippets listos para **Claude Code / Claude Desktop / ChatGPT / Cursor / n8n**, y probar `tools/list` y `explain_sunat_error` en vivo siguiendo el Design System de Odoo 20.

---

## 3. Seguridad Tributaria

- **Zero Secrets en código:** las credenciales SOL y `.pfx` permanecen cifradas en Bóveda Fernet; jamás se devuelven en respuestas MCP.
- **Aislamiento por RUC:** toda invocación MCP con `ApiClient` valida `assert_ruc_access(api_client, issuer_ruc)`.
- **Idempotencia fiscal:** si la IA reintenta `emit_document` con la misma `(issuer_ruc, doc_type, serie, correlativo)`, el Gateway retorna `idempotent_replay: true` sin duplicar el envío a SUNAT.
- **Fase 2 (Planificada):** OAuth 2.1 con PKCE (integrado con el IdP OIDC de SOFIA Control Plane) para conexión 1-clic sin pegar API Keys en Claude.ai / ChatGPT.
