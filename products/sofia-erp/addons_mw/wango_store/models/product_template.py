# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_daily_deal = fields.Boolean(
        string='Oferta del Día', 
        default=False,
        help='Marcar para incluir este producto en la sección Ofertas del Día de la portada.'
    )
    is_deal_highlight = fields.Boolean(
        string='Oferta Destacada Principal', 
        default=False,
        help='Marcar como la oferta principal en la columna izquierda destacada.'
    )
    deal_priority = fields.Integer(
        string='Prioridad de Oferta', 
        default=10,
        help='Menor número indica mayor prioridad para aparecer primero en el carrusel.'
    )
    compare_list_price = fields.Float(
        string='Precio Anterior / Tachado',
        digits='Product Price',
        help='Precio de referencia antes del descuento que se mostrará tachado (Ej: S/ 240).'
    )
    deal_discount_percent = fields.Integer(
        string='Porcentaje de Descuento (% OFF)',
        help='Porcentaje a mostrar en la etiqueta verde. Si se deja en 0, se calcula automáticamente según el precio tachado.'
    )
    deal_installments_text = fields.Char(
        string='Texto de Cuotas',
        default='6 cuotas sin interés',
        help='Ej: 6 cuotas de S/ 26.67 sin interés'
    )
    deal_coupon_badge = fields.Char(
        string='Badge de Cupón',
        help='Ej: Cupón S/ 25 OFF (opcional)'
    )
    deal_free_shipping = fields.Boolean(
        string='Mostrar "Envío gratis"',
        default=True,
        help='Muestra la insignia verde de Envío gratis en la tarjeta.'
    )

    wango_product_condition = fields.Selection([
        ('new', 'Nuevo'),
        ('reconditioned', 'Reacondicionado'),
        ('used', 'Usado'),
    ], string='Condición del Producto', default='new')

    sales_count_base = fields.Integer(
        string='Ventas Base / Social Proof',
        default=0,
        help='Unidades vendidas de partida (mantener en 0 para métricas 100% reales).'
    )
    sales_count_real = fields.Integer(
        string='Ventas Reales',
        compute='_compute_sales_count_real',
        help='Unidades vendidas en órdenes de venta confirmadas.'
    )
    wango_sales_count_total = fields.Integer(
        string='Total Unidades Vendidas',
        compute='_compute_wango_sales_total',
        store=True
    )
    wango_sales_display = fields.Char(
        string='Texto de Ventas Mostrado',
        compute='_compute_wango_sales_display',
        store=True
    )
    wango_rating_avg = fields.Float(
        string='Calificación Estrellas (1.0 - 5.0)',
        default=0.0,
        digits=(3, 1),
        help='Calificación promedio real del producto.'
    )
    wango_rating_count = fields.Integer(
        string='Cantidad de Opiniones',
        default=0,
        help='Número real de reseñas y opiniones aprobadas.'
    )
    review_ids = fields.One2many(
        'wango.product.review',
        'product_tmpl_id',
        string='Opiniones y Reseñas'
    )
    review_count = fields.Integer(
        string='Total Reseñas Registradas',
        compute='_compute_review_count'
    )

    @api.depends('review_ids')
    def _compute_review_count(self):
        for tmpl in self:
            tmpl.review_count = len(tmpl.review_ids)

    def get_published_reviews(self):
        self.ensure_one()
        return self.review_ids.filtered(lambda r: r.is_published).sorted(key=lambda r: (r.sequence, -r.id))

    def action_generate_sample_reviews(self):
        """Acción rápida para generar opiniones de ejemplo con 1 clic."""
        for tmpl in self:
            if not tmpl.review_ids:
                self.env['wango.product.review'].create([
                    {
                        'product_tmpl_id': tmpl.id,
                        'author_name': 'Carlos M.',
                        'author_location': 'Huancayo',
                        'rating': '5',
                        'title': 'Excelente producto y entrega puntual',
                        'content': 'Superó mis expectativas. Llegó en perfectas condiciones, muy bien protegido y sellado en su empaque original. La atención y rapidez de entrega en Huancayo fue impecable. Muy recomendado.',
                        'date_display': 'Hace 3 días',
                        'is_verified_purchase': True,
                        'helpful_count': 14,
                        'sequence': 10,
                    },
                    {
                        'product_tmpl_id': tmpl.id,
                        'author_name': 'Andrea R.',
                        'author_location': 'El Tambo',
                        'rating': '5',
                        'title': '100% original y compra garantizada',
                        'content': 'La calidad es muy buena y tal como se ve en la descripción. Pagué con Yape sin problemas y me llegó la boleta directo a mi WhatsApp. Sin duda volveré a comprar en la plataforma.',
                        'date_display': 'Hace 1 semana',
                        'is_verified_purchase': True,
                        'helpful_count': 9,
                        'sequence': 20,
                    },
                    {
                        'product_tmpl_id': tmpl.id,
                        'author_name': 'Javier P.',
                        'author_location': 'Chilca',
                        'rating': '5',
                        'title': 'Muy buen servicio y despacho rápido',
                        'content': 'Excelente relación precio-calidad. Todo conforme con el despacho y el recojo. La tienda fue muy amable en resolver mis dudas antes de concretar la orden.',
                        'date_display': 'Hace 2 semanas',
                        'is_verified_purchase': True,
                        'state': 'approved',
                        'is_published': True,
                        'sequence': 30,
                    },
                ])
        return True

    def can_user_review(self, partner=None):
        """Verifica si el usuario logueado ha comprado este producto y puede dejar una opinión."""
        self.ensure_one()
        if not partner:
            partner = self.env.user.partner_id
        public_partner = self.env.ref('base.public_partner', raise_if_not_found=False)
        if not partner or (public_partner and partner.id == public_partner.id):
            return False, 'not_logged'

        # Verificar compras confirmadas (sale o done) del producto
        lines = self.env['sale.order.line'].sudo().search([
            ('order_id.partner_id', '=', partner.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('product_id.product_tmpl_id', '=', self.id),
        ], limit=1)

        if not lines:
            return False, 'not_purchased'

        # Verificar si ya dejó una reseña pendiente o aprobada
        existing_review = self.env['wango.product.review'].sudo().search([
            ('product_tmpl_id', '=', self.id),
            ('partner_id', '=', partner.id),
            ('state', 'in', ['pending', 'approved']),
        ], limit=1)
        if existing_review:
            return False, 'already_reviewed'

        return True, 'can_review'

    def _compute_sales_count_real(self):
        for tmpl in self:
            try:
                lines = self.env['sale.order.line'].sudo().search([
                    ('product_id.product_tmpl_id', '=', tmpl.id),
                    ('order_id.state', 'in', ['sale', 'done']),
                ])
                tmpl.sales_count_real = int(sum(lines.mapped('product_uom_qty')))
            except Exception:
                tmpl.sales_count_real = 0

    @api.depends('sales_count_base')
    def _compute_wango_sales_total(self):
        for tmpl in self:
            real_val = getattr(tmpl, 'sales_count_real', 0) or 0
            base_val = tmpl.sales_count_base or 0
            tmpl.wango_sales_count_total = base_val + real_val

    @api.depends('wango_sales_count_total')
    def _compute_wango_sales_display(self):
        for tmpl in self:
            total = tmpl.wango_sales_count_total or 0
            if total <= 0:
                tmpl.wango_sales_display = 'Nuevo'
            elif total < 5:
                tmpl.wango_sales_display = f"{total} vendidos"
            elif total < 25:
                tmpl.wango_sales_display = "+5 vendidos"
            elif total < 50:
                tmpl.wango_sales_display = "+25 vendidos"
            elif total < 100:
                tmpl.wango_sales_display = "+50 vendidos"
            elif total < 250:
                tmpl.wango_sales_display = "+100 vendidos"
            elif total < 500:
                tmpl.wango_sales_display = "+250 vendidos"
            elif total < 1000:
                tmpl.wango_sales_display = "+500 vendidos"
            else:
                thousands = total // 1000
                tmpl.wango_sales_display = f"+{thousands} mil vendidos"

    def get_wango_stars_list(self):
        """Retorna una lista de 5 valores ('full', 'half', 'empty') según la calificación."""
        self.ensure_one()
        score = self.wango_rating_avg or 4.9
        stars = []
        for i in range(1, 6):
            if score >= i:
                stars.append('full')
            elif score >= i - 0.7:
                stars.append('half')
            else:
                stars.append('empty')
        return stars

    def get_effective_discount_pct(self):
        """Calcula el porcentaje de descuento efectivo para mostrar."""
        self.ensure_one()
        if self.deal_discount_percent > 0:
            return self.deal_discount_percent
        if self.compare_list_price > self.list_price > 0:
            diff = self.compare_list_price - self.list_price
            return int(round((diff / self.compare_list_price) * 100))
        return 0

    @api.model
    def get_wango_highlight_deal(self, website=None):
        """Obtiene la oferta destacada principal con fallback elegante si no hay ninguna configurada."""
        domain = [('website_published', '=', True)]
        if website:
            domain += website.website_domain()
        
        # 1. Buscar el marcado específicamente como destacado
        highlight = self.search(domain + [('is_deal_highlight', '=', True)], limit=1)
        if highlight:
            return highlight
            
        # 2. Si no hay, buscar el primer producto marcado como oferta del día
        daily = self.search(domain + [('is_daily_deal', '=', True)], order='deal_priority asc, id desc', limit=1)
        if daily:
            return daily
            
        # 3. Fallback: El producto publicado más reciente
        return self.search(domain, order='id desc', limit=1)

    @api.model
    def get_wango_daily_deals(self, website=None, limit=12):
        """Obtiene las ofertas del día para el carrusel derecho con fallback elegante."""
        domain = [('website_published', '=', True)]
        if website:
            domain += website.website_domain()

        highlight = self.get_wango_highlight_deal(website)
        highlight_id = highlight.id if highlight else 0

        # Buscar ofertas del día excluyendo el destacado principal
        deals = self.search(
            domain + [('is_daily_deal', '=', True), ('id', '!=', highlight_id)],
            order='deal_priority asc, id desc',
            limit=limit
        )

        # Si hay menos de 4 ofertas, completar con productos publicados recientes
        if len(deals) < 4:
            needed = 4 - len(deals)
            existing_ids = deals.ids + ([highlight_id] if highlight_id else [])
            fallbacks = self.search(
                domain + [('id', 'not in', existing_ids)],
                order='id desc',
                limit=needed
            )
            deals = deals | fallbacks

        return deals

    @api.model
    def get_wango_featured_products(self, website=None, limit=10):
        """Obtiene productos recomendados para la sección 'Inspirado en lo último que viste'."""
        domain = [('website_published', '=', True)]
        if website:
            domain += website.website_domain()
        return self.search(domain, order='write_date desc, id desc', limit=limit)

    def get_wango_seller_products(self, limit=12):
        """Obtiene otros productos publicados del mismo vendedor para la ficha de producto.
           Si no hay o no tiene vendedor, devuelve productos relacionados/destacados de la misma categoría."""
        self.ensure_one()
        domain = [
            ('id', '!=', self.id),
            ('website_published', '=', True),
        ]
        
        # 1. Si el producto pertenece a un vendedor marketplace, buscar sus productos aprobados
        if hasattr(self, 'marketplace_seller_id') and self.marketplace_seller_id:
            seller_domain = list(domain) + [
                ('marketplace_seller_id', '=', self.marketplace_seller_id.id),
            ]
            if hasattr(self, 'marketplace_status'):
                seller_domain.append(('marketplace_status', '=', 'approved'))
            seller_prods = self.sudo().search(seller_domain, limit=limit)
            if seller_prods:
                return seller_prods

        # 2. Si no hay otros productos del vendedor, buscar productos de la misma categoría
        if self.public_categ_ids:
            cat_domain = list(domain) + [('public_categ_ids', 'in', self.public_categ_ids.ids)]
            cat_prods = self.sudo().search(cat_domain, limit=limit)
            if cat_prods:
                return cat_prods

        # 3. Fallback general: productos más recientes publicados
        return self.sudo().search(domain, limit=limit)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_effective_discount_pct(self):
        self.ensure_one()
        return self.product_tmpl_id.get_effective_discount_pct()

    def get_wango_seller_products(self, limit=12):
        self.ensure_one()
        return self.product_tmpl_id.get_wango_seller_products(limit=limit)

    def get_wango_stars_list(self):
        self.ensure_one()
        return self.product_tmpl_id.get_wango_stars_list()

    def get_published_reviews(self):
        self.ensure_one()
        return self.product_tmpl_id.get_published_reviews()

    def can_user_review(self, partner=None):
        self.ensure_one()
        return self.product_tmpl_id.can_user_review(partner=partner)
