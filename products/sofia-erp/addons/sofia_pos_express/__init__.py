# -*- coding: utf-8 -*-
from . import models
from . import controllers


def post_init_create_yape_plin(env):
    """Crea diarios contables Yape y Plin (uso POS Express y Facturación; nunca compras web)."""
    for company in env['res.company'].sudo().search([]):
        env['pos.express.config'].sudo().ensure_peru_digital_wallets(company)

