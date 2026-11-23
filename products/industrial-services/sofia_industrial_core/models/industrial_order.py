# -*- coding: utf-8 -*-
"""
SOFIA Industrial Services — Modelo de Órdenes de Trabajo y Mantenimiento Industrial
Conforme a normas ISO 14224 y gestión de cuadrillas.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SofiaIndustrialOrder(models.Model):
    _name = 'sofia.industrial.order'
    _description = 'Orden de Servicio y Mantenimiento Industrial'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_scheduled desc, id desc'

    name = fields.Char(
        string='Código de Orden',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
    )
    title = fields.Char(string='Título / Resumen del Servicio', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente / Planta', required=True, tracking=True)
    
    order_type = fields.Selection([
        ('preventive', 'Mantenimiento Preventivo'),
        ('corrective', 'Mantenimiento Correctivo / Emergencia'),
        ('predictive', 'Monitoreo Predictivo / Vibraciones'),
        ('field_service', 'Servicio Técnico en Campo (FSM)'),
        ('calibration', 'Calibración & Protocolos'),
    ], string='Tipo de Servicio', default='corrective', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Normal'),
        ('2', 'Alta (Urgente)'),
        ('3', 'Crítica / Parada de Planta'),
    ], string='Prioridad / Criticidad', default='1', tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('triage', 'En Triage / Evaluación'),
        ('scheduled', 'Programada / Cuadrilla Asignada'),
        ('in_progress', 'En Ejecución en Sitio'),
        ('completed', 'Finalizada / Pendiente de Firma'),
        ('closed', 'Cerrada & Conformidad'),
        ('cancel', 'Cancelada'),
    ], string='Estado', default='draft', tracking=True)

    date_scheduled = fields.Datetime(string='Fecha y Hora Programada', tracking=True)
    date_execution_start = fields.Datetime(string='Inicio Real de Labores')
    date_execution_end = fields.Datetime(string='Término Real de Labores')

    # Recursos Humanos & Cuadrilla
    lead_technician_id = fields.Many2one('hr.employee', string='Supervisor / Técnico Líder', tracking=True)
    assigned_crew_ids = fields.Many2many('hr.employee', string='Cuadrilla Técnica Asignada')

    # Equipos y Taxonomía ISO 14224
    asset_tag = fields.Char(string='Tag del Activo / Equipo', help='Identificador físico del equipo en planta')
    failure_mode = fields.Char(string='Modo de Falla (ISO 14224)', help='Clasificación estandarizada del fallo detectado')

    # Costos & Horas
    estimated_hours = fields.Float(string='Horas-Hombre Estimadas', default=1.0)
    actual_hours = fields.Float(string='Horas-Hombre Reales')
    estimated_cost = fields.Monetary(string='Costo Estimado')
    actual_cost = fields.Monetary(string='Costo Real Ejecutado')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)

    # Documentación & Conformidad
    hse_approved = fields.Boolean(string='Permiso de Trabajo Seguro (ATS/LOTO) Aprobado', tracking=True)
    signature = fields.Binary(string='Firma Digital del Cliente', copy=False)
    signed_by = fields.Char(string='Nombre de Quien Firma la Conformidad')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sofia.industrial.order') or _('OT-NUEVA')
        return super(SofiaIndustrialOrder, self).create(vals_list)

    def action_start_service(self):
        """Inicia el servicio en sitio tras verificar permisos HSE."""
        for rec in self:
            if not rec.hse_approved and rec.order_type in ('corrective', 'field_service'):
                raise UserError(_("No puede iniciar la orden sin la aprobación del Análisis de Trabajo Seguro (ATS)."))
            rec.write({
                'state': 'in_progress',
                'date_execution_start': fields.Datetime.now(),
            })

    def action_complete_service(self):
        """Marca el servicio como completado a la espera de firma del cliente."""
        for rec in self:
            rec.write({
                'state': 'completed',
                'date_execution_end': fields.Datetime.now(),
            })
