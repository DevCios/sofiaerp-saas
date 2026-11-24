# -*- coding: utf-8 -*-
import json
import logging
import requests
from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

MP_PREFERENCE_API = "https://api.mercadopago.com/checkout/preferences"


class SofiaCheckoutController(http.Controller):

    @http.route('/checkout/process_payment', type='json', auth='public', methods=['POST'], csrf=False)
    def checkout_process_payment(self, **post):
        """
        Recibe la orden de suscripción configurada desde el frontend,
        registra o actualiza el partner fiscal peruano en Odoo y genera
        la preferencia de pago en Mercado Pago (Checkout Pro / Transparente).
        """
        try:
            plan = post.get('plan', 'pyme-pro')
            billing = post.get('billing', 'anual')
            users = int(post.get('users', 1))
            client_name = (post.get('client_name') or '').strip()
            email = (post.get('email') or '').strip().lower()
            phone = (post.get('phone') or '').strip()
            company_name = (post.get('company_name') or '').strip()
            fiscal_id = (post.get('fiscal_id') or '').strip()
            subdomain = (post.get('subdomain') or '').strip().lower()
            address = (post.get('address') or '').strip()
            city = (post.get('city') or '').strip()
            region = (post.get('region') or '').strip()
            amount_total = float(post.get('amount_total', 0.0))

            if not email or not fiscal_id:
                return {
                    'status': 'error',
                    'message': _("Debe ingresar un correo electrónico y número de RUC/DNI válidos.")
                }

            # 1. Registrar o actualizar el Partner en Odoo
            Partner = request.env['res.partner'].sudo()
            partner = Partner.search([('vat', '=', fiscal_id)], limit=1)
            if not partner and email:
                partner = Partner.search([('email', '=', email)], limit=1)

            country_pe = request.env.ref('base.pe', raise_if_not_found=False)
            partner_vals = {
                'name': company_name or client_name,
                'is_company': len(fiscal_id) == 11,
                'vat': fiscal_id,
                'email': email,
                'phone': phone,
                'street': address,
                'city': city,
                'comment': f"Subdominio solicitado: {subdomain}.sofiaerp.com | Plan: {plan} | Facturación: {billing} | Usuarios: {users}"
            }
            if country_pe:
                partner_vals['country_id'] = country_pe.id

            if partner:
                partner.write(partner_vals)
            else:
                partner = Partner.create(partner_vals)

            # 2. Registrar Orden de Venta en Odoo para Control de Suscripciones y Facturación
            sale_order = None
            if 'sale.order' in request.env:
                try:
                    product_code_map = {
                        'emprendedor': 'SOFIA-PLAN-EMP',
                        'pyme-pro': 'SOFIA-PLAN-PRO',
                        'corporativo': 'SOFIA-PLAN-CORP',
                    }
                    product_code = product_code_map.get(plan, 'SOFIA-PLAN-PRO')
                    product = request.env['product.product'].sudo().search([('default_code', '=', product_code)], limit=1)
                    
                    if product:
                        unit_rate = (14.90 if plan == 'pyme-pro' else (9.90 if plan == 'emprendedor' else 19.90)) if billing == 'anual' else (16.90 if plan == 'pyme-pro' else (11.90 if plan == 'emprendedor' else 21.90))
                        order_lines = [
                            (0, 0, {
                                'product_id': product.id,
                                'name': f"{product.name} ({users} usuario{'s' if users > 1 else ''} — Facturación {billing.capitalize()})",
                                'product_uom_qty': users * (12 if billing == 'anual' else 1),
                                'price_unit': unit_rate,
                            })
                        ]
                        if impl_cost > 0:
                            impl_code = 'SOFIA-SRV-ACOMP' if impl_cost == 150 else 'SOFIA-SRV-CONSULT'
                            impl_prod = request.env['product.product'].sudo().search([('default_code', '=', impl_code)], limit=1)
                            if impl_prod:
                                order_lines.append((0, 0, {
                                    'product_id': impl_prod.id,
                                    'name': impl_prod.name,
                                    'product_uom_qty': 1,
                                    'price_unit': impl_cost,
                                }))

                        sale_order = request.env['sale.order'].sudo().create({
                            'partner_id': partner.id,
                            'client_order_ref': f"SUB-{subdomain.upper()}",
                            'note': f"Suscripción SaaS SOFIA ERP | Subdominio: https://{subdomain}.sofiaerp.com | Plan: {plan} | Modalidad: {billing}",
                            'order_line': order_lines,
                        })
                        _logger.info("Orden de Venta creada exitosamente: %s para partner %s", sale_order.name, partner.name)
                except Exception as ex:
                    _logger.warning("No se pudo crear sale.order: %s", ex)

            # 3. Registrar Lead en CRM si el módulo está instalado
            if 'crm.lead' in request.env:
                try:
                    request.env['crm.lead'].sudo().create({
                        'name': f"Nueva Suscripción: {plan.upper()} - {company_name or client_name}",
                        'partner_id': partner.id,
                        'contact_name': client_name,
                        'email_from': email,
                        'phone': phone,
                        'expected_revenue': amount_total,
                        'description': f"Subdominio: {subdomain}.sofiaerp.com\nPlan: {plan}\nModalidad: {billing}\nUsuarios: {users}\nTotal: S/ {amount_total:.2f}\nOrden de Venta: {sale_order.name if sale_order else 'N/A'}"
                    })
                except Exception as ex:
                    _logger.warning("No se pudo registrar lead en CRM: %s", ex)

            # 4. Consultar proveedor de pago Mercado Pago en Odoo
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://sofiaerp.com').rstrip('/')
            mp_provider = None
            if 'payment.provider' in request.env:
                mp_provider = request.env['payment.provider'].sudo().search([
                    ('code', '=', 'mercadopago'),
                    ('state', 'in', ['enabled', 'test'])
                ], limit=1)

            # 4. Generar preferencia real en Mercado Pago si tiene credenciales configuradas
            if mp_provider and hasattr(mp_provider, 'mercadopago_access_token') and mp_provider.mercadopago_access_token:
                access_token = mp_provider.mercadopago_access_token
                is_sandbox = mp_provider.state != 'enabled'

                preference_payload = {
                    "items": [
                        {
                            "id": f"SOFIA-{plan.upper()}",
                            "title": f"Suscripción SOFIA ERP — Plan {plan.capitalize()} ({users} usuario{'s' if users > 1 else ''} - {billing.capitalize()})",
                            "description": f"Instancia dedicada https://{subdomain}.sofiaerp.com con Facturación Electrónica SUNAT",
                            "quantity": 1,
                            "currency_id": "PEN",
                            "unit_price": round(amount_total, 2)
                        }
                    ],
                    "payer": {
                        "name": client_name,
                        "email": email,
                        "phone": {
                            "area_code": "51",
                            "number": phone
                        },
                        "identification": {
                            "type": "RUC" if len(fiscal_id) == 11 else "DNI",
                            "number": fiscal_id
                        },
                        "address": {
                            "street_name": address
                        }
                    },
                    "back_urls": {
                        "success": f"{base_url}/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}",
                        "failure": f"{base_url}/checkout/failure?plan={plan}",
                        "pending": f"{base_url}/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}&status=pending"
                    },
                    "auto_return": "approved",
                    "external_reference": f"SOFIA-SUB-{subdomain}-{fiscal_id}",
                    "statement_descriptor": "SOFIA ERP SAAS",
                    "metadata": {
                        "subdomain": subdomain,
                        "plan": plan,
                        "billing": billing,
                        "users": users,
                        "partner_id": partner.id,
                        "fiscal_id": fiscal_id,
                        "email": email
                    }
                }

                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }

                try:
                    resp = requests.post(MP_PREFERENCE_API, headers=headers, json=preference_payload, timeout=15)
                    resp_json = resp.json()
                    
                    if resp.status_code in [200, 201]:
                        checkout_url = resp_json.get('sandbox_init_point') if is_sandbox else resp_json.get('init_point')
                        return {
                            'status': 'success',
                            'provider': 'mercadopago',
                            'redirect_url': checkout_url,
                            'preference_id': resp_json.get('id')
                        }
                    else:
                        _logger.error("Error al generar preferencia en Mercado Pago: %s", resp.text)
                except Exception as exc:
                    _logger.error("Excepción comunicando con Mercado Pago API: %s", exc)

            # 5. Modo de Contingencia / Demostración si aún no se han configurado API keys de producción
            return {
                'status': 'demo_success',
                'message': _("Solicitud de suscripción registrada exitosamente."),
                'redirect_url': f"/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}&mode=demo"
            }

        except Exception as e:
            _logger.exception("Error procesando checkout: %s", e)
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/checkout/success', type='http', auth='public', website=True)
    def checkout_success(self, **kwargs):
        """ Pantalla de Confirmación de Pago y Aprovisionamiento """
        return request.render('sofia_website_theme.checkout_success_page', {
            'subdomain': kwargs.get('subdomain', 'miempresa'),
            'plan': kwargs.get('plan', 'pyme-pro'),
            'users': kwargs.get('users', '1'),
            'billing': kwargs.get('billing', 'anual'),
            'mode': kwargs.get('mode', 'live'),
        })

    @http.route('/checkout/failure', type='http', auth='public', website=True)
    def checkout_failure(self, **kwargs):
        """ Pantalla de Pago Rechazado o Cancelado """
        return request.render('sofia_website_theme.checkout_failure_page', {
            'plan': kwargs.get('plan', 'pyme-pro'),
        })
