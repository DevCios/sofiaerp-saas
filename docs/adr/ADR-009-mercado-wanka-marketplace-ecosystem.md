# ADR-009: Ecosistema Marketplace "Mercado Wanka" (`addons_mw`) en Odoo 20

- **Estado:** Aprobado
- **Fecha:** 2026-11-26
- **Autor:** Equipo de Arquitectura SOFIA ERP
- **Dominio Inicial:** `https://tienda.sofiaerp.com` (portable a dominio propio por configuración)
- **Base de Datos Hub:** `sofia_tenant_tienda`
- **Ruta de Módulos:** `products/sofia-erp/addons_mw/` (montado en `/mnt/products/sofia-erp/addons_mw`)

---

## 1. Contexto y Reglas de Negocio

SOFIA ERP incorpora el Marketplace multi-vendedor **Mercado Wanka**, migrado desde los módulos de desarrollo propios de Odoo 15 (`wango_core`, `wango_delivery`, `wango_marketplace`, `wango_theme`, `wango_store`) hacia **Odoo Community 20**, bajo un esquema **Hub & Spoke** que preserva el aislamiento `database-per-tenant`:

1. **Responsabilidad Tributaria (SUNAT):**
   - Cada **empresa vendedora** (tenant en SOFIA ERP) es responsable de emitir la Boleta/Factura Electrónica al comprador final por los productos vendidos.
   - **Mercado Wanka NO factura los productos del vendedor**; únicamente cobra y factura al vendedor su **comisión por intermediación + cargo fijo por uso de plataforma**.
   - Fórmula inicial configurable (variable por categoría/vendedor): **`5.0% del precio total de venta + S/ 0.50 fijo por uso de plataforma`**.
2. **Habilitación Automática por Plan Pagado:**
   - Todo cliente con **cualquier plan activo pagado** en SOFIA ERP queda habilitado para activar su tienda en Mercado Wanka desde el Wizard y publicar productos en 1 clic.
   - Si la suscripción se suspende, sus productos se ocultan automáticamente del catálogo público sin perder datos.
3. **Acceso Unificado (SSO):**
   - `sofia_tenant_tienda` usa `sofia_auth_bridge` + OIDC / JWT RS256 del Control Plane para compartir accesos y credenciales con SOFIA ERP.
4. **Pasarela de Pagos Reutilizada:**
   - Reutiliza el mismo motor **Mercado Pago Checkout Pro** (`MP_ACCESS_TOKEN`, `api.mercadopago.com/checkout/preferences`) de SOFIA ERP + Yape/Plin/Transferencia.

---

## 2. Arquitectura de Módulos

- **`products/sofia-erp/addons_mw/`** (instalados en `sofia_tenant_tienda`):
  - `wango_core`: Infraestructura base, agencias/ubicaciones, trazabilidad y configuración Mercado Wanka.
  - `wango_delivery`: Retiro en tienda (mapa Leaflet), delivery por Ubigeo Perú y envío por agencia.
  - `wango_marketplace`: Multi-vendedor, división de carrito, comisiones variables (`5% + S/ 0.50`), facturación solo de comisión al vendedor, liquidaciones, libro de reclamaciones y **API Interna Hub (`/api/marketplace/v1/*`)**.
  - `wango_theme`: Header estilo Falabella, mega-menú y design system Mercado Wanka.
  - `wango_store`: Portada estilo Mercado Libre (Hero, 6 tarjetas, Ofertas del Día, Categorías, Barra de Confianza, Reseñas) + Checkout Mercado Pago integrado.
- **`products/sofia-erp/addons/sofia_marketplace_connector/`** (instalado en los tenants SOFIA ERP):
  - Integración en el **Wizard** de empresa para crear la tienda en Mercado Wanka en 1 clic.
  - Botón **Publicado en Marketplace** (1 clic) en `product.template` con sincronización de precio, imagen y stock.
  - Receptor seguro de sub-órdenes pagadas para despacho y emisión de Boleta/Factura SUNAT desde el ERP del vendedor.
