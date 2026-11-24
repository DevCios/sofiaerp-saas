# ADR-007: Sistema de Diseño Unificado e Identidad Visual SaaS de SOFIA ERP

## Estado
Aceptado

## Contexto
El portal público y sitio web corporativo de SOFIA ERP (`sofiaerp.com`) integra múltiples vistas: página de inicio (Hero y Bento Hub), planes y precios (`/precios`), catálogo de verticales (`/verticales`), mesa de ayuda (`/soporte`) y libro de reclamaciones (`/libro-de-reclamaciones`).

Inicialmente, diversas páginas utilizaban estilos fragmentados o badges de colores dispares (como amarillo `#FBBF24` o subrayados cian `#06B6D4`). Se requiere consolidar y replicar la identidad visual oficial, limpia, de alto contraste y estilo SaaS contemporáneo que fue aprobada en la vista principal:
1. **Lienzo Limpio y Minimalista:** Fondo blanco puro (`#FFFFFF`) y secciones secundarias en gris pizarra sutil (`#F8FAFC`).
2. **Titular Heroico de Alto Impacto:** Tipografía sans-serif geométrica en negro/azul profundo (`#0F172A`) con `clamp()` responsive.
3. **Píldora Distintiva de Marca (Badge Púrpura):** Resaltador en púrpura SOFIA ERP (`#7D1A6A`) con texto blanco negrita, bordes completamente redondeados (`border-radius: 9999px`) y sombra sutil con elevación.
4. **Subtítulo Amigable y de Alta Legibilidad:** Frase contextual empática en gris azulado (`#475569`, peso 600).
5. **Botones de Conversión Duales (CTAs):**
   - **Primario:** Púrpura sólido (`#7D1A6A`, hover `#631454`), bordes redondeados (`12px` o `9999px`), sombra profunda.
   - **Secundario:** Fondo blanco con borde púrpura de 1.5px (`#7D1A6A`), texto oscuro (`#0F172A`), hover lavanda sutil (`#FAF5FF`).
6. **Franja de Confianza / Beneficios (Benefits Strip):** Fila horizontal con iconos SVG delgados en color púrpura corporativo (`#7D1A6A`) y divisores verticales sutiles (`#E2E8F0`).
7. **Arquitectura de Tarjetas Bento / Cards:** Bordes limpios de 1px en `#E2E8F0`, esquinas redondeadas (`16px`), micro-sombras, tarjetas destacadas con acento púrpura y chips de métricas operativas.

## Decisión
1. **Consolidación en `theme.scss`:**
   Declarar las variables globales CSS (`:root`) y los componentes estándar (`.hero-badge-purple`, `.sofia-btn-primary`, `.sofia-btn-secondary`, `.sofia-page-hero`, `.sofia-page-title`, `.sofia-page-subtitle`, `.hero-benefits-strip`, `.sofia-card`, `.sofia-card-featured`) en el paquete `web.assets_frontend` de Odoo 20.
2. **Replicación en todas las Plantillas Web:**
   Actualizar de forma uniforme `pricing_page.xml`, `verticales_page.xml`, `support_page.xml`, `libro_reclamaciones_page.xml` y `snippets.xml`, reemplazando cualquier badge amarillo o estilo legacy por la nueva gramática visual.
3. **Mantenimiento de la Coherencia:**
   Toda nueva página, vertical o módulo web que se desarrolle en SOFIA ERP deberá ajustarse obligatoriamente a este sistema de diseño.

## Consecuencias
- **Positivas:**
  - Experiencia de usuario (UX) homogénea, profesional y de nivel corporativo en todas las rutas.
  - Mayor tasa de conversión y claridad de lectura al guiar la atención con la píldora púrpura y botones estandarizados.
  - Facilidad de mantenimiento: los cambios en estilos globales se propagan automáticamente vía SCSS.
- **Negativas / Mitigaciones:**
  - Requiere recompilar assets o actualizar la vista del tema (`odoo -u sofia_website_theme`) en el VPS para que los clientes vean los cambios inmediatamente.
