# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_type = fields.Selection([
        ('store_pickup', 'Retiro en tienda'),
        ('home_delivery', 'Despacho a domicilio'),
        ('agency_shipping', 'Recibir en agencia')
    ], string='Tipo de Entrega')

    store_branch_id = fields.Many2one('delivery.store.branch', string='Sucursal de Retiro')
    agency_id = fields.Many2one('wango.agency', string='Agencia de Envío')
    
    delivery_department_id = fields.Many2one('res.country.state', string='Departamento de Entrega', domain="[('country_id.code', '=', 'PE')]")
    delivery_province_id = fields.Many2one('wango.province', string='Provincia de Entrega', domain="[('state_id', '=', delivery_department_id)]")
    delivery_district_id = fields.Many2one('wango.district', string='Distrito de Entrega', domain="[('province_id', '=', delivery_province_id)]")
    
    estimated_delivery_date = fields.Date(string='Fecha Estimada de Entrega')
    shipping_cost = fields.Monetary(string='Costo de Envío Real', currency_field='currency_id')
    wango_shipment_id = fields.Many2one('wango.shipment', string='Envío de Encomienda Asociado')

    wango_allow_pickup = fields.Boolean(compute='_compute_wango_delivery_restrictions', string='Permitir Retiro en Tienda')
    wango_allow_home_delivery = fields.Boolean(compute='_compute_wango_delivery_restrictions', string='Permitir Entrega a Domicilio')
    wango_allow_agency = fields.Boolean(compute='_compute_wango_delivery_restrictions', string='Permitir Envío por Agencia')

    @api.depends('order_line.product_id.wango_only_pickup', 
                 'order_line.product_id.wango_no_agency', 
                 'order_line.product_id.wango_no_home_delivery')
    def _compute_wango_delivery_restrictions(self):
        for order in self:
            products = order.order_line.filtered(lambda l: not l.is_delivery).mapped('product_id')
            any_only_pickup = any(p.wango_only_pickup for p in products)
            any_no_agency = any(p.wango_no_agency for p in products)
            any_no_home = any(p.wango_no_home_delivery for p in products)
            
            if any_only_pickup:
                order.wango_allow_pickup = True
                order.wango_allow_home_delivery = False
                order.wango_allow_agency = False
            else:
                order.wango_allow_pickup = True
                order.wango_allow_home_delivery = not any_no_home
                order.wango_allow_agency = not any_no_agency

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'carrier_id' in vals:
                carrier = self.env['delivery.carrier'].browse(vals['carrier_id']) if vals['carrier_id'] else False
                if carrier:
                    vals.update({
                        'delivery_type': carrier.wango_delivery_type,
                        'store_branch_id': carrier.store_branch_id.id if carrier.store_branch_id else False,
                        'agency_id': carrier.agency_id.id if carrier.agency_id else False,
                    })
                else:
                    vals.update({
                        'delivery_type': False,
                        'store_branch_id': False,
                        'agency_id': False,
                    })
        return super(SaleOrder, self).create(vals_list)

    def write(self, vals):
        if 'carrier_id' in vals:
            carrier = self.env['delivery.carrier'].browse(vals['carrier_id']) if vals['carrier_id'] else False
            if carrier:
                vals.update({
                    'delivery_type': carrier.wango_delivery_type,
                    'store_branch_id': carrier.store_branch_id.id if carrier.store_branch_id else False,
                    'agency_id': carrier.agency_id.id if carrier.agency_id else False,
                })
            else:
                vals.update({
                    'delivery_type': False,
                    'store_branch_id': False,
                    'agency_id': False,
                })
        return super(SaleOrder, self).write(vals)

    @api.onchange('carrier_id')
    def _onchange_carrier_id_wango(self):
        if self.carrier_id:
            self.delivery_type = self.carrier_id.wango_delivery_type
            self.store_branch_id = self.carrier_id.store_branch_id
            self.agency_id = self.carrier_id.agency_id
        else:
            self.delivery_type = False
            self.store_branch_id = False
            self.agency_id = False

    def _clear_wango_delivery(self):
        """Limpia los campos de envío de WanGO y elimina la línea de envío del carrito."""
        self.ensure_one()
        self.write({
            'carrier_id': False,
            'delivery_type': False,
            'store_branch_id': False,
            'agency_id': False,
            'delivery_department_id': False,
            'delivery_province_id': False,
            'delivery_district_id': False,
            'shipping_cost': 0.0,
            'estimated_delivery_date': False
        })
        # Eliminar línea de entrega si existe
        delivery_line = self.order_line.filtered(lambda l: l.is_delivery)
        if delivery_line:
            delivery_line.sudo().unlink()

    def _check_delivery_restrictions(self):
        """Valida que la modalidad de entrega seleccionada no sea violada por las restricciones de los productos del carrito."""
        self.ensure_one()
        if not self.carrier_id:
            return
            
        products = self.order_line.filtered(lambda l: not l.is_delivery).mapped('product_id')
        any_only_pickup = any(p.wango_only_pickup for p in products)
        any_no_agency = any(p.wango_no_agency for p in products)
        any_no_home = any(p.wango_no_home_delivery for p in products)
        
        should_clear = False
        delivery_type = self.carrier_id.wango_delivery_type
        if any_only_pickup and delivery_type != 'store_pickup':
            should_clear = True
        elif any_no_agency and delivery_type == 'agency_shipping':
            should_clear = True
        elif any_no_home and delivery_type == 'home_delivery':
            should_clear = True
            
        if should_clear:
            self._clear_wango_delivery()

    def _get_delivery_methods(self):
        carriers = super(SaleOrder, self)._get_delivery_methods()
        products = self.order_line.filtered(lambda l: not l.is_delivery).mapped('product_id')
        any_only_pickup = any(p.wango_only_pickup for p in products)
        any_no_agency = any(p.wango_no_agency for p in products)
        any_no_home = any(p.wango_no_home_delivery for p in products)
        
        filtered_carriers = self.env['delivery.carrier']
        for carrier in carriers:
            if any_only_pickup and carrier.wango_delivery_type != 'store_pickup':
                continue
            if any_no_agency and carrier.wango_delivery_type == 'agency_shipping':
                continue
            if any_no_home and carrier.wango_delivery_type == 'home_delivery':
                continue
            filtered_carriers |= carrier
        return filtered_carriers

    def check_cart_stock_wango(self, warehouse_id=False):
        """
        Valida el stock disponible de los productos en el carrito.
        Si se pasa warehouse_id, valida en esa sucursal específica.
        Si no, valida a nivel consolidado de la compañía.
        """
        self.ensure_one()
        errors = []
        for line in self.order_line.filtered(lambda l: not l.is_delivery and l.product_id.type == 'product'):
            product = line.product_id
            qty_needed = line.product_uom_qty
            
            if warehouse_id:
                # Stock en almacén de la sucursal
                avail_qty = product.with_context(warehouse=warehouse_id.id).free_qty
                # Fallback en caso de que free_qty no esté disponible en la versión/modelo
                if avail_qty is None or avail_qty < 0:
                    avail_qty = product.with_context(warehouse=warehouse_id.id).virtual_available
            else:
                # Stock consolidado de la compañía
                avail_qty = product.free_qty
                if avail_qty is None or avail_qty < 0:
                    avail_qty = product.virtual_available
            
            if avail_qty < qty_needed:
                errors.append(_("El producto '%s' no cuenta con suficiente stock disponible (%s requeridos, %s disponibles).") % (product.display_name, qty_needed, avail_qty))
        return errors

    def _get_or_create_wango_carrier(self, delivery_type, name):
        """Busca el transportista nativo (delivery.carrier) configurado por el admin para esta modalidad."""
        # 1. Buscar por el campo de vinculación wango_delivery_type
        carrier = self.env['delivery.carrier'].sudo().search([
            ('wango_delivery_type', '=', delivery_type)
        ], limit=1)
        
        # 2. Si no se encuentra vinculación explícita, buscar por nombre coincidente
        if not carrier:
            carrier = self.env['delivery.carrier'].sudo().search([
                ('name', 'ilike', name)
            ], limit=1)
            
        # 3. Si sigue sin existir, crear un transportista por defecto como salvaguarda (fallback)
        if not carrier:
            product = self.env['product.product'].sudo().search([('default_code', '=', 'WANGO_DELIVERY')], limit=1)
            if not product:
                product = self.env['product.product'].sudo().create({
                    'name': 'Servicio de Envío (WanGO)',
                    'type': 'service',
                    'default_code': 'WANGO_DELIVERY',
                    'sale_ok': True,
                    'purchase_ok': False,
                })
            carrier = self.env['delivery.carrier'].sudo().create({
                'name': name,
                'product_id': product.id,
                'delivery_type': 'fixed',
                'fixed_price': 0.0,
                'wango_delivery_type': delivery_type,
            })
        return carrier

    def _set_wango_delivery_line(self, cost, description):
        """Crea o actualiza la línea de venta de costo de envío usando el transportista nativo de Odoo."""
        self.ensure_one()
        
        # 1. Determinar el nombre del transportista según la modalidad
        carrier_name = ''
        if self.delivery_type == 'store_pickup':
            carrier_name = 'Retiro en tienda (WanGO)'
        elif self.delivery_type == 'home_delivery':
            carrier_name = 'Despacho a domicilio (WanGO)'
        elif self.delivery_type == 'agency_shipping':
            carrier_name = 'Recibir en agencia (WanGO)'
        else:
            carrier_name = 'Servicio de envío (WanGO)'
            
        # 2. Buscar o crear el carrier nativo
        carrier = self._get_or_create_wango_carrier(self.delivery_type, carrier_name)
        
        # 3. Guardar el carrier en el pedido (campo nativo)
        self.write({'carrier_id': carrier.id})
        
        # 4. Usar el método nativo de Odoo para crear o actualizar la línea de envío
        self.set_delivery_line(carrier, cost)
        
        # 5. Personalizar la descripción de la línea de venta generada para mayor claridad
        delivery_line = self.order_line.filtered(lambda l: l.is_delivery)
        if delivery_line:
            delivery_line.write({'name': description})
            
        # Forzar el cálculo del total del pedido
        self._amount_all()

    def action_confirm(self):
        """
        Sobrescribe confirmación de orden de venta para validar stock
        y crear el envío wango.shipment correspondiente.
        """
        for order in self:
            carrier = order.carrier_id
            if carrier:
                delivery_type = carrier.wango_delivery_type
                # Validar stock en la sucursal de retiro antes de confirmar (solo si tiene almacén asignado)
                if delivery_type == 'store_pickup' and carrier.store_branch_id and carrier.store_branch_id.warehouse_id:
                    errors = order.check_cart_stock_wango(carrier.store_branch_id.warehouse_id)
                    if errors:
                        raise UserError("\n".join(errors))
            
            # Confirmar orden de venta nativa
            res = super(SaleOrder, order).action_confirm()
            
            # Generar guía de despacho para cualquier entrega WanGO
            if order.carrier_id and order.carrier_id.wango_delivery_type:
                order._create_wango_shipment_from_order()
                
        return res

    def _create_wango_shipment_from_order(self):
        """Crea el registro de envío (wango.shipment) y asocia los paquetes correspondientes."""
        self.ensure_one()
        if self.wango_shipment_id:
            return self.wango_shipment_id
        
        # Obtener remitente (compañía) y destinatario (dirección envío)
        sender = self.company_id.partner_id
        recipient = self.partner_shipping_id or self.partner_id
        
        # Dirección de origen y destino
        origin_addr = sender.contact_address or 'Almacén Principal'
        dest_addr = recipient.contact_address or 'Dirección Cliente'
        
        carrier = self.carrier_id
        delivery_type = carrier.wango_delivery_type if carrier else 'home_delivery'

        # Crear Shipment
        shipment_vals = {
            'sender_id': sender.id,
            'recipient_id': recipient.id,
            'delivery_type': delivery_type,
            'origin_address': origin_addr,
            'destination_address': dest_addr,
            'store_branch_id': self.store_branch_id.id if self.store_branch_id else False,
            'agency_id': self.agency_id.id if self.agency_id else False,
            'destination_agency_id': self.agency_id.id if self.agency_id else False,
            'delivery_department_id': self.delivery_department_id.id if self.delivery_department_id else False,
            'delivery_province_id': self.delivery_province_id.id if self.delivery_province_id else False,
            'delivery_district_id': self.delivery_district_id.id if self.delivery_district_id else False,
            'payment_mode': 'prepaid',
            'price': self.shipping_cost or self.amount_delivery or 0.0,
            'state': 'registered',
        }
        shipment = self.env['wango.shipment'].create(shipment_vals)
        
        # Guardar la relación en la orden de venta
        self.write({'wango_shipment_id': shipment.id})
        
        # Crear Paquete consolidado
        weight = sum(line.product_id.weight * line.product_uom_qty for line in self.order_line if not line.is_delivery and line.product_id)
        volume = sum(line.product_id.volume * line.product_uom_qty for line in self.order_line if not line.is_delivery and line.product_id)
        
        self.env['wango.package'].create({
            'shipment_id': shipment.id,
            'weight': max(weight, 0.1),
            'description': _('Pedido E-Commerce %s') % self.name,
            'width': 30.0,
            'height': 30.0,
            'length': 30.0,
        })
        
        # Registrar en bitácora el ID de envío para referencia futura
        self.message_post(body=_("Se ha generado la guía de despacho y PIN de retiro: <a href='/web#id=%s&model=wango.shipment&view_type=form'>%s</a> (PIN: <b>%s</b>)") % (shipment.id, shipment.name, shipment.pickup_pin))
        return shipment


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'currency_id' not in vals or not vals.get('currency_id'):
                order_id = vals.get('order_id')
                if order_id:
                    order = self.env['sale.order'].browse(order_id)
                    if order and order.currency_id:
                        vals['currency_id'] = order.currency_id.id
        return super(SaleOrderLine, self).create(vals_list)
