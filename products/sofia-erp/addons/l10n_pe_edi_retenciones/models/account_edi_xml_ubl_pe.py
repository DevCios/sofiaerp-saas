# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLPE(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_pe'

    def _add_invoice_header_nodes(self, document_node, vals):
        """Agrega la leyenda legal de Retención del IGV en <cbc:Note> cuando aplica."""
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        if vals.get('document_type') == 'invoice' and invoice._l10n_pe_edi_get_retention():
            notes = document_node.get('cbc:Note')
            if not isinstance(notes, list):
                notes = [notes] if notes else []
            notes.append({
                '_text': 'Sujeto a Retención del I.G.V.',
            })
            document_node['cbc:Note'] = notes

    def _get_document_withholding_node(self, vals):
        """Genera el nodo <cac:AllowanceCharge> con código 62 (Retención del IGV)
        según Catálogo 53 de SUNAT UBL 2.1.
        Respeta primero el cálculo nativo por línea de impuesto si existiera."""
        withholding_node = super()._get_document_withholding_node(vals)
        if withholding_node:
            return withholding_node

        invoice = vals['invoice']
        if vals.get('document_type') != 'invoice':
            return {}

        retention = invoice._l10n_pe_edi_get_retention()
        if not retention:
            return {}

        return {
            'cbc:ChargeIndicator': {'_text': 'false'},
            'cbc:AllowanceChargeReasonCode': {'_text': retention['code']},
            'cbc:MultiplierFactorNumeric': {'_text': self.format_float(retention['factor'], 5)},
            'cbc:Amount': {
                '_text': self.format_float(retention['amount'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:BaseAmount': {
                '_text': self.format_float(retention['base_amount'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        """Ajusta el Monto Neto Pendiente de Pago (FormaPago=Credito) y las Cuotas (Cuota001..N)
        descontando la Retención del IGV conforme a la R.S. 193-2020/SUNAT.
        Garantiza que la suma de las cuotas cuadre al céntimo exacto (evita errores SUNAT 3267/3273)."""
        super()._add_invoice_payment_terms_nodes(document_node, vals)

        invoice = vals['invoice']
        if invoice.is_refund():
            return

        retention = invoice._l10n_pe_edi_get_retention()
        if not retention:
            return

        payment_means_id = invoice._l10n_pe_edi_get_payment_means()
        if payment_means_id == 'Contado':
            return

        payment_terms = document_node.get('cac:PaymentTerms') or []
        if not payment_terms:
            return

        currency = invoice.currency_id
        dp = currency.decimal_places
        ret_amount = retention['amount']
        ret_factor = retention['factor']

        credit_node = None
        cuota_nodes = []
        for term in payment_terms:
            term_id = (term.get('cbc:ID') or {}).get('_text')
            means_id = (term.get('cbc:PaymentMeansID') or {}).get('_text', '')
            if term_id == 'FormaPago':
                if means_id == 'Credito':
                    credit_node = term
                elif means_id.startswith('Cuota'):
                    cuota_nodes.append(term)

        if not credit_node or not credit_node.get('cbc:Amount'):
            return

        # 1. Calcular el nuevo Monto Neto Pendiente de Pago (Total - Retención)
        original_credit_total = float(credit_node['cbc:Amount']['_text'])
        net_credit_total = currency.round(max(0.0, original_credit_total - ret_amount))
        credit_node['cbc:Amount']['_text'] = self.format_float(net_credit_total, dp)

        # 2. Prorratear la retención en cada cuota y ajustar el último céntimo por redondeo
        if cuota_nodes:
            running_sum = 0.0
            last_idx = len(cuota_nodes) - 1
            for idx, c_node in enumerate(cuota_nodes):
                orig_cuota = float(c_node['cbc:Amount']['_text'])
                if idx < last_idx:
                    net_cuota = currency.round(orig_cuota * (1.0 - ret_factor))
                    running_sum = currency.round(running_sum + net_cuota)
                else:
                    net_cuota = currency.round(max(0.0, net_credit_total - running_sum))
                c_node['cbc:Amount']['_text'] = self.format_float(net_cuota, dp)
