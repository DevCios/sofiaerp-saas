# -*- coding: utf-8 -*-
import json
import logging
import os
import secrets
import string
import requests
from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

MP_PREFERENCE_API = "https://api.mercadopago.com/checkout/preferences"


def trigger_control_plane_provisioning(subdomain, company_name, admin_email, plan_code="SOFIA-PLAN-PRO"):
    """
    Invoca la API del Control Plane de SOFIA ERP (FastAPI) para aprovisionar
    de forma inmediata la base de datos PostgreSQL aislada y filestore del tenant.
    """
    control_plane_url = os.getenv("CONTROL_PLANE_API_URL", "http://control-plane-api:8000").rstrip("/")
    endpoint = f"{control_plane_url}/api/v1/tenants"

    # Generar clave temporal robusta para el administrador del tenant
    chars = string.ascii_letters + string.digits
    temp_password = "Sofia" + "".join(secrets.choice(chars) for _ in range(8)) + "#"

    payload = {
        "name": company_name or f"Empresa {subdomain.capitalize()}",
        "slug": subdomain.lower().strip(),
        "runtime_mode": "SHARED_PROTECTED",
        "admin_email": admin_email.lower().strip(),
        "admin_password": temp_password,
        "plan_code": plan_code or "SOFIA-PLAN-PRO",
    }

    try:
        _logger.info("SOFIA ERP: Solicitando aprovisionamiento automático a Control Plane para tenant '%s'...", subdomain)
        resp = requests.post(endpoint, json=payload, timeout=12)
        if resp.status_code == 201:
            data = resp.json()
            _logger.info("SOFIA ERP: Tenant '%s' aprovisionado exitosamente en Control Plane (ID: %s)", subdomain, data.get('id'))
            return {"success": True, "password": temp_password, "already_exists": False, "data": data}
        elif resp.status_code == 400 and "ya se encuentra en uso" in resp.text:
            _logger.info("SOFIA ERP: Tenant '%s' ya existía en Control Plane.", subdomain)
            return {"success": True, "password": None, "already_exists": True}
        else:
            _logger.error("SOFIA ERP: Control Plane devolvió HTTP %s: %s", resp.status_code, resp.text)
            return {"success": False, "error": resp.text}
    except Exception as ex:
        _logger.error("SOFIA ERP: Error al comunicar con Control Plane API: %s", ex)
        return {"success": False, "error": str(ex)}


