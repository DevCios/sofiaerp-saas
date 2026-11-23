# ADR-005: Aprovisionamiento Seguro sin Exposición del Docker Socket

- **Estado:** Propuesto / Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Ingeniero DevOps & Especialista en Ciberseguridad

## Contexto y Riesgo
El aprovisionamiento de tenants en soluciones SaaS con Docker suele caer en el grave anti-patrón de montar el socket de Docker (`/var/run/docker.sock`) dentro del contenedor de la aplicación web (FastAPI o Odoo).
**Peligro Crítico:** Quien tenga acceso al socket de Docker tiene privilegios equivalentes a `root` en el host de Linux. Si la aplicación web sufre una vulnerabilidad de inyección o ejecución remota de código (RCE), el atacante toma el control absoluto del servidor host y de todos los demás contenedores y bases de datos de otros clientes.
El requerimiento explícitamente ordena: **"No exponer Docker Socket"**.

## Decisión
1. **Desacoplamiento del Aprovisionador:**
   - La API pública del Control Plane (FastAPI) **nunca** tendrá montado `/var/run/docker.sock`.
   - La API recibe la solicitud de creación de tenant, valida licencias/pago, y encola un mensaje firmado en Celery/Redis (`tenant.provision`).
2. **Mecanismo de Ejecución:**
   - Para el modelo *Shared Protected* (MVP 10 clientes), la creación de un nuevo tenant **no requiere crear un nuevo contenedor Docker**. Se ejecuta una tarea en Celery que:
     - Crea la base de datos en PostgreSQL con usuario de aplicación restringido.
     - Inicializa el esquema mediante comando CLI seguro (`odoo -d sofia_tenant_<id> -i base --no-http`).
     - Crea el directorio de filestore en la ruta aislada correspondiente.
     - Notifica a Nginx para actualizar el mapa dinámico de dominios/tenants (mediante archivo de configuración estático verificado o API local restringida).
   - Para el modelo *Dedicated Runtime* (clientes con contenedor dedicado):
     - La orquestación se delega a un agente de aprovisionamiento en el host (Runner aislado fuera del alcance web, o Ansible Controller ejecutado en un entorno de gestión con permisos mínimos), sin exponer el socket al runtime web.

## Consecuencias
- Cumplimiento estricto de la política de seguridad: contención de privilegios y prevención de escalada a root.
- Aprovisionamiento rápido y ligero para los primeros 10 clientes sin sobrecargar el servidor con decenas de contenedores innecesarios.
