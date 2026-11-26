# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from calendar import monthrange


class L10nPePdt621Wizard(models.TransientModel):
    _name = 'l10n_pe.pdt621.wizard'
    _description = 'Precálculo Declara Fácil 621 (IGV / Renta MYPE)'

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True
    )
    year = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: fields.Date.context_today(self).year
    )
    month = fields.Selection([
        ('01', 'Enero'),
        ('02', 'Febrero'),
        ('03', 'Marzo'),
        ('04', 'Abril'),
        ('05', 'Mayo'),
        ('06', 'Junio'),
        ('07', 'Julio'),
        ('08', 'Agosto'),
        ('09', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], string='Mes', required=True, default=lambda self: str(fields.Date.context_today(self).month).zfill(2))

    previous_igv_credit = fields.Monetary(
        string='Saldo a Favor IGV Mes Anterior (Casilla 145)',
        default=0.0,
        currency_field='currency_id',
        help='Monto del crédito fiscal no compensado arrastrado del periodo anterior.'
    )

    state = fields.Selection([
        ('draft', 'Seleccionar Periodo'),
        ('calculated', 'Liquidación Calculada'),
    ], default='draft')

    # --- VENTAS (Casillas 100, 101, 105, 109, 112) ---
    sales_taxable = fields.Monetary(string='Ventas Gravadas (Casilla 100)', readonly=True, currency_field='currency_id')
    sales_export = fields.Monetary(string='Exportaciones (Casilla 105)', readonly=True, currency_field='currency_id')
    sales_exempt = fields.Monetary(string='Ventas Exoneradas (Casilla 109)', readonly=True, currency_field='currency_id')
    sales_unaffected = fields.Monetary(string='Ventas Inafectas (Casilla 112)', readonly=True, currency_field='currency_id')
    igv_debito = fields.Monetary(string='IGV Débito Fiscal (Casilla 101)', readonly=True, currency_field='currency_id')

    # --- COMPRAS (Casillas 107, 108, 110, 113) ---
    purchases_taxable = fields.Monetary(string='Compras Gravadas Destinadas a Vtas Gravadas (Casilla 107)', readonly=True, currency_field='currency_id')
    purchases_mixed = fields.Monetary(string='Compras Gravadas Destinadas a Vtas Mixtas - Prorrata (Casilla 110)', readonly=True, currency_field='currency_id')
    purchases_no_credit = fields.Monetary(string='Compras Sin Derecho a Crédito (Casilla 113)', readonly=True, currency_field='currency_id')
    purchases_exempt = fields.Monetary(string='Compras No Gravadas / Exoneradas', readonly=True, currency_field='currency_id')
    igv_credito = fields.Monetary(string='IGV Crédito Fiscal (Casilla 108)', readonly=True, currency_field='currency_id')

    # --- DETERMINACIÓN DE LA DEUDA IGV ---
    igv_resultante = fields.Monetary(string='Impuesto Resultante IGV (Casilla 140)', readonly=True, currency_field='currency_id')
    igv_a_pagar = fields.Monetary(string='TOTAL IGV A PAGAR (Casilla 184)', readonly=True, currency_field='currency_id')
    igv_saldo_favor_siguiente = fields.Monetary(string='Saldo a Favor para el Mes Siguiente', readonly=True, currency_field='currency_id')

    # --- IMPUESTO A LA RENTA MYPE (RMT) ---
    renta_base = fields.Monetary(string='Ingresos Netos del Mes (Casilla 301)', readonly=True, currency_field='currency_id')
    renta_tasa = fields.Float(string='Tasa Renta MYPE (Casilla 312)', default=1.0, readonly=True)
    renta_a_pagar = fields.Monetary(string='PAGO A CUENTA RENTA MYPE (Casilla 302)', readonly=True, currency_field='currency_id')

    # --- TOTAL TRIBUTOS A PAGAR ---
    total_tributos = fields.Monetary(string='TOTAL TRIBUTOS A PAGAR (IGV + Renta)', readonly=True, currency_field='currency_id')
    invoice_count_sales = fields.Integer(string='Total Comprobantes de Venta', readonly=True)
    invoice_count_purchases = fields.Integer(string='Total Comprobantes de Compra', readonly=True)

    def action_calculate_pdt(self):
        """Calcula el precálculo de impuestos para el Declara Fácil 621."""
        self.ensure_one()
        y = int(self.year)
        m = int(self.month)
        date_from = f"{y:04d}-{m:02d}-01"
        weekday, last_day = monthrange(y, m)
        date_to = f"{y:04d}-{m:02d}-{last_day:02d}"

        company = self.company_id

        # 1. Procesar Ventas
        sales_domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        sale_moves = self.env['account.move'].search(sales_domain)

        s_taxable = 0.0
        s_export = 0.0
        s_exempt = 0.0
        s_unaffected = 0.0
        s_igv = 0.0

        for move in sale_moves:
            sign = -1 if move.move_type == 'out_refund' else 1
            # Obtener tipo de cambio a PEN si la factura es en otra moneda
            rate = 1.0
            if move.currency_id != company.currency_id:
                if hasattr(move, 'exchange_rate') and move.exchange_rate:
                    rate = move.exchange_rate
                else:
                    conv = self.env['res.currency']._get_conversion_rate(
                        move.currency_id, company.currency_id, company, move.invoice_date
                    )
                    rate = 1.0 / conv if conv else 1.0

            tax_data = move._l10n_pe_sire_get_tax_breakdown() if hasattr(move, '_l10n_pe_sire_get_tax_breakdown') else {}
            s_taxable += (tax_data.get('gravado', 0.0) * rate) * sign
            s_export += (tax_data.get('export', 0.0) * rate) * sign
            s_exempt += (tax_data.get('exonerado', 0.0) * rate) * sign
            s_unaffected += (tax_data.get('inafecto', 0.0) * rate) * sign
            s_igv += (tax_data.get('igv', 0.0) * rate) * sign

        # 2. Procesar Compras
        purchases_domain = [
            ('company_id', '=', company.id),
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        purchase_moves = self.env['account.move'].search(purchases_domain)

        p_taxable = 0.0
        p_mixed = 0.0
        p_no_credit = 0.0
        p_exempt = 0.0
        p_igv = 0.0

        for move in purchase_moves:
            sign = -1 if move.move_type == 'in_refund' else 1
            rate = 1.0
            if move.currency_id != company.currency_id:
                if hasattr(move, 'exchange_rate') and move.exchange_rate:
                    rate = move.exchange_rate
                else:
                    conv = self.env['res.currency']._get_conversion_rate(
                        move.currency_id, company.currency_id, company, move.invoice_date
                    )
                    rate = 1.0 / conv if conv else 1.0

            tax_data = move._l10n_pe_sire_get_tax_breakdown() if hasattr(move, '_l10n_pe_sire_get_tax_breakdown') else {}
            credit_type = getattr(move, 'l10n_pe_sire_credit_type', '1') or '1'

            base = tax_data.get('gravado', 0.0) * rate * sign
            igv_m = tax_data.get('igv', 0.0) * rate * sign

            if credit_type == '1':
                p_taxable += base
                p_igv += igv_m
            elif credit_type == '2':
                p_mixed += base
                p_igv += igv_m  # Se computa al 100% o según coeficiente de prorrata
            elif credit_type == '3':
                p_no_credit += base
            elif credit_type == '4':
                p_exempt += base

            p_exempt += (tax_data.get('exonerado', 0.0) + tax_data.get('inafecto', 0.0)) * rate * sign

        # 3. Determinación IGV
        igv_resultante = s_igv - p_igv
        saldo_anterior = self.previous_igv_credit or 0.0

        if igv_resultante > saldo_anterior:
            igv_pagar = igv_resultante - saldo_anterior
            saldo_siguiente = 0.0
        else:
            igv_pagar = 0.0
            saldo_siguiente = max(0.0, saldo_anterior - igv_resultante)

        # 4. Renta MYPE (1.0% de los ingresos netos gravados y exportaciones)
        renta_base = max(0.0, s_taxable + s_export)
        renta_pagar = renta_base * (self.renta_tasa / 100.0)

        # 5. Total tributos
        total = igv_pagar + renta_pagar

        self.write({
            'state': 'calculated',
            'sales_taxable': round(s_taxable, 2),
            'sales_export': round(s_export, 2),
            'sales_exempt': round(s_exempt, 2),
            'sales_unaffected': round(s_unaffected, 2),
            'igv_debito': round(s_igv, 2),
            'purchases_taxable': round(p_taxable, 2),
            'purchases_mixed': round(p_mixed, 2),
            'purchases_no_credit': round(p_no_credit, 2),
            'purchases_exempt': round(p_exempt, 2),
            'igv_credito': round(p_igv, 2),
            'igv_resultante': round(igv_resultante, 2),
            'igv_a_pagar': round(igv_pagar, 2),
            'igv_saldo_favor_siguiente': round(saldo_siguiente, 2),
            'renta_base': round(renta_base, 2),
            'renta_a_pagar': round(renta_pagar, 2),
            'total_tributos': round(total, 2),
            'invoice_count_sales': len(sale_moves),
            'invoice_count_purchases': len(purchase_moves),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.pdt621.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_recalculate(self):
        self.state = 'draft'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_pe.pdt621.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