class SofiaCheckoutController(http.Controller):

    @http.route('/checkout/check_subdomain', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def checkout_check_subdomain(self, subdomain=None, **kwargs):
        """
        Valida en tiempo real mientras el usuario escribe si el subdominio deseado
        está disponible o ya fue registrado, consultando al Control Plane.
        """
        clean_sub = (subdomain or '').strip().lower()
        if not clean_sub:
            return {'available': False, 'message': 'Ingresa un nombre para tu subdominio.'}

        reserved = [
            "admin", "api", "www", "mail", "smtp", "app", "sofia", "sofiaerp", 
            "control-plane", "portal", "status", "test", "demo", "billing", "auth",
            "root", "support", "soporte", "help", "dev", "staging", "prod"
        ]
        if clean_sub in reserved:
            return {'available': False, 'message': 'Este subdominio es un nombre reservado del sistema.'}

        import re
        if len(clean_sub) < 3 or len(clean_sub) > 63 or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", clean_sub):
            return {'available': False, 'message': 'Debe tener entre 3 y 63 caracteres (solo letras minúsculas, números y guiones).'}

        # 1. Consultar en la base de datos central de Control Plane
        control_plane_url = os.getenv("CONTROL_PLANE_API_URL", "http://control-plane-api:8000").rstrip("/")
        try:
            resp = requests.get(f"{control_plane_url}/api/v1/tenants/check-availability/{clean_sub}", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                return data
        except Exception as e:
            _logger.warning("SOFIA ERP: No se pudo verificar disponibilidad vía Control Plane API (%s), usando fallback local.", e)

        # 2. Fallback local: verificar si ya existe en Odoo en comentarios de partners o notas de pedidos
        domain_str = f"{clean_sub}.sofiaerp.com"
        existing_partner = request.env['res.partner'].sudo().search([('comment', 'ilike', domain_str)], limit=1)
        if existing_partner:
            return {'available': False, 'message': f"El subdominio '{clean_sub}' ya está reservado por otra empresa."}

        return {'available': True, 'message': f"¡Subdominio disponible! https://{clean_sub}.sofiaerp.com"}

    @http.route('/checkout/process_payment', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
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
            impl_cost = float(post.get('impl_cost', 0.0))

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

            # 4. Consultar credenciales de Mercado Pago (desde Odoo payment.provider, ir.config_parameter o ENV)
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://sofiaerp.com').rstrip('/')
            access_token = None
            is_sandbox = False

            if 'payment.provider' in request.env:
                mp_provider = request.env['payment.provider'].sudo().search([
                    ('code', 'in', ['mercadopago', 'mercado_pago']),
                ], limit=1)
                if mp_provider:
                    access_token = (
                        getattr(mp_provider, 'mercado_pago_access_token', None)
                        or getattr(mp_provider, 'mercadopago_access_token', None)
                        or getattr(mp_provider, 'mp_access_token', None)
                    )
                    is_sandbox = (mp_provider.state != 'enabled')

            # Si no está en el provider, buscar en Parámetros del Sistema o Variable de Entorno
            if not access_token:
                access_token = request.env['ir.config_parameter'].sudo().get_param('mercadopago.access_token') or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
                if access_token and (access_token.startswith('TEST-') or request.env['ir.config_parameter'].sudo().get_param('mercadopago.sandbox', '').lower() in ['true', '1']):
                    is_sandbox = True

            # Generar preferencia real en Mercado Pago si tiene credenciales configuradas
            if access_token:
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
                        "success": f"{base_url}/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}&email={email}&company={company_name}",
                        "failure": f"{base_url}/checkout/failure?plan={plan}",
                        "pending": f"{base_url}/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}&email={email}&company={company_name}&status=pending"
                    },
                    "auto_return": "approved",
                    "notification_url": f"{base_url}/checkout/webhook/mercadopago",
                    "external_reference": f"SOFIA-SUB-{subdomain}-{fiscal_id}",
                    "statement_descriptor": "SOFIA ERP SAAS",
                    "metadata": {
                        "subdomain": subdomain,
                        "plan": plan,
                        "billing": billing,
                        "users": users,
                        "partner_id": partner.id,
                        "fiscal_id": fiscal_id,
                        "email": email,
                        "company_name": company_name or client_name
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
                'redirect_url': f"/checkout/success?subdomain={subdomain}&plan={plan}&users={users}&billing={billing}&email={email}&company={company_name}&mode=demo"
            }

        except Exception as e:
            _logger.exception("Error procesando checkout: %s", e)
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/checkout/webhook/mercadopago', type='json', auth='none', methods=['POST'], csrf=False)
    def checkout_webhook_mercadopago(self, **post):
        """
        Webhook asíncrono de Mercado Pago:
        Verifica el estado del pago mediante la API oficial de Mercado Pago
        y dispara el aprovisionamiento automático del tenant en Celery si está aprobado.
        """
        try:
            data = json.loads(request.httprequest.data) if request.httprequest.data else {}
        except Exception:
            data = {}

        _logger.info("SOFIA ERP: Webhook Mercado Pago recibido: %s", data)
        action = data.get('action') or data.get('type')
        payment_id = data.get('data', {}).get('id') or data.get('id')

        if action in ['payment.created', 'payment.updated', 'payment'] and payment_id:
            try:
                access_token = request.env['ir.config_parameter'].sudo().get_param('mercadopago.access_token') or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
                if not access_token:
                    mp_provider = request.env['payment.provider'].sudo().search([('code', 'in', ['mercadopago', 'mercado_pago'])], limit=1)
                    if mp_provider:
                        access_token = getattr(mp_provider, 'mercado_pago_access_token', None)

                if access_token:
                    resp = requests.get(
                        f"https://api.mercadopago.com/v1/payments/{payment_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        payment_data = resp.json()
                        status = payment_data.get('status')
                        metadata = payment_data.get('metadata', {})
                        subdomain = metadata.get('subdomain')
                        email = metadata.get('email')
                        company_name = metadata.get('company_name')
                        plan = metadata.get('plan', 'pyme-pro')

                        _logger.info("SOFIA ERP: Pago %s con estado '%s' para subdominio '%s'", payment_id, status, subdomain)
                        if status == 'approved' and subdomain and email:
                            plan_code_map = {
                                'emprendedor': 'SOFIA-PLAN-EMP',
                                'pyme-pro': 'SOFIA-PLAN-PRO',
                                'corporativo': 'SOFIA-PLAN-CORP',
                            }
                            plan_code = plan_code_map.get(plan, 'SOFIA-PLAN-PRO')
                            trigger_control_plane_provisioning(
                                subdomain=subdomain,
                                company_name=company_name,
                                admin_email=email,
                                plan_code=plan_code
                            )
            except Exception as e:
                _logger.exception("SOFIA ERP: Error en webhook Mercado Pago: %s", e)

        return Response("OK", status=200)

    @http.route('/checkout/success', type='http', auth='public', website=True)
    def checkout_success(self, **kwargs):
        """ Pantalla de Confirmación de Pago y Aprovisionamiento """
        subdomain = (kwargs.get('subdomain') or '').strip().lower()
        plan = kwargs.get('plan', 'pyme-pro')
        users = kwargs.get('users', '1')
        billing = kwargs.get('billing', 'anual')
        mode = kwargs.get('mode', 'live')
        email = (kwargs.get('email') or '').strip()
        company = (kwargs.get('company') or '').strip()

        collection_status = kwargs.get('collection_status') or kwargs.get('status')
        is_approved = (collection_status == 'approved') or (mode == 'demo') or not collection_status

        provisioning_result = None
        if subdomain and is_approved:
            plan_code_map = {
                'emprendedor': 'SOFIA-PLAN-EMP',
                'pyme-pro': 'SOFIA-PLAN-PRO',
                'corporativo': 'SOFIA-PLAN-CORP',
            }
            plan_code = plan_code_map.get(plan, 'SOFIA-PLAN-PRO')
            provisioning_result = trigger_control_plane_provisioning(
                subdomain=subdomain,
                company_name=company or f"Empresa {subdomain.capitalize()}",
                admin_email=email or f"admin@{subdomain}.sofiaerp.com",
                plan_code=plan_code
            )

        temp_password = provisioning_result.get('password') if provisioning_result else None
        already_exists = provisioning_result.get('already_exists') if provisioning_result else False
        login_url = f"https://{subdomain}.sofiaerp.com" if subdomain else "https://sofiaerp.com/login"

        return request.render('sofia_website_theme.checkout_success_page', {
            'subdomain': subdomain or 'miempresa',
            'plan': plan,
            'users': users,
            'billing': billing,
            'mode': mode,
            'admin_email': email,
            'temp_password': temp_password,
            'already_exists': already_exists,
            'login_url': login_url,
        })

    @http.route('/checkout/failure', type='http', auth='public', website=True)
    def checkout_failure(self, **kwargs):
        """ Pantalla de Pago Rechazado o Cancelado """
        return request.render('sofia_website_theme.checkout_failure_page', {
            'plan': kwargs.get('plan', 'pyme-pro'),
        })

