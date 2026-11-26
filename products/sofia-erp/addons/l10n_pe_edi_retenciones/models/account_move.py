# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    pe_is_retention = fields.Boolean(
        string='Aplicar Retención IGV',
        copy=False,
        help='Marcar si esta factura está sujeta al Régimen de Retenciones del IGV (3% para clientes Agentes de Retención).'
    )
    pe_retention_percent = fields.Float(
        string='% Retención IGV',
        default=3.0,
        copy=False,
        help='Porcentaje de retención del IGV (3.0% tasa vigente SUNAT).'
    )
    pe_retention_percent_dec = fields.Float(
        string='Factor de Retención',
        store=True,
        compute='_compute_pe_retention_amounts',
        digits=(16, 5),
        copy=False,
    )
    pe_retention_base_amount = fields.Monetary(
        string='Base Imponible Retención',
        store=True,
        compute='_compute_pe_retention_amounts',
        currency_field='currency_id',
        copy=False,
    )
    pe_retention_amount = fields.Monetary(
        string='Monto Retenido IGV',
        store=True,
        compute='_compute_pe_retention_amounts',
        currency_field='currency_id',
        copy=False,
    )
    pe_retention_amount_net = fields.Monetary(
        string='Neto a Pagar (sin Retención)',
        store=True,
        compute='_compute_pe_retention_amounts',
        currency_field='currency_id',
        copy=False,
    )
    pe_retention_below_threshold = fields.Boolean(
        string='Bajo umbral legal S/ 700',
        compute='_compute_pe_retention_amounts',
        help='Indica que el monto total no supera los S/ 700.00 exigidos por la R.S. 037-2002/SUNAT.'
    )

    @api.onchange('partner_id')
    def _onchange_partner_retention(self):
        """Autocompleta la retención cuando el cliente es Agente de Retención SUNAT."""
        if self.move_type != 'out_invoice':
            return
        partner = self.commercial_partner_id or self.partner_id
        if partner and (partner.pe_is_retention or getattr(partner, 'is_retention_agent', False)):
            # Si la operación ya tiene detracción (1001-1004), no activar retención (exclusión mutua SUNAT)
            if self.l10n_pe_edi_operation_type in ('1001', '1002', '1003', '1004'):
                self.pe_is_retention = False
            else:
                self.pe_is_retention = True
                self.pe_retention_percent = partner.pe_retention_percent or 3.0
        else:
            self.pe_is_retention = False

    @api.onchange('l10n_pe_edi_operation_type')
    def _onchange_operation_type_retention(self):
        """Desactiva retención automáticamente si se selecciona una operación sujeta a detracción (SPOT)."""
        if self.l10n_pe_edi_operation_type in ('1001', '1002', '1003', '1004') and self.pe_is_retention:
            self.pe_is_retention = False

    def _l10n_pe_edi_get_retention_amount_in_pen(self):
        """Convierte el importe total de la factura a Soles (PEN) para comparar contra el umbral de S/ 700.00."""
        self.ensure_one()
        pen_currency = self.env.ref('base.PEN', raise_if_not_found=False)
        total = abs(self.amount_total)
        if not pen_currency or self.currency_id == pen_currency:
            return total
        return abs(self.currency_id._convert(
            total,
            pen_currency,
            self.company_id,
            self.invoice_date or fields.Date.context_today(self),
        ))

    @api.depends(
        'pe_is_retention',
        'pe_retention_percent',
        'amount_total',
        'currency_id',
        'invoice_date',
        'l10n_pe_edi_operation_type',
        'move_type',
        'l10n_latam_document_type_id',
    )
    def _compute_pe_retention_amounts(self):
        for move in self:
            move.pe_retention_below_threshold = False
            if move.pe_is_retention and move.move_type == 'out_invoice' and move.pe_retention_percent > 0:
                total_pen = move._l10n_pe_edi_get_retention_amount_in_pen()
                if total_pen <= 700.0:
                    move.pe_retention_below_threshold = True
                    move.pe_retention_base_amount = 0.0
                    move.pe_retention_amount = 0.0
                    move.pe_retention_percent_dec = 0.0
                    move.pe_retention_amount_net = move.amount_total
                    continue

                base = abs(move.amount_total)
                factor = move.pe_retention_percent / 100.0
                ret_amount = move.currency_id.round(base * factor)
                move.pe_retention_base_amount = base
                move.pe_retention_percent_dec = factor
                move.pe_retention_amount = ret_amount
                move.pe_retention_amount_net = move.currency_id.round(base - ret_amount)
            else:
                move.pe_retention_base_amount = 0.0
                move.pe_retention_amount = 0.0
                move.pe_retention_percent_dec = 0.0
                move.pe_retention_amount_net = move.amount_total

    @api.constrains('state', 'pe_is_retention', 'l10n_pe_edi_operation_type', 'l10n_latam_document_type_id')
    def _check_pe_retention_rules(self):
        """Valida las reglas normativas SUNAT al confirmar la factura con retención."""
        for move in self:
            if move.state == 'posted' and move.pe_is_retention and move.move_type == 'out_invoice':
                # 1. Exclusión mutua con Detracción (R.S. 037-2002 Art. 5 inc. f)
                if move.l10n_pe_edi_operation_type in ('1001', '1002', '1003', '1004') and move._l10n_pe_edi_get_spot():
                    raise ValidationError(_(
                        "Según la normativa SUNAT (R.S. 037-2002), una factura no puede estar sujeta "
                        "simultáneamente a Detracción (SPOT) y Retención del IGV. Desactive una de las dos."
                    ))
                # 2. Porcentaje válido
                if move.pe_retention_percent <= 0 or move.pe_retention_percent >= 100:
                    raise ValidationError(_("El porcentaje de retención del IGV debe ser mayor a 0% y menor a 100% (tasa SUNAT: 3%)."))

    def _l10n_pe_edi_get_retention(self):
        """Retorna el diccionario oficial de Retención del IGV para el XML UBL 2.1 y reportes.
        Cumple estrictamente con la R.S. 037-2002/SUNAT:
        - Solo aplica a Facturas de venta (Código 01 / out_invoice).
        - Importe total debe superar los S/ 700.00 (al TC oficial si es USD).
        - Excluyente con Detracción (SPOT).
        - Debe tener IGV gravado (no aplica a operaciones 100% exoneradas o inafectas).
        """
        self.ensure_one()

        if not self.pe_is_retention or self.move_type != 'out_invoice':
            return {}

        # Solo aplica a Factura (01), no a Boleta (03) ni Notas
        doc_code = self.l10n_latam_document_type_id.code if self.l10n_latam_document_type_id else '01'
        if doc_code not in ('01', '1'):
            return {}

        # Exclusión mutua con SPOT (Detracción)
        if self._l10n_pe_edi_get_spot():
            return {}

        # Validar tasa
        if not self.pe_retention_percent or self.pe_retention_percent <= 0:
            return {}

        # Validar umbral legal de S/ 700.00
        total_pen = self._l10n_pe_edi_get_retention_amount_in_pen()
        if total_pen <= 700.0:
            return {}

        # Validar que la factura tenga IGV (operación gravada)
        if self.currency_id.is_zero(self.amount_tax):
            return {}

        base_amount = abs(self.amount_total)
        factor = self.pe_retention_percent / 100.0
        retention_amount = self.currency_id.round(base_amount * factor)
        net_amount = self.currency_id.round(base_amount - retention_amount)

        return {
            'code': '62',
            'percent': self.pe_retention_percent,
            'factor': factor,
            'base_amount': base_amount,
            'amount': retention_amount,
            'net_amount': net_amount,
            'currency': self.currency_id,
            'message': _(
                "Operación sujeta a Retención del I.G.V. (%(percent)s%%)",
                percent=self.pe_retention_percent,
            ),
        }
