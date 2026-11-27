# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta

class WangoClaim(models.Model):
    _name = 'wango.claim'
    _description = 'Hoja del Libro de Reclamaciones (INDECOPI)'
    _order = 'id desc'

    name = fields.Char(string='Nº Hoja de Reclamación', required=True, copy=False, readonly=True, default=lambda self: _('Nuevo'))
    date = fields.Datetime(string='Fecha y Hora de Registro', default=fields.Datetime.now, readonly=True)
    deadline_date = fields.Date(string='Fecha Límite Legal (15 días hábiles)', compute='_compute_deadline_date', store=True)

    # 1. Identificación del Consumidor Reclamante
    consumer_name = fields.Char(string='Nombre Completo', required=True)
    doc_type = fields.Selection([
        ('dni', 'DNI'),
        ('ce', 'Carné de Extranjería'),
        ('passport', 'Pasaporte'),
        ('ruc', 'RUC')
    ], string='Tipo de Documento', default='dni', required=True)
    doc_number = fields.Char(string='Número de Documento', required=True)
    consumer_email = fields.Char(string='Correo Electrónico', required=True)
    consumer_phone = fields.Char(string='Teléfono / Celular', required=True)
    consumer_address = fields.Char(string='Domicilio', required=True)
    is_minor = fields.Boolean(string='¿Es menor de edad?', default=False)
    parent_name = fields.Char(string='Nombre del Padre / Madre o Apoderado')

    # 2. Identificación del Bien Contratado
    contracted_good = fields.Selection([
        ('product', 'Producto'),
        ('service', 'Servicio')
    ], string='Tipo de Bien', default='product', required=True)
    claimed_amount = fields.Float(string='Monto Reclamado (S/)', default=0.0)
    order_ref = fields.Char(string='Nº de Pedido / Orden (Opcional)')
    good_description = fields.Text(string='Descripción del Producto o Servicio', required=True)

    # 3. Detalle de la Reclamación
    claim_type = fields.Selection([
        ('claim', 'Reclamo (Disconformidad con el producto o servicio)'),
        ('complaint', 'Queja (Malestar respecto a la atención al cliente)')
    ], string='Tipo de Registro', default='claim', required=True)
    detail = fields.Text(string='Detalle del Reclamo / Queja', required=True)
    consumer_request = fields.Text(string='Pedido Concreto del Consumidor', required=True)

    # 4. Estado y Acciones del Proveedor (Mercado Wanka)
    state = fields.Selection([
        ('draft', 'Registrado'),
        ('in_process', 'En Investigación'),
        ('responded', 'Respondido'),
        ('closed', 'Cerrado')
    ], string='Estado', default='draft', tracking=True)
    response = fields.Text(string='Respuesta Oficial al Consumidor')
    response_date = fields.Datetime(string='Fecha de Respuesta')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            seq = self.env['ir.sequence'].next_by_code('wango.claim') or _('Nuevo')
            vals['name'] = seq
        return super(WangoClaim, self).create(vals)

    @api.depends('date')
    def _compute_deadline_date(self):
        for rec in self:
            if rec.date:
                # Estándar INDECOPI: plazo de 15 días hábiles aprox 21 días calendario
                rec.deadline_date = rec.date.date() + timedelta(days=21)
            else:
                rec.deadline_date = False

    def action_start_process(self):
        self.write({'state': 'in_process'})

    def action_send_response(self):
        self.write({
            'state': 'responded',
            'response_date': fields.Datetime.now()
        })
        # Si hay correo, enviar notificación al consumidor
        if self.consumer_email and self.response:
            body = f"""
            <h3>Respuesta a su Hoja de Reclamación: {self.name}</h3>
            <p>Estimado(a) <b>{self.consumer_name}</b>,</p>
            <p>En atención a su Hoja de Reclamación registrada el {self.date.strftime('%d/%m/%Y')}, Mercado Wanka le informa lo siguiente:</p>
            <div style="background:#f8f9fa;padding:15px;border-left:4px solid #00a650;margin:15px 0;">
                <p><b>Respuesta del Proveedor:</b></p>
                <p>{self.response}</p>
            </div>
            <p>Agradecemos su comunicación para seguir mejorando nuestro servicio.</p>
            <p><b>Mercado Wanka</b></p>
            """
            self.env['mail.mail'].sudo().create({
                'subject': f'Respuesta a Hoja de Reclamación {self.name} - Mercado Wanka',
                'body_html': body,
                'email_to': self.consumer_email,
            }).send()

    def action_close(self):
        self.write({'state': 'closed'})
