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

            # 2. Registrar Lead de Suscripción en CRM si el módulo está instalado
            if 'crm.lead' in request.env:
                try:
                    request.env['crm.lead'].sudo().create({
                        'name': f"Nueva Suscripción: {plan.upper()} - {company_name or client_name}",
                        'partner_id': partner.id,
                        'contact_name': client_name,
                        'email_from': email,
                        'phone': phone,
                        'expected_revenue': amount_total,
                        'description': f"Subdominio: {subdomain}.sofiaerp.com\nPlan: {plan}\nModalidad: {billing}\nUsuarios: {users}\nTotal: S/ {amount_total:.2f}"
                    })
                except Exception as ex:
                    _logger.warning("No se pudo registrar lead en CRM: %s", ex)

            # 3. Consultar proveedor de pago Mercado Pago en Odoo
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
