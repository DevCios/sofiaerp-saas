# -*- coding: utf-8 -*-
import base64
import logging
import urllib.parse

from odoo import http, _
from odoo.fields import Date
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)

# Límite de imagen en base64 (~3 MB binario) para evitar saturar workers
MAX_IMAGE_B64_LEN = 4 * 1024 * 1024


def _is_approved_seller(partner):
    """Única fuente de verdad del rol vendedor en el portal."""
    return bool(partner and partner.is_marketplace_seller
                and partner.marketplace_seller_status == 'approved')


def _to_float(value, default=0.0):
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


def _valid_public_categ_ids(raw_id):
    try:
        categ = request.env['product.public.category'].sudo().browse(int(raw_id))
        return [categ.id] if categ.exists() else []
    except (TypeError, ValueError):
        return []


def _extract_b64_image(value):
    """Devuelve el base64 limpio de un data-URL de imagen válido o False."""
    if value and value.startswith('data:image') and len(value) <= MAX_IMAGE_B64_LEN:
        return value.split(',', 1)[1]
    if value and value.startswith('data:image'):
        _logger.warning("Imagen rechazada por exceder el tamaño máximo permitido")
    return False


def _set_stock_quantity(product_tmpl, target_qty):
    """Fija (no suma) el stock disponible del producto en el almacén principal."""
    variant = product_tmpl.product_variant_id
    warehouse = request.env['stock.warehouse'].sudo().search(
        [('company_id', '=', request.env.company.id)], limit=1)
    if not (variant and warehouse and warehouse.lot_stock_id):
        return
    location = warehouse.lot_stock_id
    Quant = request.env['stock.quant'].sudo()
    current = sum(Quant.search([
        ('product_id', '=', variant.id),
        ('location_id', 'child_of', location.id),
    ]).mapped('quantity'))
    diff = target_qty - current
    if diff:
        Quant._update_available_quantity(variant, location, diff)


class CustomHome(Home):
    def _login_redirect(self, uid, redirect=None):
        url = super(CustomHome, self)._login_redirect(uid, redirect=redirect)
        if url in ['/my', '/', '/my/home'] or not url:
            user = request.env['res.users'].sudo().browse(uid)
            if _is_approved_seller(user.partner_id):
                return '/my/seller/dashboard'
            else:
                return '/shop'
        return url

class MarketplaceSellerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(MarketplaceSellerPortal, self)._prepare_home_portal_values(counters)
        return values

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        partner = request.env.user.partner_id
        # Si solicitó explícitamente ver sus compras personales
        if kw.get('purchases'):
            return super(MarketplaceSellerPortal, self).home(**kw)
            
        # Redirección por defecto según el rol
        if _is_approved_seller(partner):
            return request.redirect('/my/seller/dashboard')
        else:
            return request.redirect('/shop')

    @http.route(['/my/seller/dashboard'], type='http', auth="user", website=True)
    def portal_seller_dashboard(self, **kw):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        # Resumen de órdenes
        orders = request.env['sale.order'].sudo().search([
            ('marketplace_seller_id', '=', partner.id),
            ('state', 'in', ['sale', 'done'])
        ])
        
        total_sales = sum(orders.mapped('amount_total'))
        total_commission = sum(orders.mapped('marketplace_commission_total'))
        net_sales = total_sales - total_commission
        
        # Conteo de productos
        products_count = request.env['product.template'].sudo().search_count([
            ('marketplace_seller_id', '=', partner.id)
        ])
        
        # Órdenes pendientes por atender/despachar
        pending_orders = orders.filtered(lambda o: o.state == 'sale')
        pending_orders_count = len(pending_orders)

        # Misiones de activación estilo Mercado Libre
        step_account = True
        step_profile = bool(partner.vat and (partner.phone or partner.mobile))
        step_product = products_count > 0
        step_sale = len(orders) > 0
        
        if not step_profile:
            current_mission = {
                'step_name': 'Paso 1: Configurar Tienda',
                'title': 'Completa los datos de tu tienda y RUC',
                'desc': 'Ingresa tu RUC/DNI y datos de contacto para activar tus opciones de cobro.',
                'cta_text': 'Completar Datos',
                'cta_url': '/my/seller/settings'
            }
        elif not step_product:
            current_mission = {
                'step_name': 'Paso 2: Publicar Productos',
                'title': 'Crea tu primera publicación',
                'desc': 'Sube tus primeros productos con foto y precio para empezar a vender.',
                'cta_text': 'Publicar Producto',
                'cta_url': '/my/seller/products/new'
            }
        elif not step_sale:
            current_mission = {
                'step_name': 'Paso 3: Primera Venta',
                'title': '¡Listo para tu primera venta!',
                'desc': 'Comparte tus productos con clientes en redes sociales para recibir tu primer pedido.',
                'cta_text': 'Ver Catálogo',
                'cta_url': '/my/seller/products'
            }
        else:
            current_mission = {
                'step_name': '¡Tienda en Despegue!',
                'title': '¡Vas por excelente camino!',
                'desc': 'Mantén tus despachos a tiempo para seguir aumentando tu reputación.',
                'cta_text': 'Ver Órdenes',
                'cta_url': '/my/seller/orders'
            }

        values = {
            'page_name': 'seller_dashboard',
            'partner': partner,
            'orders': orders[:5], # Últimas 5
            'total_sales': total_sales,
            'total_commission': total_commission,
            'net_sales': net_sales,
            'products_count': products_count,
            'pending_orders_count': pending_orders_count,
            'step_account': step_account,
            'step_profile': step_profile,
            'step_product': step_product,
            'step_sale': step_sale,
            'current_mission': current_mission,
        }
        settlements = request.env['marketplace.settlement'].sudo().search([('seller_id', '=', partner.id)], limit=5)
        values['settlements'] = settlements
        return request.render("wango_marketplace.portal_seller_dashboard", values)

    @http.route(['/my/seller/orders', '/my/seller/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_seller_orders(self, page=1, tab='today', search='', **kw):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        today_date = Date.today()
        base_domain = [
            ('marketplace_seller_id', '=', partner.id),
            ('state', 'in', ['sale', 'done'])
        ]

        if search:
            search_str = search.strip()
            base_domain.append('|')
            base_domain.append(('name', 'ilike', search_str))
            base_domain.append(('partner_id.name', 'ilike', search_str))

        # Todas las órdenes para conteo de tabs
        all_orders = request.env['sale.order'].sudo().search(base_domain, order='date_order desc')

        # Clasificación por ciclo logístico (tabs mutuamente excluyentes)
        # 1. En tránsito: encomienda despachada o en camino
        orders_transit = all_orders.filtered(
            lambda o: o.state == 'sale' and getattr(o, 'wango_shipment_id', False)
            and getattr(o.wango_shipment_id, 'state', '') in ('dispatched', 'in_transit')
        )
        pending = all_orders.filtered(lambda o: o.state == 'sale') - orders_transit
        # 2. Envíos de hoy: pendientes con entrega hoy/vencida o sin fecha
        orders_today = pending.filtered(
            lambda o: not o.estimated_delivery_date or o.estimated_delivery_date <= today_date
        )
        # 3. Próximos días: pendientes con fecha futura
        orders_upcoming = pending - orders_today
        # 4. Finalizadas: entregadas con éxito
        orders_done = all_orders.filtered(lambda o: o.state == 'done')

        # Tab activo
        if tab == 'today':
            active_list = orders_today
        elif tab == 'upcoming':
            active_list = orders_upcoming
        elif tab == 'transit':
            active_list = orders_transit
        elif tab == 'done':
            active_list = orders_done
        else:
            tab = 'all'
            active_list = all_orders

        total_orders_tab = len(active_list)
        pager = portal_pager(
            url="/my/seller/orders",
            url_args={'tab': tab, 'search': search},
            total=total_orders_tab,
            page=page,
            step=10
        )

        offset = pager['offset']
        orders_page = active_list[offset:offset + 10]

        values = {
            'page_name': 'seller_orders',
            'orders': orders_page,
            'pager': pager,
            'default_url': '/my/seller/orders',
            'tab': tab,
            'search': search,
            'count_today': len(orders_today),
            'count_upcoming': len(orders_upcoming),
            'count_transit': len(orders_transit),
            'count_done': len(orders_done),
            'count_all': len(all_orders),
            'today_date': today_date,
        }
        return request.render("wango_marketplace.portal_seller_orders", values)

    @http.route(['/my/seller/products', '/my/seller/products/page/<int:page>'], type='http', auth="user", website=True)
    def portal_seller_products(self, page=1, archived=None, **kw):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')

        show_archived = bool(archived)
        Product = request.env['product.template'].sudo().with_context(active_test=False)
        base = [('marketplace_seller_id', '=', partner.id)]
        domain = base + [('active', '=', not show_archived)]

        product_count = Product.search_count(domain)
        pager = portal_pager(
            url="/my/seller/products",
            url_args={'archived': 1} if show_archived else {},
            total=product_count,
            page=page,
            step=10
        )

        products = Product.search(
            domain, limit=10, offset=pager['offset'], order='create_date desc'
        )

        values = {
            'page_name': 'seller_products',
            'products': products,
            'pager': pager,
            'default_url': '/my/seller/products',
            'show_archived': show_archived,
            'count_active': Product.search_count(base + [('active', '=', True)]),
            'count_archived': Product.search_count(base + [('active', '=', False)]),
        }
        return request.render("wango_marketplace.portal_seller_products", values)

    @http.route(['/my/seller/products/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_seller_product_new(self, **post):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        if request.httprequest.method == 'POST':
            name = (post.get('name') or '').strip()
            if not name:
                return request.redirect('/my/seller/products/new')

            # 1. Asignar categoría interna por defecto ("Todos" / All) — Odoo 20 usa 'consu' + is_storable=True
            default_internal_categ = request.env.ref('product.product_category_all', raise_if_not_found=False)
            raw_type = post.get('type')
            is_storable = raw_type == 'product'
            product_type = 'service' if raw_type == 'service' else 'consu'

            product_vals = {
                'name': name,
                'list_price': _to_float(post.get('list_price')),
                'type': product_type,
                'is_storable': is_storable,
                'description_sale': post.get('description'),
                'categ_id': default_internal_categ.id if default_internal_categ else False,
            }

            # 2. Asignar Categoría de eCommerce (Pública) validada
            categ_ids = _valid_public_categ_ids(post.get('public_categ_id'))
            if categ_ids:
                product_vals['public_categ_ids'] = [(6, 0, categ_ids)]

            # 3. Procesar Foto 1 (Portada Principal)
            img1 = _extract_b64_image(post.get('image_1920_b64'))
            if img1:
                product_vals['image_1920'] = img1
            elif 'image_1920' in request.httprequest.files:
                upload = request.httprequest.files.get('image_1920')
                if upload:
                    product_vals['image_1920'] = base64.b64encode(upload.read())

            new_product = request.env['product.template'].sudo().create(product_vals)
            new_product.sudo().write({
                'marketplace_seller_id': partner.id,
                'marketplace_status': 'pending',
                'is_published': False
            })

            # 4. Procesar Fotos Extras (Fotos 2, 3 y 4 en product.template.image_ids)
            for idx in (1, 2, 3):
                raw_b64 = _extract_b64_image(post.get('extra_image_%d_b64' % idx))
                if raw_b64:
                    try:
                        request.env['product.image'].sudo().create({
                            'name': '%s - Foto %d' % (new_product.name, idx + 1),
                            'product_tmpl_id': new_product.id,
                            'image_1920': raw_b64
                        })
                    except Exception:
                        _logger.exception("Error guardando foto extra %s del producto %s", idx, new_product.id)

            # 5. Fijar Stock Inicial (si es almacenable)
            stock_qty = _to_float(post.get('stock_qty'))
            if new_product.type == 'consu' and getattr(new_product, 'is_storable', False) and stock_qty > 0:
                _set_stock_quantity(new_product, stock_qty)

            return request.redirect('/my/seller/products')
            
        # Buscar categorías de eCommerce en lugar de internas
        public_categories = request.env['product.public.category'].sudo().search([])
        return request.render("wango_marketplace.portal_seller_product_form", {
            'page_name': 'seller_product_new',
            'public_categories': public_categories,
        })

    @http.route(['/my/seller/products/edit/<int:product_id>'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_seller_product_edit(self, product_id, **post):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or product.marketplace_seller_id.id != partner.id:
            return request.redirect('/my/seller/products')
            
        if request.httprequest.method == 'POST':
            raw_type = post.get('type')
            product_type = 'service' if raw_type == 'service' else ('consu' if raw_type in ('consu', 'product') else product.type)
            product_vals = {
                'name': (post.get('name') or '').strip() or product.name,
                'list_price': _to_float(post.get('list_price'), product.list_price),
                'type': product_type,
                'description_sale': post.get('description'),
            }
            if raw_type == 'product':
                product_vals['is_storable'] = True

            # Re-asignar Categoría de eCommerce (Pública) validada
            categ_ids = _valid_public_categ_ids(post.get('public_categ_id'))
            if categ_ids:
                product_vals['public_categ_ids'] = [(6, 0, categ_ids)]

            # Procesar Foto 1 (Portada Principal)
            img1_b64 = post.get('image_1920_b64')
            img1 = _extract_b64_image(img1_b64)
            if img1:
                product_vals['image_1920'] = img1
            elif img1_b64 == '__REMOVE__':
                product_vals['image_1920'] = False
            elif 'image_1920' in request.httprequest.files:
                upload = request.httprequest.files.get('image_1920')
                if upload:
                    product_vals['image_1920'] = base64.b64encode(upload.read())

            # Forzar estado a Pendiente y Despublicar (requiere re-aprobación)
            product_vals['marketplace_status'] = 'pending'
            product_vals['is_published'] = False

            product.sudo().write(product_vals)

            # Procesar Fotos Extras (Fotos 2, 3 y 4)
            try:
                existing_extra_images = product.product_template_image_ids
                for idx in (1, 2, 3):
                    extra_b64 = post.get('extra_image_%d_b64' % idx)
                    raw_b64 = _extract_b64_image(extra_b64)
                    if raw_b64:
                        if len(existing_extra_images) >= idx:
                            existing_extra_images[idx - 1].sudo().write({'image_1920': raw_b64})
                        else:
                            request.env['product.image'].sudo().create({
                                'name': '%s - Foto %d' % (product.name, idx + 1),
                                'product_tmpl_id': product.id,
                                'image_1920': raw_b64
                            })
                    elif extra_b64 == '__REMOVE__':
                        if len(existing_extra_images) >= idx:
                            existing_extra_images[idx - 1].sudo().unlink()
            except Exception:
                _logger.exception("Error actualizando fotos extra del producto %s", product.id)

            # Fijar Stock (reemplaza el valor actual, ya no lo suma)
            if product.type == 'consu' and getattr(product, 'is_storable', False) and post.get('stock_qty') not in (None, ''):
                _set_stock_quantity(product, _to_float(post.get('stock_qty')))

            return request.redirect('/my/seller/products')
            
        public_categories = request.env['product.public.category'].sudo().search([])
        return request.render("wango_marketplace.portal_seller_product_form", {
            'page_name': 'seller_product_edit',
            'product': product,
            'public_categories': public_categories,
        })

    @http.route(['/my/seller/products/archive/<int:product_id>'], type='http', auth="user", methods=['POST'], website=True)
    def archive_seller_product(self, product_id, **post):
        seller = request.env.user.partner_id
        if not _is_approved_seller(seller):
            return request.redirect('/my/seller/dashboard')

        product = request.env['product.template'].sudo().browse(product_id)
        if product.exists() and product.marketplace_seller_id.id == seller.id:
            product.sudo().write({
                'active': False,
                'is_published': False
            })

        return request.redirect('/my/seller/products')

    @http.route(['/my/seller/products/unarchive/<int:product_id>'], type='http', auth="user", methods=['POST'], website=True)
    def unarchive_seller_product(self, product_id, **post):
        seller = request.env.user.partner_id
        if not _is_approved_seller(seller):
            return request.redirect('/my')

        product = request.env['product.template'].sudo().with_context(active_test=False).browse(product_id)
        if product.exists() and product.marketplace_seller_id.id == seller.id:
            # Vuelve al catálogo pero requiere nueva aprobación antes de publicarse
            product.write({
                'active': True,
                'is_published': False,
                'marketplace_status': 'pending',
            })

        return request.redirect('/my/seller/products?archived=1')

    @http.route(['/my/seller/orders/<int:order_id>'], type='http', auth="user", website=True)
    def portal_seller_order_detail(self, order_id, **kw):
        try:
            partner = request.env.user.partner_id
            if not _is_approved_seller(partner):
                return request.redirect('/my')
                
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists() or order.marketplace_seller_id.id != partner.id:
                return request.redirect('/my/seller/orders')

            # Preparar líneas de productos como datos limpios
            order_lines = []
            for line in order.order_line:
                if getattr(line, 'is_delivery', False):
                    continue
                product = line.product_id
                order_lines.append({
                    'id': line.id,
                    'name': (product and product.name) or line.name or 'Producto',
                    'default_code': (product and product.default_code) or 'S/C',
                    'has_image': bool(product and product.image_128),
                    'product_id': product.id if product else False,
                    'qty': int(line.product_uom_qty or 1),
                    'price_unit_str': 'S/ %.2f' % (line.price_unit or 0.0),
                    'price_subtotal_str': 'S/ %.2f' % (line.price_subtotal or 0.0),
                })

            # Fechas formateadas limpias
            order_date_str = order.date_order.strftime('%d/%m/%Y') if order.date_order else 'Reciente'
            est_date = getattr(order, 'estimated_delivery_date', False)
            delivery_date_str = est_date.strftime('%d/%m/%Y') if est_date else 'Por coordinar'

            # WhatsApp sanitizado
            whatsapp_url = False
            phone_val = (order.partner_id.mobile or order.partner_id.phone or '') if order.partner_id else ''
            clean_digits = ''.join(c for c in phone_val if c.isdigit())
            if clean_digits:
                if len(clean_digits) == 9:
                    clean_digits = '51' + clean_digits
                cust_name = order.partner_id.name or 'Cliente'
                msg = f"Hola {cust_name}, te escribo de Mercado Wanka sobre tu pedido {order.name}."
                whatsapp_url = f"https://wa.me/{clean_digits}?text={urllib.parse.quote(msg)}"

            cost = getattr(order, 'shipping_cost', 0.0) or 0.0
            shipping_cost_str = ('S/ %.2f' % cost) if cost > 0 else 'Gratis'

            delivery_type = getattr(order, 'delivery_type', False)
            store_branch = getattr(order, 'store_branch_id', False)
            agency = getattr(order, 'agency_id', False)
            district = getattr(order, 'delivery_district_id', False)
            province = getattr(order, 'delivery_province_id', False)
            shipping_partner = order.partner_shipping_id or order.partner_id

            template_vals = {
                'page_name': 'seller_order_detail',
                'order': order,
                'order_lines': order_lines,
                'order_date_str': order_date_str,
                'delivery_date_str': delivery_date_str,
                'whatsapp_url': whatsapp_url,
                'shipping_cost_str': shipping_cost_str,
                'amount_untaxed_str': 'S/ %.2f' % (order.amount_untaxed or 0.0),
                'amount_total_str': 'S/ %.2f' % (order.amount_total or 0.0),
                'delivery_type': delivery_type,
                'store_branch': store_branch,
                'agency': agency,
                'district_name': district.name if district else '',
                'province_name': province.name if province else '',
                'street': shipping_partner.street or 'Dirección no especificada' if shipping_partner else '',
                'street2': shipping_partner.street2 or '' if shipping_partner else '',
                'city': shipping_partner.city or '' if shipping_partner else '',
            }
                
            response = request.render("wango_marketplace.portal_seller_order_detail", template_vals)
            response.flatten()  # Forzar evaluación de QWeb dentro del bloque try
            return response
        except Exception:
            # Nunca exponer trazas internas al usuario final
            _logger.exception("Error renderizando detalle de orden %s", order_id)
            return request.render("http_routing.http_error", {
                'status_code': _('Error'),
                'status_message': _('No pudimos cargar el detalle de esta orden. Inténtalo nuevamente o contacta a soporte.'),
            })


    @http.route(['/my/seller/orders/<int:order_id>/update_state'], type='http', auth="user", methods=['POST'], website=True)
    def portal_seller_order_update_state(self, order_id, **post):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        order = request.env['sale.order'].sudo().browse(order_id)
        if order.exists() and order.marketplace_seller_id.id == partner.id:
            new_state = post.get('new_state')
            # En un MVP, los vendedores podrian marcarlo como 'done' (entregado)
            if new_state == 'done' and order.state == 'sale':
                order.sudo().write({'state': 'done'})
                
        return request.redirect('/my/seller/orders/%s' % order_id)

    @http.route(['/my/seller/orders/<int:order_id>/label'], type='http', auth="user", website=True)
    def portal_seller_order_shipping_label(self, order_id, **kw):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')
            
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.marketplace_seller_id.id != partner.id:
            return request.redirect('/my/seller/orders')

        order_lines = []
        for line in order.order_line:
            if getattr(line, 'is_delivery', False):
                continue
            product = line.product_id
            order_lines.append({
                'name': (product and product.name) or line.name or 'Producto',
                'default_code': (product and product.default_code) or 'S/C',
                'qty': int(line.product_uom_qty or 1),
            })

        order_date_str = order.date_order.strftime('%d/%m/%Y') if order.date_order else 'Reciente'
        est_date = getattr(order, 'estimated_delivery_date', False)
        delivery_date_str = est_date.strftime('%d/%m/%Y') if est_date else 'Por coordinar'

        delivery_type = getattr(order, 'delivery_type', False)
        store_branch = getattr(order, 'store_branch_id', False)
        agency = getattr(order, 'agency_id', False)
        district = getattr(order, 'delivery_district_id', False)
        province = getattr(order, 'delivery_province_id', False)
        shipping_partner = order.partner_shipping_id or order.partner_id

        vals = {
            'order': order,
            'seller': partner,
            'order_lines': order_lines,
            'order_date_str': order_date_str,
            'delivery_date_str': delivery_date_str,
            'delivery_type': delivery_type,
            'store_branch': store_branch,
            'agency': agency,
            'district_name': district.name if district else '',
            'province_name': province.name if province else '',
            'recipient_name': (shipping_partner and shipping_partner.name) or 'Cliente',
            'recipient_phone': (shipping_partner and (shipping_partner.mobile or shipping_partner.phone)) or 'No especificado',
            'recipient_vat': (shipping_partner and shipping_partner.vat) or '',
            'street': shipping_partner.street or 'Dirección no especificada' if shipping_partner else '',
            'street2': shipping_partner.street2 or '' if shipping_partner else '',
            'city': shipping_partner.city or '' if shipping_partner else '',
            'tracking_url': urllib.parse.quote(self._get_public_tracking_url(order), safe=''),
        }

        return request.render("wango_marketplace.portal_seller_order_shipping_label", vals)


    @http.route(['/my/seller/settings'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_seller_settings(self, **post):
        partner = request.env.user.partner_id
        if not _is_approved_seller(partner):
            return request.redirect('/my')

        success_msg = False
        Branch = request.env['delivery.store.branch'].sudo()
        seller_branch = Branch.search([
            ('seller_id', '=', partner.id),
            ('point_type', '=', 'seller_store')
        ], limit=1)

        if request.httprequest.method == 'POST':
            # 1. Guardar Datos Nativos en res.partner (Nombre, RUC, Teléfono, Calle, Logo)
            # El email NO se edita aquí: puede ser el login y requiere verificación.
            partner_vals = {
                'name': (post.get('name') or '').strip() or partner.name,
                'vat': (post.get('vat') or '').strip() or partner.vat,
                'phone': post.get('phone', partner.phone),
                'street': post.get('street', partner.street),
            }

            # Procesar subida de Logo / Avatar si se envió un archivo
            logo_file = post.get('logo')
            if logo_file and hasattr(logo_file, 'read'):
                logo_content = logo_file.read()
                if logo_content:
                    partner_vals['image_1920'] = base64.b64encode(logo_content)

            partner.sudo().write(partner_vals)

            # 2. Guardar Configuración de Retiro en delivery.store.branch (Sin tocar columnas de res.partner)
            allow_pickup = bool(post.get('seller_allow_pickup'))
            if allow_pickup:
                dept_id = int(post.get('seller_pickup_department_id')) if post.get('seller_pickup_department_id') else False
                prov_id = int(post.get('seller_pickup_province_id')) if post.get('seller_pickup_province_id') else False
                dist_id = int(post.get('seller_pickup_district_id')) if post.get('seller_pickup_district_id') else False

                # Fallback si no tiene departamento seleccionado
                if not dept_id:
                    lima = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'PE')], limit=1)
                    dept_id = lima.id if lima else False

                branch_vals = {
                    'name': 'Tienda de %s' % (post.get('name') or partner.name),
                    'point_type': 'seller_store',
                    'seller_id': partner.id,
                    'address': post.get('seller_pickup_address') or post.get('street') or 'Dirección no especificada',
                    'reference': post.get('seller_pickup_reference', ''),
                    'schedule': post.get('seller_pickup_schedule', 'Lunes a Sábado 9:00 AM - 7:00 PM'),
                    'department_id': dept_id,
                    'province_id': prov_id,
                    'district_id': dist_id,
                    'active': True,
                }
                if seller_branch:
                    seller_branch.write(branch_vals)
                else:
                    seller_branch = Branch.create(branch_vals)
            else:
                if seller_branch:
                    seller_branch.write({'active': False})

            success_msg = "¡Datos de tu tienda y opciones de retiro guardados con éxito!"

        departments = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'PE')], order='name asc')
        provinces = request.env['wango.province'].sudo().search([], order='name asc')
        districts = request.env['wango.district'].sudo().search([], order='name asc')

        values = {
            'page_name': 'seller_settings',
            'partner': partner,
            'seller_branch': seller_branch,
            'departments': departments,
            'provinces': provinces,
            'districts': districts,
            'success_msg': success_msg,
        }
        return request.render("wango_marketplace.portal_seller_settings", values)

    # ── MÓDULO SENIOR DE SEGUIMIENTO (TRACKING) PARA COMPRADORES ──
    @http.route(['/my/orders/<int:order_id>/tracking', '/track/<string:order_ref>'], type='http', auth="public", website=True)
    def portal_order_tracking(self, order_id=None, order_ref=None, access_token=None, **kw):
        """
        Página Web de Seguimiento en Tiempo Real para el Comprador estilo Mercado Envíos.
        Permite consulta autenticada o mediante código de orden público / token.
        """
        Order = request.env['sale.order'].sudo()
        order = None

        if order_id:
            order = Order.browse(order_id)
        elif order_ref:
            # Buscar por nombre de orden (e.g. S00012) o por referencia de cliente
            order = Order.search([('name', '=ilike', order_ref.strip())], limit=1)
            if not order:
                # Intentar agregando prefijos comunes si el usuario sólo escribió números
                clean_ref = order_ref.strip()
                if clean_ref.isdigit():
                    order = Order.search([('name', '=ilike', 'S%' + clean_ref)], limit=1)

        if not order or not order.exists() or not self._can_view_tracking(order, access_token or kw.get('token')):
            # Mismo mensaje si no existe o si no hay permiso: evita enumeración de órdenes
            return request.render("wango_marketplace.portal_order_tracking_not_found", {
                'searched_ref': order_ref or str(order_id)
            })

        # Determinación de los pasos del Timeline Logístico (Mercado Wanka)
        # 1. confirmed (Pago Aprobado)
        # 2. preparing (En Preparación / Empacando)
        # 3. in_transit / ready_pickup (En Camino / Listo para retiro)
        # 4. delivered (Entregado con éxito)

        step_current = 1
        delivery_mode = order.delivery_type or 'home_delivery'
        shipment = order.wango_shipment_id

        if order.state == 'cancel':
            step_current = -1
        elif order.state == 'done':
            step_current = 4
        elif order.state == 'sale':
            if delivery_mode == 'store_pickup':
                # Si es retiro en tienda y la tienda ya lo tiene listo (o si pasó 1 día)
                step_current = 3
            elif delivery_mode == 'agency_shipping':
                if shipment and shipment.state in ['in_transit', 'delivered']:
                    step_current = 4 if shipment.state == 'delivered' else 3
                elif shipment and shipment.state in ['registered', 'picked_up']:
                    step_current = 2
                else:
                    step_current = 2
            else:
                # Despacho a domicilio
                step_current = 2

        # Datos de contacto de WhatsApp del vendedor
        seller = order.marketplace_seller_id or (order.order_line and order.order_line[0].product_id.marketplace_seller_id)
        seller_phone = ''
        seller_name = 'Vendedor Mercado Wanka'
        if seller:
            seller_name = seller.name
            raw_phone = (seller.phone or seller.mobile or '').replace(' ', '').replace('-', '').replace('+', '')
            if raw_phone:
                if len(raw_phone) == 9 and not raw_phone.startswith('51'):
                    raw_phone = '51' + raw_phone
                seller_phone = raw_phone

        values = {
            'page_name': 'order_tracking',
            'order': order,
            'step_current': step_current,
            'delivery_mode': delivery_mode,
            'shipment': shipment,
            'seller': seller,
            'seller_name': seller_name,
            'seller_phone': seller_phone,
        }
        return request.render("wango_marketplace.portal_order_tracking", values)

    @http.route(['/track'], type='http', auth="public", website=True)
    def track_order_search(self, q=None, **kw):
        """Buscador público de rastreo de pedidos"""
        if q:
            return request.redirect('/track/%s' % urllib.parse.quote(q.strip()))
        return request.render("wango_marketplace.portal_order_tracking_search", {})

    # ── Helpers de seguridad para el tracking ──
    def _can_view_tracking(self, order, token=None):
        """Permite ver el tracking solo al comprador, al vendedor, a usuarios internos
        o a quien tenga el access_token de la orden (QR del ticket / link del correo)."""
        if token and order.access_token and consteq(order.access_token, token):
            return True
        user = request.env.user
        if user._is_public():
            return False
        if user.has_group('base.group_user'):
            return True
        partner = user.partner_id
        if order.partner_id.commercial_partner_id == partner.commercial_partner_id:
            return True
        return bool(order.marketplace_seller_id and order.marketplace_seller_id == partner)

    def _get_public_tracking_url(self, order):
        base_url = (request.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value or 'https://mercadowanka.com').rstrip('/')
        token = order.sudo()._portal_ensure_token()
        return '%s/track/%s?access_token=%s' % (base_url, order.name, token)

