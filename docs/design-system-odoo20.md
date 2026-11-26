# Sistema de Diseño Oficial SOFIA ERP (Base Referencial Odoo 20)

Todos los desarrollos frontend de **sofiaerp.com** (`SOFIA Platform`, `Sofia Gateway`, sitio web corporativo, portal cliente y vistas web en Odoo 20) deben seguir estrictamente esta guía de diseño para garantizar coherencia visual, seriedad empresarial y una transición transparente con **Odoo 20**.

---

## 1. Paleta de Colores Oficial (Tokens CSS)

```css
:root {
  /* Marca Principal (Odoo 20 Signature Purple) */
  --o20-navbar:        #66598F; /* Barra de navegación superior */
  --o20-navbar-hover:  #554979; /* Hover/activo en barra superior */
  --o20-primary:       #714B67; /* Botones primarios, tabs activos, foco */
  --o20-primary-hover: #5C3B53; /* Hover botón primario */
  --o20-primary-soft:  #EAE6F8; /* Fondo pastel lavanda (KPIs / badges) */

  /* Acento Secundario (Odoo Teal) */
  --o20-teal:          #017E84; /* Enlaces, acciones secundarias, métricas */
  --o20-teal-hover:    #01666B;
  --o20-teal-soft:     #D9F2EE; /* Fondo pastel verde agua (KPIs / éxito) */

  /* Superficies y Bordes (Enterprise Light) */
  --o20-bg:            #F6F7F9; /* Fondo general de aplicación */
  --o20-surface:       #FFFFFF; /* Tarjetas, tablas, barra de control */
  --o20-surface-muted: #F9FAFB; /* Cabeceras de tabla / hover filas */
  --o20-border:        #E2E5EC; /* Bordes finos de 1px */

  /* Tipografía */
  --o20-text:          #1F2937; /* Texto principal (alto contraste) */
  --o20-text-muted:    #6B7280; /* Etiquetas, subtítulos, metadatos */

  /* Estados Semánticos (Pastel Odoo 20) */
  --o20-ok-bg:         #D9F2EE;
  --o20-ok-text:       #0F766E;
  --o20-warn-bg:       #FDE8D7;
  --o20-warn-text:     #B45309;
  --o20-err-bg:        #FDE2E2;
  --o20-err-text:      #B91C1C;
  --o20-info-bg:       #EAE6F8;
  --o20-info-text:     #5B4B8A;
}
```

---

## 2. Arquitectura de Layout Estándar (Odoo 20)

1. **Top Navbar (`#66598F`, altura `48px–54px`):**
   - Izquierda: Logo/nombre del módulo + navegación principal horizontal en texto blanco limpio.
   - Derecha: indicadores de estado (semáforos SUNAT / usuario activo) y botón discreto de salida.
2. **Control Panel Bar (`#FFFFFF`, borde inferior `1px solid #E2E5EC`):**
   - Izquierda: botón de acción primaria (`#714B67`), título de vista y selector de contexto (ej. empresa/RUC).
   - Derecha: filtros rápidos, buscador estilo píldora y botón actualizar.
3. **KPIs Pastel Compactos:**
   - Tarjetas claras con tintes suaves (`#EAE6F8`, `#D9F2EE`, `#FDE8D7`, `#FDE2E2`), número grande en negrita y etiqueta corta en mayúsculas/semi-bold.
4. **Tablas Limpias de Alto Contraste:**
   - Fondo blanco `#FFFFFF`, cabecera `#F9FAFB` con texto `#4B5563` de `12px` semibold, filas con separador `1px solid #EEF0F4` y hover `#F8FAFC`.
5. **Prohibido:**
   - Mezclar temas oscuros genéricos en paneles administrativos de `sofiaerp.com`.
   - Usar colores neón o gradientes estridentes fuera de la paleta Odoo 20.
