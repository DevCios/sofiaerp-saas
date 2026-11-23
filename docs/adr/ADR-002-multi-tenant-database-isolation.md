# ADR-002: Estrategia de Multi-Tenancy y Aislamiento de Base de Datos y Filestore

- **Estado:** Propuesto / Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Arquitecto de Soluciones SaaS & Arquitecto PostgreSQL

## Contexto y Problema
En plataformas SaaS empresariales con Odoo existen dos alternativas para multi-tenancy:
1. *Multi-company en una sola base de datos:* Múltiples clientes residen en la misma base de datos de Odoo separados por `res.company` y reglas de registro (`ir.rule`).
2. *Base de datos y filestore independiente por tenant (Database-per-tenant):* Cada cliente tiene una base de datos PostgreSQL y un filestore físico segregado.

El enfoque 1 (Multi-company única) presenta riesgos inaceptables para un SaaS comercial:
- Fugas de datos por errores en reglas `ir.rule` o módulos de terceros mal programados.
- Imposibilidad de restaurar o migrar a un solo cliente sin afectar a todos los demás.
- Bloqueo de toda la plataforma durante migraciones de esquema o actualizaciones de módulos.
- Exposición a fugas de información contable y SUNAT crítica.

## Decisión
Se establece como **principio arquitectónico obligatorio**:
1. **Aislamiento Estricto Database-per-Tenant:** Cada tenant tendrá su propia base de datos PostgreSQL (`sofia_tenant_<uuid>`) y su propio directorio de filestore (`/var/lib/sofia/filestores/<tenant_id>/`).
2. **Modelos de Ejecución:**
   - **Shared Protected:** Múltiples bases de datos atendidas por un pool de procesos Odoo comunes (para clientes en planes Básico/Profesional), asegurando el filtrado estricto mediante cabeceras HTTP inmutables (`X-Odoo-dbfilter` / Nginx dynamic mapping) sin depender del selector web nativo de Odoo.
   - **Dedicated Runtime:** Contenedores Odoo y recursos de cómputo dedicados exclusivamente para clientes Empresariales o con requerimientos regulatorios especiales.
3. **Migración Transparente:** La arquitectura de enrutamiento en Nginx/Tenant Resolver permite migrar un cliente de *Shared Protected* a *Dedicated Runtime* sin cambios en su identidad, dominio ni datos.

## Consecuencias
### Positivas
- Aislamiento real de datos (GDPR, secreto comercial, cumplimiento tributario).
- Backup y restauración granular por tenant (PITR independiente).
- Eliminación del riesgo de "ruidoso vecino" a nivel de base de datos gracias a cuotas y límites de conexiones PostgreSQL (`pgbouncer`).

### Negativas / Mitigaciones
- Mayor consumo de memoria base por cada base de datos (mitigado mediante `pgbouncer` para pooling de conexiones y optimización de workers en modo compartido).
