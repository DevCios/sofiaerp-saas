# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_pe_ple_get_cuo(self):
        """Devuelve el Código Único de Operación (CUO) para PLE."""
        self.ensure_one()
        # En SUNAT el CUO identifica de manera unívoca al asiento contable
        return str(self.id)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_pe_ple_clean_text(self, text, max_len=200):
        """Limpia caracteres especiales (pipes, saltos de línea) para archivos PLE."""
        if not text:
            return ''
        clean = str(text).replace('|', '/').replace('\r', '').replace('\n', ' ').strip()
        return clean[:max_len]
