# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import random

_logger = logging.getLogger(__name__)


class WangoShipment(models.Model):
    _name = 'wango.shipment'
    _inherit = ['wango.base.mixin']
    _description = 'Guía y Despacho de Envío'
    _order = 'create_date desc'

    name = fields.Char(string='Código de Guía', required=True, copy=False, default='New')

    delivery_type = fields.Selection([
        ('store_pickup', 'Retiro en Tienda / Agente Wanka'),
        ('home_delivery', 'Entrega a Domicilio'),
        ('agency_shipping', 'Envío por Agencia')
    ], string='Tipo de Entrega', default='home_delivery')

    # Remitente y Destinatario
    sender_id = fields.Many2one('res.partner', string='Remitente', required=True, check_company=True)
    recipient_id = fields.Many2one('res.partner', string='Destinatario', required=True, check_company=True)
    recipient_dni = fields.Char(related='recipient_id.vat', string='DNI/RUC Destinatario', store=True)

    # Direcciones
    origin_address = fields.Char(string='Dirección de Origen / Despacho', required=True)
    destination_address = fields.Char(string='Dirección de Entrega')

    # Destino / Retiro
    store_branch_id = fields.Many2one('delivery.store.branch', string='Punto de Retiro / Agente Wanka')
    agency_id = fields.Many2one('wango.agency', string='Agencia')
    destination_agency_id = fields.Many2one('wango.agency', string='Agencia Destino')

    # Ubigeo
    delivery_department_id = fields.Many2one('res.country.state', string='Departamento')
    delivery_province_id = fields.Many2one('wango.province', string='Provincia')
    delivery_district_id = fields.Many2one('wango.district', string='Distrito')

    # Paquetes y Carga
    package_ids = fields.One2many('wango.package', 'shipment_id', string='Paquetes')
    total_weight = fields.Float(string='Peso Total (kg)', compute='_compute_totals', store=True)
    total_volume = fields.Float(string='Volumen Total (m3)', compute='_compute_totals', store=True)

    # Asignación de Flota / Conductor
    driver_id = fields.Many2one('wango.driver', string='Repartidor', check_company=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo', check_company=True)

    # Estado del Despacho
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('registered', 'Registrada / Lista'),
        ('picked_up', 'Recogida'),
        ('in_transit', 'En Ruta / Tránsito'),
        ('delivered', 'Entregada'),
        ('failed', 'Entrega Fallida'),
        ('cancelled', 'Cancelada')
    ], default='draft', string='Estado')

    # Cobranza
    payment_mode = fields.Selection([
        ('prepaid', 'Pagado Online'),
        ('cod', 'Pago Contraentrega')
    ], default='prepaid', string='Modo de Pago')

    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    price = fields.Monetary(string='Costo de Envío', currency_field='currency_id')

    # Seguridad: PIN Secreto de Retiro
    pickup_pin = fields.Char(string='PIN de Retiro', size=6, copy=False, help='Código secreto para entregar el paquete')
    tracking_qr_url = fields.Char(string='URL de Rastreo QR', compute='_compute_tracking_qr_url')

    # Trazabilidad / Checkpoints
    checkpoint_ids = fields.One2many('wango.shipment.checkpoint', 'shipment_id', string='Puntos de Control')

    # Evidencia de Entrega
    proof_of_delivery = fields.Image(string="Foto de Entrega")
    signature = fields.Image(string="Firma Receptor")
    delivered_to = fields.Char(string="Recibido Por")
    delivery_date = fields.Datetime(string="Fecha de Entrega")

    def _compute_tracking_qr_url(self):
        base_url = (self.env['ir.config_parameter'].sudo().search([('key', '=', 'web.base.url')], limit=1).value or 'https://tienda.sofiaerp.com')
        for rec in self:
            rec.tracking_qr_url = f"{base_url}/track/{rec.name}"

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('wango.shipment') or 'New'
        if not vals.get('pickup_pin'):
            vals['pickup_pin'] = str(random.randint(1000, 9999))
        shipment = super(WangoShipment, self).create(vals)
        shipment._add_checkpoint('Registrada en sistema de despacho', shipment.origin_address or 'Almacén')
        return shipment

    def _add_checkpoint(self, description, location=False):
        for rec in self:
            loc = location
            if not loc:
                if rec.store_branch_id:
                    loc = rec.store_branch_id.name
                elif rec.agency_id:
                    loc = rec.agency_id.name
                else:
                    loc = rec.destination_address or 'En ruta'
            self.env['wango.shipment.checkpoint'].create({
                'shipment_id': rec.id,
                'state': rec.state,
                'description': description,
                'location': loc,
                'user_id': self.env.user.id,
            })

    @api.depends('package_ids.weight', 'package_ids.volume_m3')
    def _compute_totals(self):
        for rec in self:
            rec.total_weight = sum(p.weight for p in rec.package_ids)
            rec.total_volume = sum(p.volume_m3 for p in rec.package_ids)

    def write(self, vals):
        state_before = {rec.id: rec.state for rec in self} if 'state' in vals else {}
        result = super().write(vals)

        if 'state' in vals:
            for rec in self:
                old_state = state_before.get(rec.id, '?')
                try:
                    self.env['wango.audit.log'].log_event(
                        event_name='Cambio de estado de envío: %s → %s' % (old_state, vals['state']),
                        record=rec,
                        old_value=old_state,
                        new_value=vals['state'],
                        details='Guía %s actualizada por %s' % (rec.name, self.env.user.name)
                    )
                except Exception:
                    pass

                state_labels = dict(rec._fields['state'].selection)
                rec._add_checkpoint(
                    'Estado actualizado: %s' % state_labels.get(vals['state'], vals['state'])
                )

        return result

    def action_register(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'registered'

    def action_set_in_transit(self):
        for rec in self:
            rec.write({'state': 'in_transit'})

    def action_set_ready_agency(self):
        for rec in self:
            loc = rec.store_branch_id.name if rec.store_branch_id else (rec.agency_id.name if rec.agency_id else 'Punto de Destino')
            rec._add_checkpoint('Llegó a punto de destino. ¡Listo para recojo con PIN de seguridad!', loc)

    def action_open_delivery_wizard(self):
        self.ensure_one()
        return {
            'name': 'Registrar Entrega con PIN',
            'type': 'ir.actions.act_window',
            'res_model': 'wango.delivery.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shipment_id': self.id}
        }


