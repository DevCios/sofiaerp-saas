# Modelos de Arquitectura C4 y Flujos Dinámicos: SOFIA ERP

## 1. Nivel 1: Diagrama de Contexto del Sistema (System Context)

El diagrama de contexto ilustra cómo los distintos actores interactúan con la plataforma SOFIA ERP y sus sistemas externos asociados.

```mermaid
flowchart TD
    subgraph Actores["Actores del Sistema"]
        AdminSaaS["Administrador SOFIA Platform\n(Operador SaaS / Soporte)"]
        AdminTenant["Administrador de Empresa / Tenant\n(Cliente Comercial)"]
        UserOp["Usuario Operativo del Tenant\n(Ventas, Almacén, Facturación)"]
        ClientEnd["Cliente Final / Tercero\n(Portal Proveedor / Consulta)"]
    end

    subgraph SofiaSystem["SOFIA ERP Ecosystem"]
        SofiaPlatform["SOFIA Platform & ERP Core\n(Plataforma SaaS Multiproducto)"]
    end

    subgraph SistemasExternos["Sistemas y Servicios Externos"]
        SUNAT["SUNAT / OSE (Perú)\n(Facturación Electrónica / Validador)"]
        DNSProvider["Servidores DNS Públicos\n(Verificación TXT / CNAME)"]
        LetsEncrypt["Let's Encrypt / ACME CA\n(Emisión Certificados TLS)"]
        SMTPGateway["Servidor SMTP Transaccional\n(Envío Notificaciones / Invitaciones)"]
        ExternalStorage["Almacenamiento S3 / MinIO Externo\n(Backups Cifrados y Réplicas)"]
    end

    AdminSaaS -->|Gestiona Tenants, Planes, Infraestructura| SofiaPlatform
    AdminTenant -->|Administra Usuarios, Suscripción, Branding| SofiaPlatform
    UserOp -->|Ejecuta Operaciones ERP y Facturación| SofiaPlatform
    ClientEnd -->|Consulta Estados de Cuenta / Documentos| SofiaPlatform

    SofiaPlatform -->|Envío de XML y Recepción de CDR| SUNAT
    SofiaPlatform -->|Validación de Dominios Personalizados| DNSProvider
    SofiaPlatform -->|Aprovisionamiento Automatizado de SSL| LetsEncrypt
    SofiaPlatform -->|Notificaciones por Correo| SMTPGateway
    SofiaPlatform -->|Respaldo Diario y WAL Archiving| ExternalStorage
```

---

## 2. Nivel 2: Diagrama de Contenedores (Container Diagram)

Muestra los límites técnicos, tecnologías seleccionadas y protocolos de comunicación entre contenedores.

```mermaid
flowchart TB
    subgraph Edge["Perímetro de Seguridad (Nginx Ingress / Reverse Proxy)"]
        Nginx["Nginx Reverse Proxy & SSL Terminator\n(Lua / Dynamic Map / Certbot ACME)\nPuertos 80, 443"]
    end

    subgraph ControlPlaneContainer["Control Plane — SOFIA Platform (Monolito Modular)"]
        CP_API["FastAPI Application Server\n(Python 3.11, Uvicorn, Pydantic v2)\n• Tenant Resolver\n• Identity & OIDC\n• Catalog & Billing\n• Capacity Metering"]
        CP_Worker["Celery Background Worker\n(Python 3.11)\n• Tenant Provisioning\n• SSL Generation Task\n• Backup Orchestration"]
        CP_Beat["Celery Beat Scheduler\n• Subscription Renewals\n• Metrics Aggregation"]
    end

    subgraph RuntimePlaneContainer["Runtime Plane — SOFIA ERP (Odoo Runtimes)"]
        OdooShared["Odoo Community 18/20 Container Pool\n(Python 3.11, Werkzeug, Gevent/Workers)\n• Módulo sofia_auth_bridge\n• Módulo l10n_pe_edi_sunat\n• Addons de Negocio"]
        OdooDedicated["Dedicated Odoo Container\n(Para Clientes Enterprise)"]
    end

    subgraph DataPlaneContainer["Data Plane (Persistencia y Caché)"]
        PgBouncer["PgBouncer Connection Pooler\n(Gestión Eficiente de Descriptores)"]
        PostgresCentral[(PostgreSQL Central Database\nTenants, Subscriptions, Users, Audits)]
        PostgresTenants[(PostgreSQL Tenant Databases Cluster\nsofia_tenant_uuid1, sofia_tenant_uuid2)]
        RedisCache[(Redis In-Memory Data Store\nBroker Celery, Rate Limiting, Concurrencia)]
        FileStoreVolume["Volúmenes Locales Aislados\n/var/lib/sofia/filestores/tenant_id"]
    end

    %% Flujos de Red
    Nginx -->|Proxy HTTP :8000 /api, /auth, /admin| CP_API
    Nginx -->|Proxy HTTP :8069 con cabecera X-Odoo-dbfilter| OdooShared
    Nginx -->|Proxy HTTP :8069 (Ruta Dedicada)| OdooDedicated

    CP_API -->|Lectura / Escritura de Esquema Central| PostgresCentral
    CP_API -->|Caché de Sesiones y Locks Atómicos| RedisCache
    CP_API -->|Encola Tareas de Aprovisionamiento| RedisCache

    CP_Worker -->|Lee Tareas| RedisCache
    CP_Worker -->|DDL: CREATE DATABASE tenant_id| PostgresTenants
    CP_Worker -->|Crea directorios con permisos estrictos| FileStoreVolume

    OdooShared -->|Consultas SQL vía Pooler| PgBouncer
    OdooDedicated -->|Consultas SQL vía Pooler| PgBouncer
    PgBouncer --> PostgresTenants
    OdooShared -->|Lectura y Escritura de Adjuntos| FileStoreVolume
```

