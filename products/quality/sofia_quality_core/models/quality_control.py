# -*- coding: utf-8 -*-
"""
SOFIA Quality Core — Puntos de Control de Calidad (QCP), No Conformidades (NC) y Trazabilidad ISO 9001.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SofiaQualityCheck(models.Model):
    _name = 'sofia.quality.check'
    _description = 'Punto de Inspección y Control de Calidad'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, default=lambda self: _('Nuevo'))
    product_id = fields.Many2one('product.product', string='Material / Producto Inspeccionado', required=True, tracking=True)
    lot_name = fields.Char(string='Número de Lote / Serie', tracking=True)
    picking_id = fields.Many2one('stock.picking', string='Albarán / Guía Asociada')
    
    test_type = fields.Selection([
        ('pass_fail', 'Pasa / No Pasa (Visual)'),
        ('measure', 'Medición Cuantitativa / Tolerancia'),
        ('certificate', 'Inspección de Certificado de Calidad (3.1/3.2)'),
    ], string='Tipo de Prueba', default='pass_fail', required=True)

    measure_value = fields.Float(string='Valor Medido')
    tolerance_min = fields.Float(string='Tolerancia Mínima')
    tolerance_max = fields.Float(string='Tolerancia Máxima')

    state = fields.Selection([
        ('draft', 'Pendiente de Inspección'),
        ('passed', 'Conforme / Aprobado'),
        ('failed', 'No Conforme / Rechazado'),
    ], string='Resultado', default='draft', tracking=True)

    inspector_id = fields.Many2one('res.users', string='Inspector Responsable', default=lambda self: self.env.user)
    date_inspected = fields.Datetime(string='Fecha y Hora de Inspección')
    notes = fields.Text(string='Observaciones Técnicas de Calidad')

    def action_pass(self):
        for rec in self:
            rec.write({
                'state': 'passed',
                'date_inspected': fields.Datetime.now(),
            })

    def action_fail(self):
        for rec in self:
            rec.write({
                'state': 'failed',
                'date_inspected': fields.Datetime.now(),
            })
            # Disparar automáticamente una No Conformidad
            self.env['sofia.quality.alert'].create({
                'title': f"Rechazo en Inspección {rec.name} - {rec.product_id.display_name}",
                'quality_check_id': rec.id,
                'product_id': rec.product_id.id,
                'lot_name': rec.lot_name,
            })


class SofiaQualityAlert(models.Model):
    _name = 'sofia.quality.alert'
    _description = 'Alerta de Calidad y No Conformidad (CAPA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    title = fields.Char(string='Título de la No Conformidad', required=True, tracking=True)
    quality_check_id = fields.Many2one('sofia.quality.check', string='Inspección Origen')
    product_id = fields.Many2one('product.product', string='Producto Afectado')
    lot_name = fields.Char(string='Lote / Serie')
    
    root_cause = fields.Text(string='Análisis de Causa Raíz (5 Porqués / Ishikawa)')
    action_plan = fields.Text(string='Plan de Acción Correctiva / Preventiva (CAPA)')

    stage = fields.Selection([
        ('draft', 'Identificada'),
        ('investigation', 'En Investigación de Causa Raíz'),
        ('capa', 'Implementando Acciones CAPA'),
        ('closed', 'Cerrada & Verificada Eficaz'),
    ], string='Etapa de Gestión', default='draft', tracking=True)