class WangoPackage(models.Model):
    _name = 'wango.package'
    _inherit = ['wango.base.mixin']
    _description = 'Paquete de Despacho'

    description = fields.Char(string='Descripción Contenido', required=True)
    weight = fields.Float(string='Peso (kg)', required=True, default=0.0)
    width = fields.Float(string='Ancho (cm)', default=0.0)
    height = fields.Float(string='Alto (cm)', default=0.0)
    length = fields.Float(string='Largo (cm)', default=0.0)

    volume_m3 = fields.Float(string='Volumen (m3)', compute='_compute_volume', store=True)
    shipment_id = fields.Many2one('wango.shipment', string='Guía Asociada', ondelete='cascade')

    is_fragile = fields.Boolean(string='Frágil')
    declared_value = fields.Monetary(string='Valor Declarado')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)

    @api.depends('width', 'height', 'length')
    def _compute_volume(self):
        for rec in self:
            rec.volume_m3 = (rec.width * rec.height * rec.length) / 1000000.0


class WangoShipmentCheckpoint(models.Model):
    _name = 'wango.shipment.checkpoint'
    _description = 'Punto de Control / Trazabilidad de Despacho'
    _order = 'date desc, id desc'

    shipment_id = fields.Many2one('wango.shipment', string='Guía de Envío', required=True, ondelete='cascade')
    date = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now, required=True)
    state = fields.Char(string='Estado')
    description = fields.Char(string='Evento / Descripción', required=True)
    location = fields.Char(string='Ubicación / Punto')
    user_id = fields.Many2one('res.users', string='Operador', default=lambda self: self.env.user)


class WangoDeliveryWizard(models.TransientModel):
    _name = 'wango.delivery.wizard'
    _description = 'Registrar Entrega de Paquete'

    shipment_id = fields.Many2one('wango.shipment', string='Guía de Envío', required=True)
    signature = fields.Binary(string='Firma del Receptor')
    proof_of_delivery = fields.Image(string='Foto de Entrega', max_width=1024, max_height=1024)
    delivered_to = fields.Char(string='Recibido Por (Nombre Completo y DNI)', required=True)
    notes = fields.Text(string='Notas / Observaciones')

    def action_confirm_delivery(self):
        self.ensure_one()
        self.shipment_id.write({
            'state': 'delivered',
            'signature': self.signature,
            'proof_of_delivery': self.proof_of_delivery,
            'delivered_to': self.delivered_to,
            'delivery_date': fields.Datetime.now()
        })
        return {'type': 'ir.actions.act_window_close'}