---

## 3. Nivel 3: Diagrama de Componentes del Control Plane (Component Diagram)

Detalla la arquitectura modular interna de la aplicación FastAPI.

```mermaid
flowchart TD
    subgraph FastAPI_App["SOFIA Platform Core (FastAPI Application)"]
        Router["API Gateway / Routing Layer\n(FastAPI APIRouter)"]

        subgraph Modules["Módulos de Negocio Desacoplados"]
            TenantMod["Tenant & Domain Manager\n• Tenant CRUD\n• Custom Domain TXT Verifier\n• Subdomain Router"]
            AuthMod["Identity & Auth Manager (OIDC)\n• PKCE Verifier\n• JWT/JWKS Signer (RS256)\n• MFA Engine (TOTP/WebAuthn)"]
            CatalogMod["Product & Licensing Manager\n• Product Catalog\n• Subscription State Machine\n• Entitlement Evaluator"]
            CapacityMod["Capacity & Concurrency Meter\n• Active Sessions Tracker\n• Storage Quota Inspector\n• Atomic Concurrency Lock"]
            ProvMod["Provisioning Orchestrator\n• Task Dispatcher\n• Health Prober\n• Tenant Lifecycle Controller"]
            AuditMod["Security & Audit Logger\n• Immutable Audit Event Stream\n• Tamper-proof Log Signing"]
        end

        subgraph CoreInfra["Infraestructura y Persistencia"]
            SQLAlchemyCore["SQLAlchemy 2.0 ORM & Session Manager"]
            RedisClient["Async Redis Client (aioredis)"]
            CeleryClient["Celery Dispatcher Client"]
        end
    end

    Router --> TenantMod
    Router --> AuthMod
    Router --> CatalogMod
    Router --> CapacityMod
    Router --> ProvMod
    Router --> AuditMod

    TenantMod --> SQLAlchemyCore
    AuthMod --> SQLAlchemyCore
    AuthMod --> RedisClient
    CatalogMod --> SQLAlchemyCore
    CapacityMod --> RedisClient
    ProvMod --> CeleryClient
    AuditMod --> SQLAlchemyCore
```

---

## 4. Flujos de Secuencia Críticos

### 4.1 Flujo 1: Resolución Dinámica de Dominio y Tenant (Domain & Tenant Resolution)

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Navegador Web
    participant Nginx as Edge Nginx
    participant Resolver as Tenant Resolver (FastAPI / Redis)
    participant Odoo as Runtime Odoo

    Cliente->>Nginx: GET https://erp.empresa.com/web
    Nginx->>Resolver: Consulta mapeo interno (Host: erp.empresa.com)
    alt Dominio no reconocido o suspendido
        Resolver-->>Nginx: Status 404 Not Found o 423 Locked
        Nginx-->>Cliente: Retorna página de error corporativo SOFIA
    else Dominio verificado y activo
        Resolver-->>Nginx: tenant_uuid: "abc-123", status: "ACTIVE", pool: "shared-01"
        Nginx->>Nginx: Inyecta cabecera X-Odoo-dbfilter: ^sofia_tenant_abc_123$
        Nginx->>Odoo: Reenvía petición a upstream Odoo con cabeceras sanitizadas
        Odoo->>Odoo: Conecta a DB sofia_tenant_abc_123
        Odoo-->>Nginx: Respuesta HTML/JSON del ERP
        Nginx-->>Cliente: Entrega página al usuario
    end
```

### 4.2 Flujo 2: Aprovisionamiento Automatizado y Asíncrono de un Nuevo Tenant

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin SOFIA
    participant API as Control Plane API
    participant DB_Central as DB Central
    participant Redis as Redis Queue
    participant Worker as Celery Worker
    participant Postgres as PostgreSQL Server
    participant Storage as Filestore Disk

    Admin->>API: POST /api/v1/tenants (Crear tenant "Minera Andina")
    API->>DB_Central: Inserta registro Tenant (Estado: PROVISIONING)
    API->>Redis: Encola tarea: tasks.provision_tenant(tenant_id)
    API-->>Admin: Retorna HTTP 202 Accepted {id: tenant_id, status: "PROVISIONING"}

    Worker->>Redis: Toma tarea de aprovisionamiento
    Worker->>Postgres: Ejecuta: CREATE DATABASE sofia_tenant_minera;
    Worker->>Worker: Inicializa esquema base seguro (odoo -i base --no-http)
    Worker->>Storage: Crea directorio /var/lib/sofia/filestores/tenant_minera/
    Worker->>Storage: Aplica chown/chmod estrictos (usuario odoo:odoo 0750)
    Worker->>DB_Central: Actualiza estado: ACTIVE, provisioned_at: NOW()
    Worker->>Redis: Publica evento WebSocket / Notificación de éxito
    Admin->>API: Consulta GET /api/v1/tenants/{tenant_id} -> Estado: ACTIVE
```
