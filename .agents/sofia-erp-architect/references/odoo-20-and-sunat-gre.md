# Referencia Técnica: Odoo Community 20, Facturación SUNAT y GRE

## 1. Núcleo Odoo Community 20
- **Base:** Imagen oficial de Docker `odoo:20.0` o build optimizado sobre Python 3.11/3.12.
- **Sin Dependencias de Enterprise:** No utilizar ni llamar APIs de `enterprise-addons`.
- **Addons Comunitarios Clave:**
  - `sofia_auth_bridge`: Puente de autenticación OIDC con soporte offline.
  - `web_responsive`: Adaptación móvil y tablet de la interfaz administrativa.
  - Módulos contables OCA para balances y reportes financieros sin `account_accountant`.

## 2. Facturación Electrónica SUNAT (Perú)
- **Formatos y Estándares:**
  - Estándar XML UBL 2.1 aprobado por SUNAT.
  - Tipos de Comprobantes:
    - `01`: Factura Electrónica.
    - `03`: Boleta de Venta Electrónica.
    - `07`: Nota de Crédito Electrónica.
    - `08`: Nota de Débito Electrónica.
- **Firma Digital y Certificados:**
  - Archivos `.pfx` o `.pem` cargados por tenant en su base de datos aislada con contraseña cifrada con clave AES-256 derivada del secret de la plataforma.
  - Firma del Digest Value y SignatureValue con algoritmo RSA-SHA256.
- **Flujo de Envío y CDR:**
  - Envío SOAP/REST hacia SUNAT u Operador de Servicios Electrónicos (OSE).
  - Almacenamiento obligatorio del ticket, CDR en XML comprimido `.zip` y estados de respuesta (Aceptado, Rechazado, Con Observaciones).
- **Representación Gráfica (PDF):**
  - Generación de Código QR con los 8 campos obligatorios de SUNAT:
    `RUC | TipoDoc | Serie | Correlativo | IGV | Total | Fecha | TipoDocAdquiriente | NumDocAdquiriente | DigestValue`
  - Resumen Hash oficial visible en el pie de página.

## 3. Guías de Remisión Electrónica (GRE)
- **Tipos de GRE Soportados:**
  - `09`: Guía de Remisión Remitente (traslado por cuenta propia o por venta).
  - `31`: Guía de Remisión Transportista (servicio público de transporte de carga).
- **Campos Mandatorios SUNAT (Resoluciones 2022-2026):**
  - Código de motivo de traslado (Venta, Compra, Traslado entre establecimientos, etc.).
  - Modalidad de transporte (01 Transporte Público, 02 Transporte Privado).
  - Datos de vehículos (Placas) y conductores (Licencias de conducir, DNI).
  - Pesos brutos totales y unidades de medida (KGM, TNE).
  - Generación y consulta mediante API REST oficial de SUNAT para GRE.
