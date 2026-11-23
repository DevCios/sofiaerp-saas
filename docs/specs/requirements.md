# Especificación de Requisitos del Sistema: SOFIA ERP

## 1. Requisitos Funcionales (RF)

### 1.1 Control Plane (SOFIA Platform)
- **RF-01 (Gestión de Tenants):** El sistema debe permitir registrar, consultar, suspender, reactivar y archivar tenants de forma atómica y auditable.
- **RF-02 (Resolución de Tenants y Dominios):** El sistema debe resolver el tenant correspondiente a partir del subdominio de plataforma (`<tenant>.erp.sofiaerp.com`) o dominio personalizado del cliente (`erp.cliente.com`), validando su estado activo.
- **RF-03 (Identidad y OIDC):** Proveedor de identidad centralizado con soporte de OAuth 2.0 / OpenID Connect (Authorization Code Flow con PKCE). Debe permitir autenticación multifactor (MFA vía TOTP y WebAuthn/Passkeys), revocación de sesiones centralizada y emisión de tokens JWT firmados asimétricamente (RS256).
- **RF-04 (Gestión de Usuarios y Roles):** Un usuario podrá pertenecer a múltiples tenants con roles diferenciados. El Control Plane administrará la relación usuario-tenant y las credenciales globales.
- **RF-05 (Catálogo de Productos y Planes):** Catálogo de productos comerciales (*SOFIA ERP*, *SOFIA Industrial Services*, *SOFIA Quality*, *SOFIA Projects*) y planes tarifarios (*Básico*, *Profesional*, *Empresarial*), con gestión de complementos (*add-ons* de suscripción).
- **RF-06 (Entitlements y Capacidades):** Evaluación dinámica de capacidades contratadas (`custom_domain`, `custom_login_branding`, `custom_logo`, `custom_colors`, `white_label`, `multiple_products`, `advanced_support`). La degradación de capacidades no destruirá configuraciones preexistentes.
- **RF-07 (Control de Capacidad y Concurrencia):** Medición en tiempo real de usuarios contratados, usuarios habilitados, sesiones concurrentes activas y almacenamiento ocupado por tenant con operaciones atómicas en Redis para evitar condiciones de carrera.
- **RF-08 (Orquestación de Aprovisionamiento Asíncrono):** Aprovisionamiento automatizado de bases de datos PostgreSQL, directorios de filestore, configuración de Nginx y sembrado inicial de datos mediante tareas encoladas en Celery.
- **RF-09 (Dominios Personalizados y SSL Automatizado):** Registro de dominio de cliente, verificación de propiedad mediante registro DNS TXT (`_sofia-challenge.cliente.com`), validación de CNAME y emisión/renovación automática de certificados TLS mediante ACME/Let's Encrypt.
- **RF-10 (Facturación Comercial SaaS):** Facturación periódica de suscripciones, emisión de estados de cuenta, control de morosidad y cobro automatizado de licencias y capacidades adicionales.
- **RF-11 (Auditoría Central):** Registro inmutable de eventos de seguridad (inicios de sesión, cambios de credenciales, accesos administrativos, exportaciones de datos y modificaciones de planes).

### 1.2 Runtime Plane (SOFIA ERP / Odoo)
- **RF-12 (Aislamiento de Operaciones ERP):** El producto ERP ejecutará la funcionalidad estándar de Odoo Community (Ventas, Compras, Inventario, Facturación, Contactos) garantizando que cada tenant opere exclusivamente contra su base de datos y filestore.
- **RF-13 (Puente de Autenticación OIDC):** Módulo ligero `sofia_auth_bridge` en Odoo que valida los tokens JWT emitidos por SOFIA Central sin requerir conexión síncrona permanente con el Control Plane.
- **RF-14 (Facturación Electrónica SUNAT - Perú):** Emisión, firma digital, empaquetado XML (UBL 2.1), envío al OSE/SUNAT, recepción y parseo de CDR, y generación de representación impresa en PDF con código QR y Hash para facturas, boletas, notas de crédito/débito y guías de remisión.
- **RF-15 (Portabilidad de Datos):** Exportación funcional completa (CSV/XLSX/PDF/XML) accesible para el cliente desde la interfaz y exportación técnica (backup binario PostgreSQL + filestore) gestionada bajo solicitud autorizada.

---

## 2. Requisitos No Funcionales (RNF)

### 2.1 Seguridad y Privacidad
- **RNF-01 (Aislamiento de Datos):** Separación lógica y física absoluta de bases de datos PostgreSQL (Database-per-Tenant) y directorios de filestore por cliente.
- **RNF-02 (Cero Exposición de Docker Socket):** Ningún contenedor accesible por HTTP ni servicio web montará `/var/run/docker.sock`.
- **RNF-03 (Cero Exposición de Servicios de Infraestructura):** PostgreSQL, Redis, Celery y servicios internos residirán en redes Docker internas sin puertos mapeados al exterior (`0.0.0.0`).
- **RNF-04 (Cifrado Integral):** TLS 1.3 obligatorio en tránsito para todas las conexiones públicas. Cifrado AES-256 en reposo para backups y almacenamiento de archivos sensibles.
- **RNF-05 (Protección contra Inyección de Cabeceras):** Filtrado y saneamiento estricto de la cabecera `Host` en Nginx antes del reenvío al runtime, forzando `X-Odoo-dbfilter` verificado.

### 2.2 Disponibilidad, Continuidad y Resiliencia
- **RNF-06 (Autonomía ante Caída de SOFIA Central):** Si el Control Plane experimenta una interrupción, los runtimes de Odoo deben seguir procesando transacciones comerciales y operativas para usuarios con sesiones vigentes mediante validación local con JWKS público en caché.
- **RNF-07 (RPO y RTO por Plan):**
  - *Básico:* RPO <= 24 h | RTO <= 24 h.
  - *Profesional:* RPO <= 4 h | RTO <= 8 h.
  - *Empresarial:* RPO <= 15 min (PITR con archivado continuo WAL) | RTO <= 4 h.

### 2.3 Escalabilidad y Rendimiento
- **RNF-08 (Escala Inicial del MVP):** Soporte garantizado para 10 clientes concurrentes en el despliegue inicial con un consumo de recursos acotado (< 16 GB RAM en un VPS único).
- **RNF-09 (Tiempo de Respuesta):** Tiempo de respuesta de API del Control Plane <= 120 ms en percentil 95 (P95). Tiempo de carga de páginas transaccionales de Odoo <= 1.5 s en P95.
- **RNF-10 (Concurrencia y Pooling):** Implementación obligatoria de `pgbouncer` para evitar agotamiento de descriptores de conexión en PostgreSQL.

### 2.4 Mantenibilidad y Calidad
- **RNF-11 (Arquitectura de Código Abierto):** Stack 100% basado en software libre sin dependencia de licencias de pago para el núcleo operativo.
- **RNF-12 (Trazabilidad y Observabilidad):** Métricas estandarizadas en formato OpenMetrics/Prometheus, logs JSON estructurados agregados en Loki y alertas proactivas vía Alertmanager.
- **RNF-13 (Documentación Integral):** Cobertura de arquitectura documentada con estándar C4 y decisiones técnicas formalizadas mediante ADRs.
