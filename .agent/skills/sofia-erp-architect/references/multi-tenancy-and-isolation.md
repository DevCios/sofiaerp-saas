# Referencia Técnica: Multi-Tenancy y Aislamiento de Tenants

## 1. Principio Database-per-Tenant

Queda estrictamente prohibido compartir una única base de datos multi-company de Odoo entre clientes comerciales SaaS.
- **Razón de Seguridad:** Evita fugas de datos por fallos en `ir.rule` o módulos de terceros.
- **Razón Operativa:** Permite respaldar, restaurar, clonar a un *staging lab* o migrar de versión a un solo cliente sin interrumpir a los demás.

## 2. Inyección de Cabecera y Enrutamiento en Nginx

Para evitar que el cliente manipule el selector de bases de datos de Odoo (`dbfilter` exploit):
1. Nginx recibe la petición con `Host: erp.empresa.com`.
2. Nginx resuelve el mapeo interno hacia el slug del tenant (ej. `empresa_com`).
3. Nginx reescribe la cabecera forzando:
   `proxy_set_header X-Odoo-dbfilter ^sofia_tenant_empresa_com$;`
4. El proceso de Odoo conecta directamente a esa base de datos y no lista otras en el selector web.

## 3. Contención de Fallas (Blast Radius)

- **Límites de Cómputo por Proceso Odoo:**
  - `limit_memory_hard = 1073741824` (1 GB máximo por worker).
  - `limit_memory_soft = 838860800` (800 MB umbral de reciclaje).
  - `limit_time_cpu = 60` (Timeout de 60 segundos de CPU).
  - `limit_time_real = 120` (Timeout de 120 segundos de tiempo real).
- **Límites de Base de Datos:**
  - `statement_timeout = 30000` (30 segundos máximo por consulta SQL).
  - `idle_in_transaction_session_timeout = 60000` (1 minuto máximo en transacción abierta).
- **Aislamiento de Sesiones en Redis:**
  - Concurrencia controlada atómicamente con scripts Lua en Redis (`HSETNX` / `INCRBY`).
