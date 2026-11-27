# ADR-012: Multi-Workspace Self-Service y Facturación de Planes con Mercado Pago (`apisunat.pro` / `gateway.sofiaerp.com`)

- **Estado:** Aceptado
- **Fecha:** 2026-11-27
- **Componente:** `sunat-gateway` (`gateway.sofiaerp.com` / `apisunat.pro`)
- **Relacionado con:** `ADR-008`, `ADR-010`, `ADR-011`

---

## 1. Contexto

Para comercializar `sofia-sunat-gateway` como plataforma API independiente (por ejemplo bajo `apisunat.pro`), además de servir a los tenants internos de SOFIA ERP, se requiere:
1. **Registro self-service de cuentas y Workspaces** con aislamiento estricto de datos por `workspace_id` (cada cliente solo ve y opera sus propios RUCs, comprobantes, API Keys y logs).
2. **Planes y recarga/upgrade con Mercado Pago** (Tarjetas, Yape, Plin, PagoEfectivo) que actualice automáticamente `Workspace.plan_name`, `Workspace.monthly_quota` y la cuota de sus empresas emisoras (`Issuer.monthly_quota`).
3. **Retrocompatibilidad total con SOFIA ERP:** el Superadmin (`GATEWAY_ADMIN_EMAIL`) y el mesh interno (`X-Internal-Service-Key`) mantienen visibilidad global sin cambios en los tenants existentes.

---

## 2. Decisiones Técnicas

1. **Nuevos modelos en `sofia_sunat_gateway_db`:**
   - `workspaces`: `id`, `name`, `slug`, `plan_name` (`FREE`/`STARTER`/`PRO`/`ENTERPRISE`), `monthly_quota` (default `50` en plan FREE), `plan_expires_at`, `is_active`.
   - `gateway_users`: `id`, `workspace_id`, `email` (unique), `full_name`, `password_hash` (`PBKDF2-HMAC-SHA256` con salt aleatorio de 16 bytes, 200,000 iteraciones — cero dependencias externas), `role` (`workspace_owner`), `is_active`.
   - `billing_orders`: `id`, `workspace_id`, `plan_code`, `quota_granted`, `amount_pen`, `status` (`PENDING` / `PAID` / `FAILED`), `mp_preference_id`, `mp_payment_id` (unique para idempotencia estricta), `paid_at`.
   - Columna `workspace_id` (nullable, migración idempotente `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) en `issuers`, `api_clients` y `api_request_logs`.
2. **Aislamiento Multi-Workspace en API:**
   - `create_user_jwt(...)` emite JWT con `role="workspace_owner"` y `workspace_id`.
   - `get_gateway_admin` (renombrado conceptualmente a acceso de consola: acepta `gateway_admin` global, `internal` mesh o `workspace_owner` acotado a su `workspace_id`).
   - Todas las rutas del panel (`/stats`, `/quota`, `/logs`, `/issuers`, `/clients`, `/documents`, `/summaries`, `/contingencies`, `/observations`) filtran automáticamente por `workspace_id` cuando el usuario es `workspace_owner`.
3. **Catálogo de Planes y Checkout Mercado Pago (`/api/v1/billing/*`):**
   - `FREE`: `50` comprobantes/mes (`S/ 0.00`).
   - `STARTER`: `500` comprobantes/mes (`S/ 39.00`).
   - `PRO`: `3,000` comprobantes/mes (`S/ 99.00`).
   - `ENTERPRISE`: `15,000` comprobantes/mes (`S/ 249.00`).
   - `POST /api/v1/billing/checkout` crea `BillingOrder` + preferencia Mercado Pago Checkout Pro (`MP_ACCESS_TOKEN`).
   - `GET /api/v1/billing/mp-callback` y `POST /api/v1/billing/mp-webhook` verifican el pago directamente en `api.mercadopago.com/v1/payments/{id}` (con validación HMAC `x-signature` opcional vía `MP_WEBHOOK_SECRET`), aplican el upgrade de forma idempotente y sincronizan `monthly_quota` en el Workspace y todos sus `issuers`.
