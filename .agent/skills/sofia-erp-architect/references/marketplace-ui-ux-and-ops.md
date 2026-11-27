# Arquitectura UI/UX de eCommerce de Alta Conversión y Operación de Marketplace (Mercado Wanka)

Guía obligatoria para todo diseño frontend y lógica funcional/administrativa del Marketplace **Mercado Wanka** (`tienda.sofiaerp.com` / dominio propio) integrado con **SOFIA ERP** y **`gateway.sofiaerp.com`**.

---

## 1. Estándar UI/UX eCommerce de Nivel Internacional (Mercado Libre / Falabella / Amazon)

### 1.1 Principios Visuales y Mobile-First
- **75%–85% del tráfico eCommerce en Perú es móvil:** Diseñar primero para pantallas de `360px–430px` (tap targets mínimos de `44x44px`, barra de compra sticky en móvil, carruseles con `CSS Scroll Snap` sin librerías pesadas).
- **Jerarquía Visual Clara:**
  - Header sticky blanco sólido (`z-index: 1050`, sombra sutil) con buscador prominente al centro, botón de Categorías, acceso a cuenta y carrito con badge visible.
  - Contraste mínimo **WCAG AA (4.5:1)** en textos, precios y CTAs.
  - Fondo blanco limpio en tarjetas de producto para evitar recortes en fotografías.
- **Arquitectura de Portada de Alta Conversión:**
  1. Hero Banner de alto impacto (máximo 1 mensaje claro + 1 CTA).
  2. Tira de 6 tarjetas de acceso rápido (cuenta, ubicación, envío gratis, más vendidos, favoritos, tiendas oficiales).
  3. Carrusel *Inspirado en lo último que viste* y *Ofertas del Día* (1 destacada + slider lateral).
  4. Grilla de categorías populares y barra de confianza (*Yape/Plin/Mercado Pago*, *Envío rápido*, *Compra Protegida Escrow*).
  5. Footer institucional con enlaces legales y botón oficial **Libro de Reclamaciones (INDECOPI)**.

### 1.2 Tarjeta de Producto y Ficha de Alta Conversión
- **Tarjeta de producto:** Foto limpia `object-fit: contain`, precio anterior tachado + `% OFF`, precio principal en negrita grande (`S/`), cuotas sin interés, nombre truncado a máximo 2 líneas, calificación (`★ 4.9 (24) · +25 vendidos`), vendedor verificado y badge *Envío gratis / FULL*.
- **Ficha de producto:** Galería rápida, reputación de la tienda (medalla Tienda Oficial, % despacho a tiempo), estimador de envío por Ubigeo antes de ir al carrito, botón de compra destacado y reseñas verificadas.
- **Rendimiento (Core Web Vitals):** Apuntar a `LCP < 2.0s`, `CLS < 0.1`, imágenes optimizadas (`WebP` cuando sea posible) y cero scripts bloqueantes inline dentro de XML.

---

## 2. Arquitectura Funcional y Administrativa del Marketplace (Perú)

### 2.1 Modelo Tributario y de Comisiones (Inquebrantable)
- **Responsabilidad de Facturación SUNAT:**
  - Cada **empresa vendedora** (tenant SOFIA ERP) es la única responsable de emitir la **Boleta o Factura Electrónica SUNAT** al comprador final por los productos vendidos.
  - **Mercado Wanka NO factura productos de terceros**; únicamente factura al vendedor su **servicio de intermediación + uso de plataforma**.
- **Fórmula de Comisión (Configurable por categoría y por vendedor):**
  - Base inicial: **`5.0%` sobre el valor total de la venta (`price_total`) + `S/ 0.50` fijo por uso de plataforma por venta**.
  - Cálculo centralizado en `wango_marketplace/services/commission_service.py`.

### 2.2 Flujo Financiero, Pagos y Antifraude (Escrow + KYC)
- **Pagos Mercado Pago (mismo motor SOFIA ERP):**
  - Checkout Pro (`MP_ACCESS_TOKEN`) aceptando Tarjetas, Yape y Plin.
  - Webhook `/shop/mercadopago/webhook` con validación **HMAC-SHA256 (`x-signature`)**, verificación de monto cobrado vs. orden, e **idempotencia estricta** por `payment_id`.
- **Custodia Antifraude (Escrow):**
  - Las liquidaciones (`marketplace.settlement`) incluyen por defecto solo órdenes entregadas (`only_delivered_escrow = True`), reteniendo el dinero hasta confirmar recepción (PIN/QR) para prevenir fraudes y contracargos.
  - Al liquidar, se genera automáticamente la factura `out_invoice` de Mercado Wanka al vendedor **solo por la comisión + cargo de plataforma**.
- **KYC y Auditoría Bancaria:**
  - Validación RUC/DNI contra SUNAT (`sofiaerp_pe_vat`) y registro de Banco + Cuenta + CCI (20 dígitos).
  - Todo cambio de cuenta bancaria/CCI queda registrado de forma inmutable en `mw.bank.audit`.

### 2.3 Integración Hub & Spoke con SOFIA ERP (Zero-Blocking)
- **Habilitación Automática por Plan Pagado:** Todo cliente con plan activo en SOFIA ERP puede activar su tienda desde el Wizard y publicar productos en 1 clic (`sofia_marketplace_connector`). Si el plan se suspende, sus productos se ocultan automáticamente.
- **Patrón Transactional Outbox (`mw.webhook.outbox`):** Al confirmar una compra multi-vendedor, el carrito se divide en sub-órdenes por vendedor y se encola el envío a cada tenant SOFIA ERP en `mw.webhook.outbox` (con reintento automático vía cron y backoff `2m → 10m → 30m → 2h → 6h`) para nunca bloquear el checkout del comprador.
- **Cumplimiento Legal Perú:** Libro de Reclamaciones Virtual (INDECOPI), Términos y Condiciones con rol de intermediario explícito, Política de Privacidad (Ley 29733) y Política de Cambios/Devoluciones.
