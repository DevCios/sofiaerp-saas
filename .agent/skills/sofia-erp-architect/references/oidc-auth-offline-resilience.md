# Referencia Técnica: Identidad OIDC y Resiliencia Operativa Offline

## 1. Arquitectura de Identidad Central (OIDC)

- **Proveedor:** SOFIA Platform (`auth.sofiaerp.com`).
- **Flujo:** Authorization Code Flow con PKCE (RFC 7636).
- **Emisión de Tokens:**
  - JWT firmado con algoritmo asimétrico **RS256** (RSA 4096-bit).
  - Claims incluidos:
    - `iss`: `"https://auth.sofiaerp.com"`
    - `sub`: User UUID
    - `aud`: `"sofia-platform"`
    - `tenant_id`: UUID del tenant en contexto
    - `roles`: `["TENANT_ADMIN"]` o `["OPERATOR"]`
    - `exp`: Timestamp de expiración (TTL recomendado: 8 horas)

## 2. Publicación de Claves Públicas (JWKS)

- Endpoint expuesto por el Control Plane:
  `GET https://auth.sofiaerp.com/.well-known/jwks.json`
- Formato RFC 7517 con Key ID (`kid`) para rotación programada sin interrupción de servicio.

## 3. Resiliencia Operativa Offline en Runtimes de Odoo

Para garantizar que una falla del Control Plane no detenga la operación:
1. El runtime Odoo almacena en caché local las claves públicas descargadas de `auth.sofiaerp.com/.well-known/jwks.json` o montadas en `/etc/sofia/keys/jwt_public.pem`.
2. Cuando el usuario envía una petición con su sesión o token JWT, Odoo valida:
   - Validez matemática de la firma con la clave pública en memoria.
   - Fecha de expiración (`exp > now`).
   - Audiencia y emisor correspondientes.
3. Si el Control Plane está caído, la validación se ejecuta **100% en local sin tráfico de red**.
4. El usuario sigue creando cotizaciones, despachando pedidos y emitiendo facturas electrónicas.
