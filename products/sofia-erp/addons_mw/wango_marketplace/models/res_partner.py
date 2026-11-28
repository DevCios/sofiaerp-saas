# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_marketplace_seller = fields.Boolean(string="Es Vendedor del Marketplace", default=False)
    
    marketplace_seller_status = fields.Selection([
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado')
    ], string="Estado de Vendedor", default='pending', tracking=True)

    marketplace_delivery_carrier_id = fields.Many2one(
        'delivery.carrier', 
        string="Método de Envío por Defecto",
        help="El método de envío que se aplicará a los productos de este vendedor en el checkout."
    )

    seller_rating_avg = fields.Float(
        string="Calificación de la Tienda (1.0 - 5.0)",
        default=0.0,
        digits=(3, 1),
        help="Calificación promedio de la tienda para mostrar estrellas."
    )
    seller_rating_count = fields.Integer(
        string="Opiniones / Compradores Satisfechos",
        default=0,
        help="Número total de compradores que calificaron la tienda."
    )
    seller_sales_completed = fields.Integer(
        string="Ventas Concretadas",
        default=0,
        help="Número total de ventas concretadas por este vendedor."
    )
    seller_is_official_store = fields.Boolean(
        string="Tienda Oficial / Mercado Wanka Líder",
        default=False,
        help="Muestra la medalla de Tienda Oficial con verificación."
    )
    seller_on_time_delivery_pct = fields.Integer(
        string="% Despacho a Tiempo",
        default=0,
        help="Porcentaje de envíos entregados a tiempo."
    )
    seller_good_service_pct = fields.Integer(
        string="% Buena Atención",
        default=0,
        help="Porcentaje de satisfacción en atención al cliente."
    )

    # Integración Ecosistema SOFIA ERP (Hub & Spoke)
    sofia_tenant_slug = fields.Char(
        string="Slug Tenant SOFIA ERP",
        index=True,
        help="Subdominio/slug del tenant en SOFIA ERP (ej. miempresa).",
    )
    sofia_tenant_url = fields.Char(
        string="URL ERP del Vendedor",
        help="URL base del ERP del vendedor para envío de pedidos pagados (ej. https://miempresa.sofiaerp.com).",
    )
    sofia_seller_token = fields.Char(
        string="Token API Tienda",
        copy=False,
        help="Token interno para autenticar sincronizaciones entre el tenant SOFIA ERP y Mercado Wanka.",
    )
    sofia_subscription_active = fields.Boolean(
        string="Suscripción SOFIA Activa",
        default=True,
        help="Si se desactiva (plan vencido/suspendido), los productos de esta tienda se ocultan automáticamente.",
    )
    marketplace_custom_commission_rate = fields.Float(
        string="Comisión Personalizada Vendedor (%)",
        default=0.0,
        help="Si es mayor a 0, sobrescribe la comisión por categoría para este vendedor.",
    )

    # KYC y Datos Bancarios para Liquidación de Ventas
    seller_kyc_verified = fields.Boolean(
        string="KYC / RUC Verificado en SUNAT",
        default=False,
        help="Confirma que el RUC está ACTIVO/HABIDO en SUNAT y la cuenta bancaria corresponde al titular.",
    )
    seller_bank_name = fields.Selection([
        ('bcp', 'BCP — Banco de Crédito del Perú'),
        ('bbva', 'BBVA Perú'),
        ('interbank', 'Interbank'),
        ('scotiabank', 'Scotiabank'),
        ('banbif', 'BanBif'),
        ('yape_plin', 'Yape / Plin Empresarial'),
    ], string="Banco para Liquidaciones")
    seller_bank_account = fields.Char(string="Número de Cuenta (Soles)")
    seller_bank_cci = fields.Char(string="Código de Cuenta Interbancario (CCI - 20 dígitos)", size=20)

    def get_seller_stars_list(self):
        """Retorna lista de 5 estados ('full', 'half', 'empty') para la tienda."""
        self.ensure_one()
        score = self.seller_rating_avg or 4.9
        stars = []
        for i in range(1, 6):
            if score >= i:
                stars.append('full')
            elif score >= i - 0.7:
                stars.append('half')
            else:
                stars.append('empty')
        return stars

    def action_approve_seller(self):
        for rec in self:
            rec.marketplace_seller_status = 'approved'

    def action_reject_seller(self):
        for rec in self:
            rec.marketplace_seller_status = 'rejected'

    def write(self, vals):
        bank_fields = {'seller_bank_name', 'seller_bank_account', 'seller_bank_cci'}
        tracked = bank_fields.intersection(vals.keys())
        snapshots = {}
        if tracked:
            for rec in self:
                snapshots[rec.id] = f"{rec.seller_bank_name or '-'} / {rec.seller_bank_account or '-'} / CCI:{rec.seller_bank_cci or '-'}"
        res = super().write(vals)
        if tracked:
            Audit = self.env['mw.bank.audit'].sudo()
            for rec in self:
                new_info = f"{rec.seller_bank_name or '-'} / {rec.seller_bank_account or '-'} / CCI:{rec.seller_bank_cci or '-'}"
                if new_info != snapshots.get(rec.id):
                    Audit.create({
                        'seller_id': rec.id,
                        'old_bank_info': snapshots.get(rec.id),
                        'new_bank_info': new_info,
                        'note': f"Campos modificados: {', '.join(sorted(tracked))}",
                    })
        return res
