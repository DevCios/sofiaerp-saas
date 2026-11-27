# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WangoProductReview(models.Model):
    _name = 'wango.product.review'
    _description = 'Opinión y Calificación de Producto'
    _order = 'sequence, id desc'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente Registrado',
        ondelete='set null',
        index=True
    )
    title = fields.Char(
        string='Título de la Opinión',
        required=True,
        default='Excelente producto'
    )
    author_name = fields.Char(
        string='Nombre del Comprador',
        required=True,
        default='Comprador verificado'
    )
    author_location = fields.Char(
        string='Ubicación / Ciudad',
        default='Huancayo'
    )
    rating = fields.Selection([
        ('5', '⭐⭐⭐⭐⭐ (5 Estrellas)'),
        ('4', '⭐⭐⭐⭐ (4 Estrellas)'),
        ('3', '⭐⭐⭐ (3 Estrellas)'),
        ('2', '⭐⭐ (2 Estrellas)'),
        ('1', '⭐ (1 Estrella)'),
    ], string='Calificación', default='5', required=True)

    content = fields.Text(
        string='Comentario / Reseña',
        required=True
    )
    date_display = fields.Char(
        string='Fecha Mostrada',
        default='Reciente',
        help='Texto visible en la web. Ej: Hace 3 días, Hace 1 semana, Ayer'
    )
    date_review = fields.Date(
        string='Fecha de Registro',
        default=fields.Date.context_today
    )
    is_verified_purchase = fields.Boolean(
        string='Compra Verificada',
        default=True
    )
    helpful_count = fields.Integer(
        string='Votos "Es útil"',
        default=0
    )
    state = fields.Selection([
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado y Publicado'),
        ('rejected', 'Rechazado'),
    ], string='Estado de Moderación', default='pending', required=True, index=True)

    is_published = fields.Boolean(
        string='Publicado en la Web',
        default=False,
        help='Solo se muestra en la tienda web si está marcado y aprobado.'
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )

    def get_rating_int(self):
        self.ensure_one()
        try:
            return int(self.rating)
        except Exception:
            return 5

    def action_approve(self):
        """Aprueba la reseña y la publica en la web."""
        self.write({
            'state': 'approved',
            'is_published': True,
        })

    def action_reject(self):
        """Rechaza la reseña y la retira de la web."""
        self.write({
            'state': 'rejected',
            'is_published': False,
        })

    def action_set_pending(self):
        """Pone la reseña en estado pendiente."""
        self.write({
            'state': 'pending',
            'is_published': False,
        })

    def init(self):
        super().init()
        # Auto-poblar los comentarios de ejemplo iniciales (aprobados) para los productos existentes
        try:
            products = self.env['product.template'].sudo().search([])
            for p in products:
                existing = self.sudo().search([('product_tmpl_id', '=', p.id)], limit=1)
                if not existing:
                    self.sudo().create([
                        {
                            'product_tmpl_id': p.id,
                            'author_name': 'Carlos M.',
                            'author_location': 'Huancayo',
                            'rating': '5',
                            'title': 'Excelente producto y entrega puntual',
                            'content': 'Superó mis expectativas. Llegó en perfectas condiciones, muy bien protegido y sellado en su empaque original. La atención y rapidez de entrega en Huancayo fue impecable. Muy recomendado.',
                            'date_display': 'Hace 3 días',
                            'is_verified_purchase': True,
                            'helpful_count': 14,
                            'state': 'approved',
                            'is_published': True,
                            'sequence': 10,
                        },
                        {
                            'product_tmpl_id': p.id,
                            'author_name': 'Andrea R.',
                            'author_location': 'El Tambo',
                            'rating': '5',
                            'title': '100% original y compra garantizada',
                            'content': 'La calidad es muy buena y tal como se ve en la descripción. Pagué con Yape sin problemas y me llegó la boleta directo a mi WhatsApp. Sin duda volveré a comprar en la plataforma.',
                            'date_display': 'Hace 1 semana',
                            'is_verified_purchase': True,
                            'helpful_count': 9,
                            'state': 'approved',
                            'is_published': True,
                            'sequence': 20,
                        },
                        {
                            'product_tmpl_id': p.id,
                            'author_name': 'Javier P.',
                            'author_location': 'Chilca',
                            'rating': '5',
                            'title': 'Muy buen servicio y despacho rápido',
                            'content': 'Excelente relación precio-calidad. Todo conforme con el despacho y el recojo. La tienda fue muy amable en resolver mis dudas antes de concretar la orden.',
                            'date_display': 'Hace 2 semanas',
                            'is_verified_purchase': True,
                            'helpful_count': 5,
                            'state': 'approved',
                            'is_published': True,
                            'sequence': 30,
                        },
                    ])
        except Exception:
            pass
