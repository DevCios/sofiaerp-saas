# -*- coding: utf-8 -*-
from odoo import models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _is_peruvian_national_bank_account(self):
        self.ensure_one()
        # 1. Comprobación estándar de Odoo (BIC BANCPEPL y código de compensación 18)
        is_standard = super()._is_peruvian_national_bank_account()
        if is_standard:
            return True

        # 2. Resiliencia: si el nombre del banco o el titular hace referencia al Banco de la Nación / Detracciones
        bank_name = (self.bank_id.name or '').upper()
        holder_name = (self.acc_holder_name or '').upper()

        if 'NACION' in bank_name or 'DETRACCION' in bank_name or 'DETRACCION' in holder_name or 'NACION' in holder_name:
            return True

        clearing = self._get_clearing_number('PE') if hasattr(self, '_get_clearing_number') else False
        if clearing == '18':
            return True

        return False
