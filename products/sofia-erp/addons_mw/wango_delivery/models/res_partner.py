# -*- coding: utf-8 -*-
from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('vat', 'country_id')
    def check_vat(self):
        """
        Sobrescribe la restricción estricta de base_vat para permitir DNIs peruanos (8 dígitos)
        en compradores de Marketplace cuando solicitan Boleta de Venta.
        Por defecto Odoo espera un RUC de 11 dígitos que comience con 10 o 20.
        """
        non_dni_partners = self.env['res.partner']
        for partner in self:
            vat = partner.vat
            if vat:
                vat_clean = vat.strip().replace(' ', '').replace('-', '')
                # Si es un DNI peruano válido (8 dígitos numéricos), omitir validación de RUC
                if len(vat_clean) == 8 and vat_clean.isdigit():
                    continue
            non_dni_partners |= partner
        
        if non_dni_partners and hasattr(super(ResPartner, non_dni_partners), 'check_vat'):
            return super(ResPartner, non_dni_partners).check_vat()
        return True

