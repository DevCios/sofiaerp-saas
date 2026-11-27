# -*- coding: utf-8 -*-

from odoo import models, fields, api

class WangoDeliveryDashboard(models.TransientModel):
    _name = 'delivery.dashboard'
    _description = 'Tablero Logístico de Entregas'

    kpi_pickup_count = fields.Integer(string='Recojos en Tienda Pendientes', compute='_compute_kpis')
    kpi_delivery_count = fields.Integer(string='Deliverys a Domicilio Pendientes', compute='_compute_kpis')
    kpi_agency_count = fields.Integer(string='Envíos por Agencia Pendientes', compute='_compute_kpis')
    kpi_total_cost = fields.Float(string='Costos Logísticos Recaudados (S/)', compute='_compute_kpis')
    kpi_average_time = fields.Float(string='Plazo Promedio de Entrega (días)', compute='_compute_kpis')

    def _compute_kpis(self):
        for rec in self:
            # Pendientes: pedidos confirmados en estado 'sale'
            rec.kpi_pickup_count = self.env['sale.order'].sudo().search_count([
                ('delivery_type', '=', 'store_pickup'),
                ('state', '=', 'sale')
            ])
            rec.kpi_delivery_count = self.env['sale.order'].sudo().search_count([
                ('delivery_type', '=', 'home_delivery'),
                ('state', '=', 'sale')
            ])
            rec.kpi_agency_count = self.env['sale.order'].sudo().search_count([
                ('delivery_type', '=', 'agency_shipping'),
                ('state', '=', 'sale')
            ])
            
            # Costos totales sumando los fletes facturados
            orders = self.env['sale.order'].sudo().search([('state', 'in', ['sale', 'done'])])
            rec.kpi_total_cost = sum(orders.mapped('shipping_cost'))
            
            # Promedio de tiempos estimados configurados
            coverages = self.env['delivery.coverage'].sudo().search([('active', '=', True)])
            rec.kpi_average_time = sum(coverages.mapped('time_max')) / len(coverages) if coverages else 1.5

    @api.model
    def action_open_dashboard(self):
        """Crea el registro del dashboard al abrir y redirige a la vista formulario."""
        record = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tablero Logístico',
            'res_model': 'delivery.dashboard',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }
