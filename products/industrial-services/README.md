# SOFIA Industrial Services — Arquitectura de Producto

## 1. Misión del Producto
**SOFIA Industrial Services** es una suite empresarial de Gestión de Mantenimiento de Activos (CMMS / EAM) y Gestión de Servicios de Campo (Field Service Management - FSM), diseñada para plantas industriales, empresas de ingeniería, flotas y servicios técnicos especializados.

Inspirado en los estándares operativos de clase mundial de IBM Maximo, SAP S/4HANA Asset Management, IFS Cloud y ServiceNow FSM.

## 2. Mapa de Capacidades Funcionales (10 Dominios de Negocio)
1. **Gestión Comercial de Servicios:** Catálogo técnico de prestaciones, tarifas horarias, contratos marco y SLAs.
2. **Solicitudes & Triage (Helpdesk Industrial):** Captura de fallas, severidad y conversión en órdenes de trabajo.
3. **Órdenes de Trabajo (Field Service):** Alcance, WBS de tareas, cuadrillas asignadas y programación táctica.
4. **Mantenimiento Industrial (CMMS/EAM):** Estrategias preventiva, correctiva, predictiva y taxonomía de fallas **ISO 14224**.
5. **Jerarquía de Activos & Equipos:** Árbol de activos por planta/sistema, criticidad ABC y métricas **MTBF / MTTR**.
6. **Recursos Humanos & Cuadrillas:** Técnicos, certificaciones de seguridad (soldadura, eléctrica, altura) y horas-hombre.
7. **Logística de Repuestos:** BOM de mantenimiento, kits de repuestos y gestión de stock de furgón (*Van Stock*).
8. **Costos & Rentabilidad Analítica:** Costeo en tiempo real de mano de obra, materiales y margen bruto por orden.
9. **Gestión Documental & Evidencias:** Protocolos de calibración, fotos antes/después y firma digital de conformidad en sitio.
10. **Seguridad y Calidad (HSE):** Análisis de Trabajo Seguro (ATS) y Permisos de Trabajo de Alto Riesgo (LOTO, Espacios Confinados).

## 3. Arquitectura y Comunicación con SOFIA Central
- **Identidad:** Integra el módulo `sofia_auth_bridge` para SSO mediante OIDC con validación offline.
- **Aislamiento:** Comparte la base de datos del tenant o utiliza esquema propio con contratos API versionados vía `TenantContext`.
- **Frontend / UX:** Vistas de alta densidad operativa (Kanban táctico, Searchpanel y reducción de clics).
