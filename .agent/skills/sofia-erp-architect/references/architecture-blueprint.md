# Referencia Técnica: Blueprint de Arquitectura y Separación de Planos

## 1. Tres Planos Desacoplados

### 1.1 Control Plane (SOFIA Platform)
- **Tecnología:** Python 3.11, FastAPI asíncrono, SQLAlchemy 2.0, Pydantic v2, Celery 5.
- **Responsabilidad:** Registro central de clientes, aprovisionamiento automatizado, emisión de identidad OIDC, catálogo comercial, facturación SaaS de suscripciones, control de cuotas y auditoría.
- **Persistencia:** Base de datos relacional PostgreSQL exclusiva (`sofia_central_db`). No almacena datos transaccionales de las empresas de los clientes.

### 1.2 Runtime Plane (SOFIA ERP & Productos Futuros)
- **Tecnología:** Odoo Community 20, Nginx 1.27, Python 3.11/Werkzeug.
- **Responsabilidad:** Ejecución de los procesos de negocio de cada empresa (Ventas, Facturación, Inventarios, Compras, Contabilidad, Guías de Remisión).
- **Modos de Ejecución:**
  - *Shared Protected:* Pool de workers compartidos enrutados mediante cabeceras dinámicas `X-Odoo-dbfilter` para tenants en planes Básico y Profesional.
  - *Dedicated Runtime:* Contenedor Odoo dedicado exclusivamente al tenant en plan Empresarial.

### 1.3 Data Plane (Persistencia Aislada)
- **PostgreSQL 16 Multi-Database:** Un esquema relacional independiente por tenant (`sofia_tenant_<slug>`).
- **Connection Pooler (PgBouncer):** Delante de PostgreSQL en modo `transaction` para mitigar el agotamiento de descriptores de conexión.
- **Filestores Aislados:** Rutas físicas `/var/lib/sofia/filestores/<slug>/` con permisos POSIX restringidos (0750) impidiendo el acceso cruzado entre clientes.

---

## 2. Topología de Redes en Docker

```text
[ Internet Pública ]
       │
   (Puertos 80, 443)
       ▼
┌──────────────────────────────────────────────┐
│ sofia-net-public (DMZ)                       │
│  - sofia-edge-router (Nginx)                 │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ sofia-net-app (Red de Aplicaciones Interna)  │
│  - sofia-control-plane-api (FastAPI :8000)   │
│  - sofia-odoo-runtime-shared (Odoo :8069)    │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ sofia-net-data (Red de Datos Aislada)        │
│  - sofia-pgbouncer (:6432)                   │
│  - sofia-postgres (:5432 - Sin puerto host)  │
│  - sofia-redis (:6379 - Sin puerto host)     │
│  - sofia-control-plane-worker (Celery)       │
└──────────────────────────────────────────────┘
```
