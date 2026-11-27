# Estándares de Ingeniería y Migración — Odoo Community 20 (SOFIA ERP)

Reglas técnicas obligatorias y verificadas en producción sobre **Odoo Community 20** (`20.0-20261112`). Todo módulo nuevo o migrado desde versiones anteriores (v15–v18) debe cumplirlas al 100%.

---

## 1. Seguridad y Permisos (`security/`)

1. **`ir.access.csv` (reemplaza a `ir.model.access.csv` y `ir.rule`):**
   - Cabecera obligatoria: `id,name,model_id,group_id/id,operation,domain`
   - Valores válidos en `operation`: **`r`**, **`ru`**, **`cru`**, **`crud`** (`c`=create, `r`=read, `u`=update/write, `d`=delete/unlink). **Prohibido usar `rw`, `rwc` o `rc`.**
   - `model_id` es el nombre técnico del modelo (`sale.order`, `mw.webhook.outbox`), no `model_sale_order`.
2. **Roles y Jerarquía (`res.groups.privilege`):**
   - **Prohibido** usar `category_id` o `users` directamente en `res.groups`.
   - Para mostrar selectores desplegables ordenados en la ficha de Usuario (en lugar de checkboxes técnicos sueltos), crear un `ir.module.category`, un `res.groups.privilege` apuntando a esa categoría, y asignar `privilege_id` a cada `res.groups`.
3. **Menús (`ir.ui.menu`):**
   - El campo se llama **`group_ids`** (no `groups_id`).

---

## 2. Vistas XML y QWeb (`views/`)

1. **Listas, Kanban, Search y Acciones:**
   - Usar `<list>` / `</list>` y `view_mode` con `list` (nunca `<tree>`).
   - Usar expresiones directas `invisible="..."`, `readonly="..."`, `required="..."` (prohibido `attrs=` y `states=`).
   - En `<kanban>`, usar `<t t-name="card">` (nunca `kanban-box`).
   - En `<search>`, `<group>` va limpio sin `expand="0"` ni `string="..."`.
   - En `ir.actions.act_window`, `target` nunca puede ser `inline` (usar `current` o `new`).
   - En `ir.actions.report`, **no** usar `report_file` (solo `report_name`).
2. **Directivas QWeb en Odoo 20:**
   - **Usar siempre `t-out=`** (en Odoo 20 `t-esc=` fue removido y no imprime texto).
   - **Scoping de `t-call`:** declarar `<t t-set="var" t-value="..."/>` **antes** de `<t t-call="..."/>`, nunca dentro del cuerpo de `t-call` si el subtemplate no invoca `<t t-out="0"/>`.
   - **Evitar xpaths frágiles sobre `website_sale`:** `website_sale.cart_summary`, `//h1[@itemprop='name']`, `//a[@id='add_to_cart']`, `//div[hasclass('oe_cart')]` y `//ol[hasclass('breadcrumb')]/..` cambiaron en Odoo 20. Anclar en contenedores estables (`//main` de `website.layout`, `//div[@id='product_details']`, `//div[@id='products_grid']/*[1]`).
   - **Nunca envolver el nodo raíz de un `<xpath>` con `t-if`** al lado de `t-if`/`t-else` hermanos (puede provocar `IndentationError` compilado); envolverlo en un `<div>` neutro.

---

## 3. Modelos ORM y Controladores Python (`models/`, `controllers/`)

1. **`ir.config_parameter`:** `get_param()` y `set_param()` fueron removidos en Odoo 20. Usar siempre ORM:
   ```python
   rec = env['ir.config_parameter'].sudo().search([('key', '=', 'mi.clave')], limit=1)
   val = rec.value if rec else default
   ```
2. **Productos (`product.template`):** `type='product'` ya no existe. Usar **`type='consu'`** con **`is_storable=True`** para productos almacenables (`'service'` para servicios).
3. **Dependencias eliminadas:** `base_vat` y `payment_transfer` ya no existen como módulos separados (usar `account` + `payment`). Si se extiende `check_vat()`, proteger con `hasattr(super(...), 'check_vat')`.
4. **Rutas HTTP / JSON-RPC:**
   - Usar `type='jsonrpc'` (no `type='json'`) y `request.get_json_data()` (no `request.jsonrequest`).
   - Importar `Home` desde `odoo.addons.web.controllers.home` (no `web.controllers.main`).
   - Carrito eCommerce: usar `request.cart` (o el adaptador `website.sale_get_order()` con fallback a `request.cart`).
5. **Parámetros de campo:** No pasar `auto_join=True` ni `widget="..."` en definiciones Python de `fields.*`, ni `tracking=True` en modelos que no hereden `mail.thread`. Usar `@api.model_create_multi` en `create(self, vals_list)`.

---

## 4. Assets Frontend y Fuentes de Íconos

- **No** colocar URLs externas (`https://...`) dentro de `assets` en `__manifest__.py`; cargarlas vía `<link rel="stylesheet"/>` en `<xpath expr="//head" position="inside">`.
- **Prohibido** aplicar `font-family: ... !important` sobre `*`, `span`, `i`, `.fa`, `.oi` o `.material-icons` (rompe FontAwesome, Odoo Icons `.oi` y Material Icons como `keyboard_arrow_right`). Aplicar tipografía en `body` por herencia CSS limpia.
- En cabeceras personalizadas que reemplacen `<header>`, conservar `id="top"`, `class="... o_header_standard"`, y `.o_wsale_my_cart` envolviendo `.my_cart_quantity` para que `CartService` de Odoo 20 funcione sin errores JS.
- Nunca usar `class="oe_login_form"` en modales de login personalizados sin `.oe_login_buttons` (dispara `WebsiteAuthFormWarning`).
