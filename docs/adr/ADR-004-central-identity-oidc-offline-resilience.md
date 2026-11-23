# ADR-004: Identidad Centralizada (OIDC) y Resiliencia Operativa Offline

- **Estado:** Propuesto / Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Especialista en Ciberseguridad & Arquitecto de Software

## Contexto y Problema
El sistema requiere autenticación única mediante OAuth 2.0 / OpenID Connect (OIDC) en SOFIA Central (`auth.sofiaerp.com`), soporte para dominios personalizados (`erp.cliente.com`), MFA y selección de empresas.
A la vez, el requerimiento estipula una regla crítica de continuidad:
*Si SOFIA Central deja de funcionar, los ERP que ya están operativos deben poder continuar trabajando dentro de políticas de seguridad controladas.*

Si cada llamada HTTP a Odoo requiriera consultar síncronamente al Control Plane, una caída o lentitud en SOFIA Central dejaría a todos los clientes inoperativos (Single Point of Failure).

## Decisión
1. **Flujo de Autenticación OIDC:**
   - Flujo *Authorization Code Flow con PKCE*.
   - El Control Plane emite tokens JWT firmados con clave privada asimétrica (algoritmo RS256 o EdDSA).
   - El Control Plane expone un endpoint público de JWKS (`/.well-known/jwks.json`).
2. **Validación Local y Caché Criptográfico:**
   - El Runtime Odoo (mediante un addon puente ligero `sofia_auth_bridge`) descarga y almacena en caché local las claves públicas (JWKS).
   - Valida la firma del JWT, emisor (`iss`), audiencia (`aud`), fecha de expiración (`exp`) y claims del tenant de forma 100% autónoma en memoria.
3. **Resiliencia ante Caída del Control Plane:**
   - Los usuarios con sesiones activas o tokens vigentes continúan trabajando sin interrupciones.
   - En caso de desconexión del Control Plane:
     - Nuevos registros o provisionamientos quedan en cola.
     - Cambios en el plan de suscripción se posponen.
     - Los tokens tienen un tiempo de vida (TTL) controlado (ej. 4 a 8 horas con refresh token o extensión de gracia regulada).
     - Si expira el token y el Control Plane no responde, se entra en modo de gracia limitado o cierre seguro según la política configurada.

## Consecuencias
- Alta resiliencia operativa: desacoplamiento del ciclo de vida entre la plataforma central y las operaciones del día a día de las fábricas y comercios.
- Máxima seguridad sin compartir secretos simétricos entre runtimes.
