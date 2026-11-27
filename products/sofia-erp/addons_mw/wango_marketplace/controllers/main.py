# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

class MarketplaceWebsiteSale(WebsiteSale):
    
    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        """ 
        Interceptamos la búsqueda de la tienda de Odoo para inyectar 
        nuestro filtro por vendedor si viene en la URL (?seller_id=X)
        """
        domain = super(MarketplaceWebsiteSale, self)._get_search_domain(
            search, category, attrib_values, search_in_description
        )
        
        seller_id = request.params.get('seller_id')
        if seller_id:
            try:
                # Validar que sea un número entero seguro
                seller_id_int = int(seller_id)
                domain.append(('marketplace_seller_id', '=', seller_id_int))
            except ValueError:
                pass
                
        return domain
