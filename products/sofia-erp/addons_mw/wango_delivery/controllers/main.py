# -*- coding: utf-8 -*-

from odoo import http, _, fields
from odoo.http import request
import base64
from datetime import timedelta


class WangoDeliveryController(http.Controller):

    def _get_order_origin_dept_id(self, order):
        """Determina el departamento de origen para un pedido completo."""
        first_line = next((line for line in order.order_line if not line.is_delivery and line.product_id), None)
        if first_line:
            product = first_line.product_id
            if product.wango_origin_department_id:
                return product.wango_origin_department_id.id
            elif getattr(product, 'marketplace_seller_id', False) and product.marketplace_seller_id.state_id:
                return product.marketplace_seller_id.state_id.id
            elif getattr(product, 'seller_id', False) and getattr(product.seller_id, 'partner_id', False) and product.seller_id.partner_id.state_id:
                return product.seller_id.partner_id.state_id.id
            elif product.company_id and product.company_id.partner_id.state_id:
                return product.company_id.partner_id.state_id.id
        
        # Fallback a compañía o Lima
        if order.company_id and order.company_id.partner_id.state_id:
            return order.company_id.partner_id.state_id.id
        
        lima = request.env['res.country.state'].sudo().search([('code', '=', 'LIMA'), ('country_id.code', '=', 'PE')], limit=1)
        if not lima:
            lima = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'PE')], limit=1)
        return lima.id if lima else False

    def _get_home_delivery_coverage_and_cost(self, district_id, origin_dept_id):
        """Calcula la cobertura y costo final sumando el recargo interprovincial si aplica, soportando cobertura jerárquica."""
        env = request.env
        district = env['wango.district'].sudo().browse(int(district_id))
        
        debug_lines = []
        debug_lines.append("--- _get_home_delivery_coverage_and_cost START ---")
        debug_lines.append("district_id: %s (exists: %s)" % (district_id, district.exists()))
        debug_lines.append("origin_dept_id: %s" % origin_dept_id)

        if not district.exists():
            try:
                with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                    f.write("\n".join(debug_lines) + "\n")
            except Exception:
                pass
            return False, 0.0

        dest_dept_id = district.province_id.state_id.id if district.province_id and district.province_id.state_id else False
        debug_lines.append("dest_dept_id: %s" % dest_dept_id)

        # Obtener todas las reglas de cobertura activas para el departamento de destino
        all_coverages = env['delivery.coverage'].sudo().search([
            ('department_id', '=', dest_dept_id),
            ('active', '=', True)
        ])
        
        # Filtrar solo las reglas que correspondan a la ubicación (jerárquicamente: Distrito > Provincia > Departamento)
        valid_coverages = []
        for cov in all_coverages:
            if cov.district_id and cov.district_id.id == district.id:
                valid_coverages.append(cov)
            elif not cov.district_id and cov.province_id and cov.province_id.id == district.province_id.id:
                # Si el distrito está marcado en la lista de exclusión de esta regla provincial, se ignora
                if cov.excluded_district_ids and district.id in cov.excluded_district_ids.ids:
                    debug_lines.append("Distrito %s excluido expresamente en cobertura provincial ID %s" % (district.name, cov.id))
                    continue
                valid_coverages.append(cov)
            elif not cov.district_id and not cov.province_id and cov.department_id and cov.department_id.id == dest_dept_id:
                valid_coverages.append(cov)
                
        # Ordenar por especificidad descendente (Distrito > Provincia > Departamento)
        valid_coverages.sort(key=lambda r: (3 if r.district_id else 2 if r.province_id else 1), reverse=True)

        debug_lines.append("Valid sorted coverages count: %s" % len(valid_coverages))
        for c in valid_coverages:
            debug_lines.append("  valid cov ID %s: specificity=%s, cost=%s, origin=%s" % 
                               (c.id, (3 if c.district_id else 2 if c.province_id else 1), c.cost, c.origin_department_id.id if c.origin_department_id else False))

        if not valid_coverages:
            debug_lines.append("No valid coverages found, returning False")
            try:
                with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                    f.write("\n".join(debug_lines) + "\n")
            except Exception:
                pass
            return False, 0.0

        # 1. Intentar buscar una regla directa específica para el origen en las coberturas válidas
        for cov in valid_coverages:
            if cov.origin_department_id and cov.origin_department_id.id == origin_dept_id:
                debug_lines.append("Found specific coverage rule directly matching origin: ID %s, cost=%s" % (cov.id, cov.cost))
                try:
                    with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                        f.write("\n".join(debug_lines) + "\n")
                except Exception:
                    pass
                return cov, cov.cost

        # 2. Si el origen es diferente al destino, intentar aplicar la suma interprovincial (Opción B)
        if origin_dept_id and dest_dept_id and origin_dept_id != dest_dept_id:
            interstate_rule = env['delivery.interstate.cost'].sudo().search([
                ('state_from_id', '=', origin_dept_id),
                ('state_to_id', '=', dest_dept_id)
            ], limit=1)
            debug_lines.append("Interstate rule search (from %s to %s) found: %s" % (origin_dept_id, dest_dept_id, interstate_rule.exists()))
            if interstate_rule:
                debug_lines.append("  interstate cost: %s" % interstate_rule.cost)
                local_cov = False
                for cov in valid_coverages:
                    if cov.origin_department_id and cov.origin_department_id.id == dest_dept_id:
                        local_cov = cov
                        break
                if not local_cov:
                    for cov in valid_coverages:
                        if not cov.origin_department_id:
                            local_cov = cov
                            break
                            
                if local_cov:
                    total_cost = local_cov.cost + interstate_rule.cost
                    debug_lines.append("  Found local_cov: ID %s, local cost: %s, total sum cost: %s" % (local_cov.id, local_cov.cost, total_cost))
                    try:
                        with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                            f.write("\n".join(debug_lines) + "\n")
                    except Exception:
                        pass
                    return local_cov, total_cost

        # 3. Fallback: Buscar regla general de cobertura (sin origen) en las coberturas válidas
        for cov in valid_coverages:
            if not cov.origin_department_id:
                debug_lines.append("Fallback to general coverage rule (no origin): ID %s, cost=%s" % (cov.id, cov.cost))
                try:
                    with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                        f.write("\n".join(debug_lines) + "\n")
                except Exception:
                    pass
                return cov, cov.cost
                
        # Retornar la primera regla encontrada si hay alguna
        debug_lines.append("Fallback to first valid coverage: ID %s, cost=%s" % (valid_coverages[0].id, valid_coverages[0].cost))
        try:
            with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                f.write("\n".join(debug_lines) + "\n")
        except Exception:
            pass
        return valid_coverages[0], valid_coverages[0].cost

        return False, 0.0

    @http.route('/shop/delivery/locations', type='jsonrpc', auth='public', website=True)
    def get_locations(self, department_id=False, province_id=False, **kw):
        """Devuelve departamentos, provincias o distritos de manera jerárquica."""
        env = request.env

        # 1. Provincias de un Departamento (state_id = res.country.state)
        if department_id:
            dept_domain = []
            if str(department_id).isdigit():
                dept_domain = ['|', ('state_id', '=', int(department_id)), ('state_id.code', '=', str(department_id))]
            else:
                dept_domain = [('state_id.name', 'ilike', str(department_id))]
            
            provinces = env['wango.province'].sudo().search(dept_domain, order='name asc')
            if not provinces and str(department_id).isdigit():
                # Fallback buscar por nombre del state_id si no hubo match directo
                st = env['res.country.state'].sudo().browse(int(department_id))
                if st.exists():
                    provinces = env['wango.province'].sudo().search([('state_id.name', 'ilike', st.name)], order='name asc')

            result_provinces = []
            for p in provinces:
                name = p.name
                # Si en base de datos quedó 'Callao' para el código 1501 (Lima Metropolitana), corregir al vuelo
                if p.code == '1501' or (name == 'Callao' and p.state_id.code == '15'):
                    name = 'Lima'
                    # Auto-actualizar en BD si tiene el nombre viejo
                    if p.name != 'Lima':
                        p.sudo().write({'name': 'Lima'})
                result_provinces.append({'id': p.id, 'name': name})
            
            result_provinces.sort(key=lambda x: x['name'])
            return result_provinces

        # 2. Distritos de una Provincia
        if province_id:
            districts = env['wango.district'].sudo().search(
                [('province_id', '=', int(province_id))], order='name asc'
            )
            return [{'id': d.id, 'name': d.name} for d in districts]

        # 3. Departamentos — derivados de wango.province (fuente de verdad configurada).
        #    Evita depender de que res.country.state tenga datos de Perú cargados.
        provinces_all = env['wango.province'].sudo().search([])
        seen = {}
        for p in provinces_all:
            if p.state_id and p.state_id.id not in seen:
                seen[p.state_id.id] = p.state_id.name

        if seen:
            return sorted(
                [{'id': k, 'name': v} for k, v in seen.items()],
                key=lambda x: x['name']
            )

        # Fallback: buscar directamente en res.country.state por código PE o nombre Perú
        states = env['res.country.state'].sudo().search(
            [('country_id.code', '=', 'PE')], order='name asc'
        )
        if not states:
            states = env['res.country.state'].sudo().search(
                [('country_id.name', 'ilike', 'Per')], order='name asc'
            )
        return [{'id': s.id, 'name': s.name} for s in states]

    @http.route('/shop/delivery/product_info', type='jsonrpc', auth='public', website=True)
    def get_product_delivery_info(self, product_id, qty=1, department_id=False, province_id=False, district_id=False, **kw):
        """Calcula opciones, costos y disponibilidad de delivery para un producto específico."""
        qty = int(qty) or 1
        product = request.env['product.template'].sudo().browse(int(product_id))
        
        try:
            with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                f.write("\n--- get_product_delivery_info ROUTE START ---\n")
                f.write("product_id: %s (exists: %s)\n" % (product_id, product.exists()))
        except Exception:
            pass

        if not product.exists():
            return {'error': _('Producto no encontrado')}

        # 1. Determinar Departamento de Origen del Producto, Vendedor o Compañía
        origin_dept_id = False
        origin_source = ""
        if product.wango_origin_department_id:
            origin_dept_id = product.wango_origin_department_id.id
            origin_source = "product"
        elif getattr(product, 'marketplace_seller_id', False) and product.marketplace_seller_id.state_id:
            origin_dept_id = product.marketplace_seller_id.state_id.id
            origin_source = "marketplace_seller"
        elif getattr(product, 'seller_id', False) and getattr(product.seller_id, 'partner_id', False) and product.seller_id.partner_id.state_id:
            origin_dept_id = product.seller_id.partner_id.state_id.id
            origin_source = "seller"
        elif product.company_id and product.company_id.partner_id.state_id:
            origin_dept_id = product.company_id.partner_id.state_id.id
            origin_source = "company"
        else:
            # Fallback a primer departamento encontrado en Perú (ej. Lima)
            lima = request.env['res.country.state'].sudo().search([('code', '=', 'LIMA'), ('country_id.code', '=', 'PE')], limit=1)
            if not lima:
                lima = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'PE')], limit=1)
            origin_dept_id = lima.id if lima else False
            origin_source = "fallback_lima"

        try:
            with open("C:/Users/Dev/AppData/Local/Temp/wango_debug.log", "a", encoding="utf-8") as f:
                f.write("resolved origin_dept_id: %s (source: %s)\n" % (origin_dept_id, origin_source))
        except Exception:
            pass

                # 2. Retiro en Agente Wanka o Local Propio
        branches_data = []
        allow_pickup = product.wango_only_pickup or not product.wango_no_home_delivery or not product.wango_no_agency
        
        branch_domain = [('active', '=', True)]
        if district_id:
            branch_domain.append(('district_id', '=', int(district_id)))
        elif province_id:
            branch_domain.append(('province_id', '=', int(province_id)))
        elif department_id:
            branch_domain.append(('department_id', '=', int(department_id)))

        branches = request.env['delivery.store.branch'].sudo().search(branch_domain)
        pickup_available = False
        product_seller = getattr(product, 'marketplace_seller_id', False)

        for branch in branches:
            # Si es local propio de un vendedor y no es el dueño de este producto, saltar
            if getattr(branch, 'point_type', 'agent') == 'seller_store' and getattr(branch, 'seller_id', False):
                if not product_seller or branch.seller_id.id != product_seller.id:
                    continue

            # Para Agente Wanka o almacenes sin inventario Odoo forzado:
            has_stock = True
            if getattr(branch, 'warehouse_id', False) and product.type == 'consu' and getattr(product, 'is_storable', True):
                try:
                    avail_qty = product.with_context(warehouse=branch.warehouse_id.id).free_qty
                    has_stock = avail_qty >= qty
                except Exception:
                    has_stock = True

            if has_stock:
                pickup_available = True

            ptype = getattr(branch, 'point_type', 'agent') or 'agent'
            type_label = 'Agente Wanka' if ptype == 'agent' else 'Local del Vendedor'

            branches_data.append({
                'id': branch.id,
                'name': branch.name,
                'point_type': ptype,
                'type_label': type_label,
                'address': branch.address,
                'reference': getattr(branch, 'reference', '') or '',
                'has_stock': has_stock,
                'stock_message': _('✓ Disponible para retiro') if has_stock else _('✗ Sin stock'),
                'schedule': branch.schedule or ''
            })

        # Verificar si el vendedor tiene activado el interruptor de retiro en su local propio en su perfil
        if product_seller and getattr(product_seller, 'seller_allow_pickup', False):
            seller_dist = getattr(product_seller, 'seller_pickup_district_id', False)
            seller_prov = getattr(product_seller, 'seller_pickup_province_id', False)
            seller_dept = getattr(product_seller, 'seller_pickup_department_id', False)
            
            matches_seller_loc = False
            if district_id and seller_dist and seller_dist.id == int(district_id):
                matches_seller_loc = True
            elif not district_id and province_id and seller_prov and seller_prov.id == int(province_id):
                matches_seller_loc = True
            elif not district_id and not province_id and department_id and seller_dept and seller_dept.id == int(department_id):
                matches_seller_loc = True
            elif not district_id and not province_id and not department_id:
                matches_seller_loc = True

            if matches_seller_loc:
                pickup_available = True
                branches_data.insert(0, {
                    'id': 'seller_%s' % product_seller.id,
                    'name': 'Tienda de %s' % (product_seller.name or 'Vendedor'),
                    'point_type': 'seller_store',
                    'type_label': 'Local del Vendedor',
                    'address': product_seller.seller_pickup_address or (product_seller.street or ''),
                    'reference': product_seller.seller_pickup_reference or '',
                    'has_stock': True,
                    'stock_message': _('✓ Disponible para retiro'),
                    'schedule': product_seller.seller_pickup_schedule or 'Horario comercial'
                })

        # 3. Despacho a Domicilio
        home_delivery_data = {'available': False, 'message': _('Sin cobertura en esta zona')}
        if not product.wango_only_pickup and not product.wango_no_home_delivery and district_id:
            coverage, cost = self._get_home_delivery_coverage_and_cost(district_id, origin_dept_id)
            
            if coverage:
                product_price_total = product.list_price * qty
                if coverage.free_shipping_min > 0 and product_price_total >= coverage.free_shipping_min:
                    cost = 0.0
                
                if product.wango_custom_home_time:
                    time_display_str = product.wango_custom_home_time
                else:
                    unit_display = _('días') if coverage.time_unit == 'days' else _('horas')
                    time_display_str = '%s-%s %s' % (coverage.time_min, coverage.time_max, unit_display)
                    
                home_delivery_data = {
                    'available': True,
                    'cost': cost,
                    'cost_display': _('Gratis') if cost == 0.0 else 'S/ %.2f' % cost,
                    'time_display': time_display_str
                }

        # 4. Envío por Agencia
        agency_data = {'available': False, 'message': _('No disponible en esta zona')}
        if not product.wango_only_pickup and not product.wango_no_agency and district_id:
            total_weight = (product.weight or 0.0) * qty
            total_volume = (product.volume or 0.0) * qty
            
            agency_domain = [
                ('weight_max', '>=', total_weight),
                ('volume_max', '>=', total_volume),
            ]
            cost_rules = request.env['delivery.agency.cost'].sudo().search(agency_domain)
            # Sort by specificity descending: district > province > department > global
            cost_rules = sorted(
                cost_rules,
                key=lambda r: (3 if r.district_id else 2 if r.province_id else 1 if r.department_id else 0),
                reverse=True
            )
            
            matching_agencies = []
            agencies_processed = set()
            
            for rule in cost_rules:
                if not rule.agency_id:
                    continue
                if rule.agency_id.id in agencies_processed:
                    continue
                    
                matches_location = False
                if rule.district_id and rule.district_id.id == int(district_id):
                    matches_location = True
                elif not rule.district_id and rule.province_id and rule.province_id.id == int(province_id):
                    matches_location = True
                elif not rule.district_id and not rule.province_id and rule.department_id and rule.department_id.id == int(department_id):
                    matches_location = True
                elif not rule.district_id and not rule.province_id and not rule.department_id:
                    matches_location = True
                    
                if matches_location:
                    matching_agencies.append({
                        'id': rule.agency_id.id,
                        'name': rule.agency_id.name,
                        'cost': rule.cost,
                        'cost_display': 'S/ %.2f' % rule.cost,
                        'time_display': '%s-%s días' % (rule.time_min, rule.time_max)
                    })
                    agencies_processed.add(rule.agency_id.id)
            
            if matching_agencies:
                matching_agencies.sort(key=lambda x: x['cost'])
                cheapest = matching_agencies[0]
                agency_data = {
                    'id': cheapest['id'],
                    'available': True,
                    'cost_display': cheapest['cost_display'],
                    'time_display': cheapest['time_display'],
                    'name': cheapest['name'],
                    'all_agencies': matching_agencies
                }

        cov_count = 0
        if district_id:
            cov_count = request.env['delivery.coverage'].sudo().search_count([
                ('district_id', '=', int(district_id)),
                ('active', '=', True)
            ])
            
        agency_rules_count = 0
        if district_id:
            agency_rules_count = request.env['delivery.agency.cost'].sudo().search_count([
                ('weight_max', '>=', (product.weight or 0.0) * qty),
                ('volume_max', '>=', (product.volume or 0.0) * qty),
            ])

        diagnostics = {
            'product_name': product.name,
            'product_only_pickup': product.wango_only_pickup,
            'product_no_home_delivery': product.wango_no_home_delivery,
            'product_no_agency': product.wango_no_agency,
            'district_id': district_id,
            'origin_dept_id': origin_dept_id,
            'coverages_found_for_district': cov_count,
            'agency_rules_found_total': agency_rules_count,
        }

        return {
            'store_pickup': {
                'available': pickup_available,
                'cost_display': _('Gratis'),
                'branches': branches_data,
                'time_display': product.wango_custom_pickup_time if product.wango_custom_pickup_time else ''
            },
            'home_delivery': home_delivery_data,
            'agency_shipping': agency_data,
            'diagnostics': diagnostics
        }

    @http.route('/shop/delivery/branches', type='jsonrpc', auth='public', website=True)

    def get_branches(self, district_id=False, **kw):
        """Devuelve las sucursales habilitadas en la ubicación seleccionada y su stock en tiempo real."""
        if not district_id:
            return []
            
        order = getattr(request, 'cart', None) or (getattr(request, 'website', None) or request.env['website'].get_current_website()).sale_get_order()
        if not order:
            return []

        branches = request.env['delivery.store.branch'].sudo().search([
            ('district_id', '=', int(district_id)),
            ('active', '=', True)
        ])
        
        result = []
        for branch in branches:
            # Validar stock en la sucursal
            stock_errors = order.check_cart_stock_wango(branch.warehouse_id)
            stock_available = len(stock_errors) == 0
            
            result.append({
                'id': branch.id,
                'name': branch.name,
                'address': branch.address,
                'latitude': branch.latitude,
                'longitude': branch.longitude,
                'phone': branch.phone or '',
                'schedule': branch.schedule or '',
                'stock_available': stock_available,
                'stock_message': _('✓ Stock Disponible') if stock_available else _('✕ Sin stock en esta tienda'),
                'cost_display': _('Gratis'),
                'cost': 0.0
            })
        return result

    @http.route('/shop/delivery/calculate', type='jsonrpc', auth='public', website=True)
    def calculate_delivery(self, department_id, province_id, district_id, **kw):
        """Calcula el costo y tiempos estimados para Domicilio y Agencias en la ubicación."""
        order = getattr(request, 'cart', None) or (getattr(request, 'website', None) or request.env['website'].get_current_website()).sale_get_order()
        if not order:
            return {'error': _('No se encontró orden activa')}

        # Peso y volumen acumulados del carrito
        total_weight = sum(line.product_id.weight * line.product_uom_qty for line in order.order_line if not line.is_delivery and line.product_id)
        total_volume = sum(line.product_id.volume * line.product_uom_qty for line in order.order_line if not line.is_delivery and line.product_id)

        # 1. Calcular Delivery a Domicilio
        origin_dept_id = self._get_order_origin_dept_id(order)
        coverage, cost = self._get_home_delivery_coverage_and_cost(district_id, origin_dept_id)
        
        delivery_info = None
        if coverage:
            # Validar envío gratis por monto mínimo
            if coverage.free_shipping_min > 0 and order.amount_untaxed >= coverage.free_shipping_min:
                cost = 0.0
                
            unit_display = _('días') if coverage.time_unit == 'days' else _('horas')
            delivery_info = {
                'available': True,
                'cost': cost,
                'cost_display': _('Gratis') if cost == 0.0 else 'S/ %.2f' % cost,
                'time_display': '%s-%s %s' % (coverage.time_min, coverage.time_max, unit_display),
                'free_shipping_min': coverage.free_shipping_min,
                'free_shipping_diff': max(coverage.free_shipping_min - order.amount_untaxed, 0.0)
            }
        else:
            delivery_info = {
                'available': False,
                'message': _('Sin cobertura de reparto en este distrito actualmente.')
            }

        # 2. Calcular Envíos por Agencia (Flete acumulado)
        # Buscar tarifas coincidentes
        domain = [
            ('weight_max', '>=', total_weight),
            ('volume_max', '>=', total_volume),
            ('company_id', '=', order.company_id.id)
        ]
        
        # Buscar tarifas con priorización jerárquica (Distrito > Provincia > Departamento > Global)
        cost_rules = request.env['delivery.agency.cost'].sudo().search(domain)
        # Sort by specificity descending: district > province > department > global
        cost_rules = sorted(
            cost_rules,
            key=lambda r: (3 if r.district_id else 2 if r.province_id else 1 if r.department_id else 0),
            reverse=True
        )
        
        agencies_data = []
        agencies_processed = set()
        
        # Clasificar tarifas encontradas por agencia
        for rule in cost_rules:
            if rule.agency_id.id in agencies_processed:
                continue
                
            # Verificar si la regla cubre la ubicación jerárquicamente
            matches_location = False
            if rule.district_id and rule.district_id.id == int(district_id):
                matches_location = True
            elif not rule.district_id and rule.province_id and rule.province_id.id == int(province_id):
                matches_location = True
            elif not rule.district_id and not rule.province_id and rule.department_id and rule.department_id.id == int(department_id):
                matches_location = True
            elif not rule.district_id and not rule.province_id and not rule.department_id:
                # Regla general (catch-all)
                matches_location = True
                
            if matches_location:
                # Obtener logo de agencia como base64 o url
                logo_url = '/web/image/wango.agency/%s/logo' % rule.agency_id.id if rule.agency_id.logo else '/wango_delivery/static/src/img/agency_default.png'
                
                agencies_data.append({
                    'id': rule.agency_id.id,
                    'name': rule.agency_id.name,
                    'logo': logo_url,
                    'cost': rule.cost,
                    'cost_display': 'S/ %.2f' % rule.cost,
                    'time_display': '%s-%s días' % (rule.time_min, rule.time_max),
                    'phone': rule.agency_id.phone or ''
                })
                agencies_processed.add(rule.agency_id.id)
                
        # Ordenar agencias de menor a mayor costo
        agencies_data.sort(key=lambda x: x['cost'])

        return {
            'home_delivery': delivery_info,
            'agencies': agencies_data
        }

    @http.route('/shop/delivery/select', type='jsonrpc', auth='public', website=True)
    def select_delivery(self, delivery_type, department_id=False, province_id=False, district_id=False, store_branch_id=False, agency_id=False, **kw):
        """Asigna la opción de entrega seleccionada al Sale Order y actualiza el carrito."""
        order = getattr(request, 'cart', None) or (getattr(request, 'website', None) or request.env['website'].get_current_website()).sale_get_order()
        if not order:
            return {'error': _('No se encontró orden activa')}

        cost = 0.0
        description = ''
        est_date = None

        # 1. Procesar Retiro en Tienda
        if delivery_type == 'store_pickup':
            branch = request.env['delivery.store.branch'].sudo().browse(int(store_branch_id))
            if not branch.exists():
                return {'error': _('Sucursal no encontrada')}
                
            # Validar stock en la sucursal solo si tiene un almacén asignado
            if branch.warehouse_id:
                stock_errors = order.check_cart_stock_wango(branch.warehouse_id)
                if stock_errors:
                    return {'error': "\n".join(stock_errors)}
                
            cost = 0.0
            description = _('Retiro en tienda: %s') % branch.name
            est_date = fields.Date.context_today(order) # Hoy mismo
            
            order.write({
                'delivery_type': 'store_pickup',
                'store_branch_id': branch.id,
                'agency_id': False,
                'delivery_department_id': branch.department_id.id if branch.department_id else (int(department_id) if department_id else False),
                'delivery_province_id': branch.province_id.id if branch.province_id else (int(province_id) if province_id else False),
                'delivery_district_id': branch.district_id.id if branch.district_id else (int(district_id) if district_id else False),
                'shipping_cost': 0.0,
                'estimated_delivery_date': est_date
            })

        # 2. Procesar Entrega a Domicilio
        elif delivery_type == 'home_delivery':
            origin_dept_id = self._get_order_origin_dept_id(order)
            coverage, cost = self._get_home_delivery_coverage_and_cost(district_id, origin_dept_id)
            if not coverage:
                return {'error': _('No hay cobertura de reparto para la zona elegida.')}
            if coverage.free_shipping_min > 0 and order.amount_untaxed >= coverage.free_shipping_min:
                cost = 0.0
                
            district = request.env['wango.district'].sudo().browse(int(district_id))
            description = _('Despacho a domicilio: %s') % district.name
            
            # Calcular fecha estimada
            days = coverage.time_max if coverage.time_unit == 'days' else 1
            est_date = fields.Date.context_today(order) + timedelta(days=days)
            
            order.write({
                'delivery_type': 'home_delivery',
                'store_branch_id': False,
                'agency_id': False,
                'delivery_department_id': int(department_id) if department_id else False,
                'delivery_province_id': int(province_id) if province_id else False,
                'delivery_district_id': int(district_id) if district_id else False,
                'shipping_cost': cost,
                'estimated_delivery_date': est_date
            })

        # 3. Procesar Envío por Agencia
        elif delivery_type == 'agency_shipping':
            agency = request.env['wango.agency'].sudo().browse(int(agency_id))
            if not agency.exists():
                return {'error': _('Agencia no encontrada')}
                
            # Calcular costo en base al peso y volumen total acumulado
            total_weight = sum(line.product_id.weight * line.product_uom_qty for line in order.order_line if not line.is_delivery and line.product_id)
            total_volume = sum(line.product_id.volume * line.product_uom_qty for line in order.order_line if not line.is_delivery and line.product_id)
            
            domain = [
                ('agency_id', '=', agency.id),
                ('weight_max', '>=', total_weight),
                ('volume_max', '>=', total_volume),
                ('company_id', '=', order.company_id.id)
            ]
            cost_rules = request.env['delivery.agency.cost'].sudo().search(domain)
            # Sort by specificity descending: district > province > department > global
            cost_rules = sorted(
                cost_rules,
                key=lambda r: (3 if r.district_id else 2 if r.province_id else 1 if r.department_id else 0),
                reverse=True
            )
            
            selected_rule = False
            for rule in cost_rules:
                if rule.district_id and rule.district_id.id == int(district_id):
                    selected_rule = rule
                    break
                elif not rule.district_id and rule.province_id and rule.province_id.id == int(province_id):
                    selected_rule = rule
                    break
                elif not rule.district_id and not rule.province_id and rule.department_id and rule.department_id.id == int(department_id):
                    selected_rule = rule
                    break
                elif not rule.district_id and not rule.province_id and not rule.department_id:
                    selected_rule = rule
                    break
                        
            if not selected_rule:
                return {'error': _('No se encontró tarifa de flete para la agencia seleccionada en este destino.')}
                
            cost = selected_rule.cost
            description = _('Recibir en agencia: %s') % agency.name
            
            est_date = fields.Date.context_today(order) + timedelta(days=selected_rule.time_max)
            
            order.write({
                'delivery_type': 'agency_shipping',
                'store_branch_id': False,
                'agency_id': agency.id,
                'delivery_department_id': int(department_id) if department_id else False,
                'delivery_province_id': int(province_id) if province_id else False,
                'delivery_district_id': int(district_id) if district_id else False,
                'shipping_cost': cost,
                'estimated_delivery_date': est_date
            })

        else:
            return {'error': _('Modalidad de entrega no válida')}

        # Inyectar la línea de envío en el pedido
        order.sudo()._set_wango_delivery_line(cost, description)

        return {
            'success': True,
            'delivery_type': order.delivery_type,
            'summary_html': description,
            'shipping_cost_display': _('Gratis') if cost == 0.0 else 'S/ %.2f' % cost,
            'order_total_display': 'S/ %.2f' % order.amount_total,
            'estimated_date_display': est_date.strftime('%d/%m/%Y') if est_date else ''
        }


    @http.route('/shop/delivery/locate_by_coords', type='jsonrpc', auth='public', website=True)
    def locate_by_coords(self, latitude, longitude, **kw):
        """Traduce latitud y longitud a Distrito, Provincia y Departamento usando geocodificación inversa libre."""
        import urllib.request
        import json
        
        dept_name = ""
        prov_name = ""
        dist_name = ""
        street_name = ""
        
        try:
            url = "https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=%s&lon=%s" % (latitude, longitude)
            req = urllib.request.Request(url, headers={'User-Agent': 'MercadoWankaOdoo/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    address = data.get('address', {})
                    
                    dist_candidate = (
                        address.get('suburb') or 
                        address.get('neighbourhood') or 
                        address.get('city_district') or 
                        address.get('town') or 
                        address.get('village') or 
                        address.get('municipality') or
                        address.get('quarter')
                    )
                    prov_candidate = address.get('county') or address.get('city')
                    dept_candidate = address.get('state') or address.get('region')
                    
                    road = address.get('road') or address.get('pedestrian') or address.get('path') or address.get('street') or ''
                    house_num = address.get('house_number') or ''
                    if road:
                        street_name = ("%s %s" % (road, house_num)).strip()
                    
                    dist_name = dist_candidate or ""
                    prov_name = prov_candidate or ""
                    dept_name = dept_candidate or ""
        except Exception:
            pass

        District = request.env['wango.district'].sudo()
        district_rec = False
        
        if dist_name:
            district_rec = District.search([('name', 'ilike', dist_name.strip())], limit=1)
            
        if not district_rec and prov_name:
            district_rec = District.search([('province_id.name', 'ilike', prov_name.strip())], limit=1)

        # Fallback a Huancayo si no coincide
        if not district_rec:
            district_rec = District.search([('name', 'ilike', 'Huancayo'), ('province_id.name', 'ilike', 'Huancayo')], limit=1)
            if not district_rec:
                district_rec = District.search([], limit=1)

        if district_rec:
            return {
                'success': True,
                'district_id': district_rec.id,
                'district_name': district_rec.name,
                'province_id': district_rec.province_id.id,
                'province_name': district_rec.province_id.name,
                'department_id': district_rec.state_id.id if district_rec.state_id else False,
                'department_name': district_rec.state_id.name if district_rec.state_id else 'Junín',
                'street': street_name,
            }
        return {'success': False, 'message': 'No se pudo determinar el distrito'}

    @http.route('/shop/delivery/user_addresses', type='jsonrpc', auth='public', website=True)
    def get_user_addresses(self, **kw):
        """Devuelve las direcciones registradas del usuario autenticado para selección rápida."""
        if request.env.user._is_public():
            return {'logged_in': False, 'addresses': []}

        partner = request.env.user.partner_id
        # Direcciones de envío del contacto principal
        addresses = partner.child_ids.filtered(lambda c: c.type in ('delivery', 'other') and not c.is_company)
        
        results = []
        # Incluir la dirección principal del partner si tiene calle y ciudad/distrito
        if partner.street or partner.city:
            results.append({
                'id': partner.id,
                'name': partner.name or 'Dirección Principal',
                'street': partner.street or '',
                'street2': partner.street2 or '',
                'city': partner.city or '',
                'state_id': partner.state_id.id if partner.state_id else False,
                'state_name': partner.state_id.name if partner.state_id else '',
                'is_main': True,
            })

        for addr in addresses:
            results.append({
                'id': addr.id,
                'name': addr.name or 'Otra Dirección',
                'street': addr.street or '',
                'street2': addr.street2 or '',
                'city': addr.city or '',
                'state_id': addr.state_id.id if addr.state_id else False,
                'state_name': addr.state_id.name if addr.state_id else '',
                'is_main': False,
            })

        # Enlazar con wango.district si coincide con city
        District = request.env['wango.district'].sudo()
        for r in results:
            if r['city']:
                d = District.search([('name', 'ilike', r['city'].strip())], limit=1)
                if d:
                    r['district_id'] = d.id
                    r['district_name'] = d.name
                    r['province_id'] = d.province_id.id
                    r['province_name'] = d.province_id.name
                    r['department_id'] = d.state_id.id if d.state_id else False
                    r['department_name'] = d.state_id.name if d.state_id else ''

        return {'logged_in': True, 'addresses': results}

    @http.route('/shop/delivery/save_user_address', type='jsonrpc', auth='user', website=True)
    def save_user_address(self, name, street, street2="", district_id=False, **kw):
        """Permite guardar una nueva dirección física en la libreta del usuario autenticado."""
        partner = request.env.user.partner_id
        District = request.env['wango.district'].sudo()
        district = District.browse(int(district_id)) if district_id else False

        state_id = district.state_id.id if district and district.state_id else partner.state_id.id
        city_name = district.name if district else ''

        new_addr = request.env['res.partner'].sudo().create({
            'parent_id': partner.id,
            'type': 'delivery',
            'name': name or 'Mi Dirección',
            'street': street,
            'street2': street2,
            'city': city_name,
            'state_id': state_id,
            'country_id': partner.country_id.id or request.env.ref('base.pe', raise_if_not_found=False).id,
        })

        return {
            'success': True,
            'address_id': new_addr.id,
            'name': new_addr.name,
            'street': new_addr.street,
            'city': new_addr.city,
            'district_id': district.id if district else False,
            'district_name': district.name if district else '',
            'province_id': district.province_id.id if district else False,
            'province_name': district.province_id.name if district else '',
            'department_id': state_id,
            'department_name': district.state_id.name if district and district.state_id else '',
        }
