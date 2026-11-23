# ADR-003: Núcleo Odoo Community 20 y Módulos de Facturación Electrónica SUNAT y GRE

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Autores:** Especialista Senior Odoo Community & Product Manager

## Contexto y Actualización
En el análisis preliminar de Fase 0 se identificó el riesgo de inmadurez de módulos de localización fiscal para Odoo 20. 
El equipo del proyecto ha confirmado y validado la **disponibilidad completa del módulo especializado de Facturación Electrónica y Guías de Remisión Electrónica (GRE) para Odoo Community 20**.

## Decisión
1. **Fijación de Núcleo:** Se establece **Odoo Community 20** como la versión troncal estándar para el producto **SOFIA ERP** en el MVP comercial de 10 clientes.
2. **Alcance Tributario Completo:** El módulo integrado soportará:
   - Facturas Electrónicas (01)
   - Boletas de Venta Electrónicas (03)
   - Notas de Crédito (07) y Notas de Débito (08)
   - Guías de Remisión Electrónica Remitente (09) y Transportista (31)
   - Generación de XML conforme a estándar UBL 2.1 de SUNAT.
   - Firma digital electrónica mediante certificado digital del cliente (`.pfx` / `.pem` cifrado en base de datos).
   - Envío asíncrono y síncrono al OSE o SUNAT, recepción, parseo y almacenamiento de CDR (Constancia de Recepción).
   - Representación impresa en PDF con código QR y resumen Hash oficial.
3. **Persistencia del Desacoplamiento:** Aunque el MVP utilizará Odoo 20, la API de aprovisionamiento del Control Plane mantendrá la abstracción para admitir múltiples runtimes en el futuro sin reescribir la plataforma.

## Consecuencias
- Mitigación absoluta del riesgo de madurez tributaria en Odoo 20.
- Cumplimiento integral de las resoluciones de superintendencia vigentes de SUNAT para emisión electrónica obligatoria en Perú.
- Cobertura completa de operaciones de despacho y logística mediante GRE.
