# Guía Maestra de Despliegue y Puesta en Producción: SOFIA ERP

Este manual detalla los procedimientos estandarizados para desplegar la plataforma **SOFIA ERP** tanto en entornos de desarrollo/staging local como en el servidor de producción (VPS Hardened) para los primeros 10 clientes comerciales del MVP.

---

## 1. Requisitos Previos del Servidor de Producción

Conforme a la especificación de dimensionamiento aprobada en [05-infrastructure-sizing-mvp.md](file:///c:/Users/dev/Documents/DevCios/sofiaerp/docs/architecture/05-infrastructure-sizing-mvp.md):

- **Hardware Recomendado:** 1 VPS Cloud o Servidor Dedicado:
  - **CPU:** 8 vCPU (AMD EPYC o Intel Xeon > 2.8 GHz).
  - **Memoria RAM:** 32 GB RAM (mínimo 16 GB con swap de 8 GB).
  - **Disco:** 250 GB a 500 GB SSD NVMe en RAID 1.
  - **Sistema Operativo:** Ubuntu Server 24.04 LTS o Debian 12.
- **Herramientas Obligatorias:**
  - Docker Engine >= 26.0 y Docker Compose Plugin >= 2.27.
  - Git >= 2.40.
  - OpenSSL, GPG y `rclone` (para respaldos en Google Drive).
  - Certbot o plugin ACME para Nginx.
- **Dominio y DNS:**
  - Registros DNS configurados en el registrador apuntando a la IP pública del servidor:
    - `A api.sofiaerp.com -> <IP_SERVIDOR>`
    - `A auth.sofiaerp.com -> <IP_SERVIDOR>`
    - `A app.sofiaerp.com -> <IP_SERVIDOR>`
    - `A admin.sofiaerp.com -> <IP_SERVIDOR>`
    - `A erp.sofiaerp.com -> <IP_SERVIDOR>`
    - `CNAME *.erp.sofiaerp.com -> erp.sofiaerp.com`

---

## 2. Paso a Paso: Despliegue en Producción (Linux VPS)

### Paso 1: Hardening Inicial del Servidor y Firewall (UFW)
Asegurar que únicamente los puertos web (80 y 443) y el puerto de administración SSH estén accesibles al exterior. **Ningún puerto de datos (5432, 6432, 6379) debe abrirse a Internet.**

```bash
# 1. Actualizar repositorios del sistema
sudo apt update && sudo apt upgrade -y

# 2. Configurar Firewall UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH Administrativo'
sudo ufw allow 80/tcp comment 'HTTP Nginx'
sudo ufw allow 443/tcp comment 'HTTPS TLS Nginx'
sudo ufw enable
```

---

### Paso 2: Clonar el Repositorio e Inicializar Estructura
```bash
# Clonar código en el directorio corporativo
sudo mkdir -p /opt/sofiaerp
sudo chown -R $USER:$USER /opt/sofiaerp
cd /opt/sofiaerp

git clone <URL_DEL_REPOSITORIO> .
```

---

### Paso 3: Generación del Par de Claves Asimétricas RSA (JWKS OIDC)
El sistema utiliza criptografía asimétrica **RS256** para que los runtimes de Odoo validen tokens JWT localmente sin consultar síncronamente al Control Plane (ADR-004).

```bash
# Crear directorio de claves con permisos estrictos
mkdir -p control-plane/keys
chmod 700 control-plane/keys

# 1. Generar Clave Privada RSA de 4096 bits
openssl genpkey -algorithm RSA -out control-plane/keys/jwt_private.pem -pkeyopt rsa_keygen_bits:4096

# 2. Extraer Clave Pública correspondiente
openssl rsa -pubout -in control-plane/keys/jwt_private.pem -out control-plane/keys/jwt_public.pem

# Asegurar permisos de lectura restringidos
chmod 600 control-plane/keys/jwt_private.pem
chmod 644 control-plane/keys/jwt_public.pem
```

---

### Paso 4: Configuración de Variables de Entorno (`.env`)
Copiar la plantilla [.env.example](file:///c:/Users/dev/Documents/DevCios/sofiaerp/.env.example) hacia `.env` y generar contraseñas criptográficas seguras:

```bash
cp .env.example infrastructure/docker/.env
cd infrastructure/docker

# Generar contraseñas aleatorias únicas para cada servicio
POSTGRES_PASS=$(openssl rand -hex 24)
REDIS_PASS=$(openssl rand -hex 24)
ODOO_PASS=$(openssl rand -hex 24)
APP_SECRET=$(openssl rand -hex 32)

# Configurar valores en el archivo .env
sed -i "s/generate_secure_password_min_24_chars/$POSTGRES_PASS/g" .env
sed -i "s/generate_secure_redis_auth_token/$REDIS_PASS/g" .env
sed -i "s/generate_secure_odoo_db_password/$ODOO_PASS/g" .env
sed -i "s/generate_with_openssl_rand_hex_32_change_in_production/$APP_SECRET/g" .env
```

---

### Paso 5: Configuración de Google Drive con `rclone` (ADR-006)
Para habilitar el resguardo automático de backups cifrados en Google Drive:

```bash
# 1. Crear directorio de configuración de rclone
mkdir -p backups
chmod 700 backups

# 2. Ejecutar asistente de configuración de rclone para vincular Google Drive
rclone config
# Seleccionar: New remote -> Nombre: 'gdrive' -> Tipo: 'drive'
# Seguir el asistente para vincular la cuenta Google Workspace o Service Account.

# 3. Mover el archivo generado a la ruta del proyecto
cp ~/.config/rclone/rclone.conf backups/rclone.conf
chmod 600 backups/rclone.conf
```

---

### Paso 6: Construcción y Levantamiento de Contenedores
```bash
# Construir imágenes de Control Plane y levantar todos los servicios en segundo plano
docker compose up -d --build

# Verificar que los 6 contenedores estén levantados y saludables
docker compose ps
```

Deberás observar los siguientes contenedores activos:
- `sofia-edge-router` (Nginx - Puertos 80, 443)
- `sofia-control-plane-api` (FastAPI - Red interna)
- `sofia-control-plane-worker` (Celery - Red interna)
- `sofia-pgbouncer` (PgBouncer - Red interna)
- `sofia-postgres` (PostgreSQL 16 - Red interna)
- `sofia-redis` (Redis 7 - Red interna)
- `sofia-odoo-runtime-shared` (Odoo 20 Community - Red interna)

---

### Paso 7: Verificación de Salud del Sistema
Ejecuta la comprobación del endpoint de diagnóstico:

```bash
# Comprobación de salud interna
curl -I http://localhost/api/v1/health

# Respuesta esperada:
# HTTP/1.1 200 OK
# {"status":"online","components":{"api":"healthy","database":"healthy"}}
```

---

## 3. Aprovisionamiento del Primer Tenant Comercial (Ejemplo Práctico)

Una vez desplegada la plataforma, el aprovisionamiento de un nuevo cliente se ejecuta de manera automatizada mediante una única llamada a la API:

```bash
curl -X POST http://api.sofiaerp.com/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Minera Andina de Exploraciones S.A.C.",
    "slug": "minera-andina",
    "runtime_mode": "SHARED_PROTECTED",
    "admin_email": "gerencia@mineraandina.com",
    "admin_password": "TemporalPassword2026#",
    "plan_code": "SOFIA-ERP-PRO"
  }'
```

### ¿Qué ocurre internamente en segundos?
1. El **Control Plane** inserta el registro del tenant con estado `PROVISIONING`.
2. El **Celery Worker** recibe la tarea:
   - Conecta a PostgreSQL y ejecuta `CREATE DATABASE sofia_tenant_minera_andina OWNER odoo_runtime_user;`.
   - Limita las conexiones máximas (`CONNECTION LIMIT 30`).
   - Crea el directorio físico `/var/lib/sofia/filestores/minera-andina` con permisos `0750`.
   - Inicializa el esquema Odoo 20 con los módulos `base` y `sofia_auth_bridge`.
3. El estado del tenant cambia automáticamente a `ACTIVE`.
4. El cliente ya puede acceder a su ERP en:
   `https://minera-andina.erp.sofiaerp.com`

---

## 4. Despliegue Rápido en Entorno Local (Desarrollo / Testing)

Si deseas probar todo el stack localmente en tu estación de trabajo:

```bash
# 1. Situarse en el directorio de infraestructura
cd infrastructure/docker

# 2. Copiar variables de entorno
cp ../../.env.example .env

# 3. Crear claves JWT de prueba
mkdir -p ../../control-plane/keys
openssl genpkey -algorithm RSA -out ../../control-plane/keys/jwt_private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in ../../control-plane/keys/jwt_private.pem -out ../../control-plane/keys/jwt_public.pem

# 4. Iniciar con Docker Compose
docker compose up -d --build
```
Acceso a servicios en local:
- **API & Docs Swagger:** `http://localhost/api/docs`
- **Métricas Prometheus:** `http://localhost/api/v1/metrics`
- **Health Check:** `http://localhost/api/v1/health`
