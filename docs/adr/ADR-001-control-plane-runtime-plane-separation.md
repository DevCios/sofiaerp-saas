# ADR-001: Separación de Planos (Control Plane, Runtime Plane, Data Plane)

- **Estado:** Propuesto / Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Equipo de Arquitectura SOFIA ERP

## Contexto y Problema
SOFIA ERP es una plataforma SaaS comercial multiproducto. Un error común en implementaciones SaaS basadas en Odoo es acoplar la administración de la plataforma (facturación SaaS, aprovisionamiento de tenants, gestión de suscripciones) dentro de la misma instancia de Odoo de los clientes o en una base de datos Odoo "master". Esto produce riesgos de seguridad severos, bloqueos durante migraciones y caída total si la instancia administrativa falla.

## Decisión
Dividir formalmente la plataforma en tres planos desacoplados:

1. **Control Plane (SOFIA Central / Platform):**
   - Construido como un **Monolito Modular** en Python + FastAPI.
   - Responsabilidades: Catálogo de productos, gestión de tenants, subdominios y dominios personalizados, suscripciones y licencias, control de capacidad y concurrencia, orquestación de aprovisionamiento, facturación SaaS y auditoría.
   - No almacena datos operativos de las empresas clientes.

2. **Runtime Plane (Instancias de Producto):**
   - Ejecuta los productos comerciales contratados: inicialmente **SOFIA ERP** (Odoo Community), con capacidad futura para *SOFIA Industrial Services*, *SOFIA Quality*, etc.
   - Enrutado a través de Nginx Reverse Proxy.
   - Diseñado para operar de forma autónoma con tokens criptográficos locales en caso de indisponibilidad temporal del Control Plane.

3. **Data Plane (Almacenamiento y Persistencia):**
   - Clusters PostgreSQL aislados para Control Plane y Runtimes.
   - Filestores segmentados en disco con permisos POSIX estrictos o MinIO/S3.
   - Logs estructurados (Loki), métricas (Prometheus) y backups cifrados (WAL-G / pg_dump).

## Consecuencias
### Positivas
- Aislamiento total de seguridad: si un runtime de cliente se compromete, no tiene credenciales ni acceso de red al Control Plane.
- Resiliencia: una caída del Control Plane no detiene la operación diaria de los ERP de los clientes.
- Independencia tecnológica: el Control Plane evoluciona independientemente del core de Odoo.

### Negativas / Mitigaciones
- Mayor disciplina en el despliegue de infraestructura y redes internas virtuales (Docker networks aisladas).
- Necesidad de replicar metadatos esenciales en tokens JWT firmados (JWKS) para evitar consultas síncronas bloqueantes hacia el Control Plane.
