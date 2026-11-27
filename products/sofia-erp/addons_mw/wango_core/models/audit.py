from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class WangoAuditLog(models.Model):
    _name = 'wango.audit.log'
    _inherit = ['wango.base.mixin']
    _description = 'Log de Auditoría WanGO'
    _order = 'create_date desc'

    name = fields.Char(string='Evento', required=True)
    model_name = fields.Char(string='Modelo Afectado')
    res_id = fields.Integer(string='ID Registro')
    res_name = fields.Char(string='Nombre Registro')

    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user)

    old_value = fields.Text(string='Valor Anterior')
    new_value = fields.Text(string='Valor Nuevo')

    details = fields.Text(string='Detalles Técnicos')
    ip_address = fields.Char(string='Dirección IP')

    @api.model
    def log_event(self, event_name, record, old_value=None, new_value=None, details=None):
        """
        Método helper para registrar eventos de auditoría de forma cómoda.

        Uso:
            self.env['wango.audit.log'].log_event(
                'Cambio de estado',
                record=self,
                old_value='draft',
                new_value='confirmed'
            )

        :param str event_name: Descripción del evento
        :param record: Recordset del modelo afectado
        :param old_value: Valor anterior (string)
        :param new_value: Nuevo valor (string)
        :param str details: Información técnica adicional
        """
        try:
            # Intentar obtener IP del request actual (si estamos en contexto HTTP)
            ip_address = None
            try:
                from odoo.http import request as http_request
                if http_request and http_request.httprequest:
                    ip_address = http_request.httprequest.remote_addr
            except RuntimeError:
                pass  # No hay request HTTP activo (ej. cron jobs)

            self.sudo().create({
                'name': event_name,
                'model_name': record._name,
                'res_id': record.id,
                'res_name': record.display_name if hasattr(record, 'display_name') else str(record.id),
                'user_id': self.env.user.id,
                'old_value': str(old_value) if old_value is not None else False,
                'new_value': str(new_value) if new_value is not None else False,
                'details': details,
                'ip_address': ip_address,
            })
        except Exception as e:
            # El log de auditoría nunca debe bloquear la operación principal
            _logger.error("WanGO Audit: Error al registrar evento '%s': %s", event_name, str(e))
