# -*- coding: utf-8 -*-
import hashlib
import hmac
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


def trigger_control_plane_provisioning(subdomain, company_name, admin_email, plan_code="SOFIA-PLAN-PRO", billing_cycle="MONTHLY", users_count=1):
    """
    Invoca la API del Control Plane de SOFIA ERP (FastAPI) para aprovisionar
    de forma inmediata la base de datos PostgreSQL aislada y filestore del tenant.
    """
    control_plane_url = os.getenv("CONTROL_PLANE_API_URL", "http://control-plane-api:8000").rstrip("/")
    internal_key = os.getenv("INTERNAL_SERVICE_KEY", "sofia_internal_mesh_key_change_in_prod")
    endpoint = f"{control_plane_url}/api/v1/tenants"

    # Generar clave temporal robusta para el administrador del tenant
    chars = string.ascii_letters + string.digits
    temp_password = "Sofia" + "".join(secrets.choice(chars) for _ in range(8)) + "#"

    try:
        safe_users = max(1, int(users_count or 1))
    except (ValueError, TypeError):
        safe_users = 1

    payload = {
        "name": company_name or f"Empresa {subdomain.capitalize()}",
        "slug": subdomain.lower().strip(),
        "runtime_mode": "SHARED_PROTECTED",
        "admin_email": admin_email.lower().strip(),
        "admin_password": temp_password,
        "plan_code": plan_code or "SOFIA-PLAN-PRO",
        "billing_cycle": "ANNUAL" if str(billing_cycle).lower() in ("anual", "annual") else "MONTHLY",
        "users_count": safe_users,
    }

    try:
        _logger.info("SOFIA ERP: Solicitando aprovisionamiento automático a Control Plane para tenant '%s'...", subdomain)
        resp = requests.post(
            endpoint,
            json=payload,
            headers={"X-Internal-Service-Key": internal_key},
            timeout=12,
        )
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
            plan = (post.get('plan') or 'pyme-pro').strip().lower()
            if plan not in ('emprendedor', 'pyme-pro', 'corporativo'):
                plan = 'pyme-pro'
            billing = (post.get('billing') or 'anual').strip().lower()
            if billing not in ('anual', 'mensual'):
                billing = 'anual'
            users = max(1, min(500, int(post.get('users', 1))))
            client_name = (post.get('client_name') or '').strip()
            email = (post.get('email') or '').strip().lower()
            phone = (post.get('phone') or '').strip()
            company_name = (post.get('company_name') or '').strip()
            fiscal_id = (post.get('fiscal_id') or '').strip()
            subdomain = (post.get('subdomain') or '').strip().lower()
            address = (post.get('address') or '').strip()
            city = (post.get('city') or '').strip()
            region = (post.get('region') or '').strip()

            # SEGURIDAD: Recalcular el monto total 100% en el servidor (nunca confiar en amount_total del cliente)
            raw_impl_cost = float(post.get('impl_cost', 0.0))
            impl_cost = raw_impl_cost if raw_impl_cost in (0.0, 150.0, 350.0) else 0.0
            server_rates = {
                'emprendedor': {'anual': 9.90, 'mensual': 11.90},
                'pyme-pro': {'anual': 14.90, 'mensual': 16.90},
                'corporativo': {'anual': 19.90, 'mensual': 21.90},
            }
            unit_rate_srv = server_rates[plan][billing]
            months_srv = 12 if billing == 'anual' else 1
            amount_total = round((unit_rate_srv * users * months_srv) + impl_cost, 2)

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
            def _icp(key, default=''):
                rec = request.env['ir.config_parameter'].sudo().search([('key', '=', key)], limit=1)
                return rec.value if (rec and rec.value) else default

            base_url = _icp('web.base.url', 'https://sofiaerp.com').rstrip('/')
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
                access_token = _icp('mercadopago.access_token') or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
                if access_token and (access_token.startswith('TEST-') or _icp('mercadopago.sandbox', '').lower() in ['true', '1']):
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

    def _get_mp_access_token(self):
        """Obtiene el Access Token de Mercado Pago desde payment.provider, ir.config_parameter o ENV."""
        access_token = None
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
        if not access_token:
            rec = request.env['ir.config_parameter'].sudo().search([('key', '=', 'mercadopago.access_token')], limit=1)
            access_token = (rec.value if rec else '') or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
        return access_token

    def _verify_mp_webhook_signature(self, data_id):
        """
        Valida la firma HMAC-SHA256 (x-signature) de Mercado Pago en modo fail-closed.
        """
        rec = request.env['ir.config_parameter'].sudo().search([('key', '=', 'mercadopago.webhook_secret')], limit=1)
        webhook_secret = (rec.value if rec else '') or os.getenv('MERCADOPAGO_WEBHOOK_SECRET')
        if not webhook_secret:
            _logger.error("SOFIA ERP MP webhook: MERCADOPAGO_WEBHOOK_SECRET no configurado (rechazado fail-closed).")
            return False

        x_signature = request.httprequest.headers.get('x-signature', '')
        x_request_id = request.httprequest.headers.get('x-request-id', '')
        if not x_signature:
            return False

        parts = {}
        for item in x_signature.split(','):
            if '=' in item:
                k, v = item.split('=', 1)
                parts[k.strip()] = v.strip()

        ts = parts.get('ts')
        v1 = parts.get('v1')
        if not ts or not v1:
            return False

        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(webhook_secret.encode('utf-8'), manifest.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)

    def _verify_mp_payment_approved(self, payment_id):
        """
        Consulta server-to-server la API oficial de Mercado Pago para verificar
        que el pago existe y tiene status == 'approved'.
        """
        if not payment_id or not str(payment_id).isdigit():
            return None

        access_token = self._get_mp_access_token()
        if not access_token:
            return None

        try:
            resp = requests.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                payment_data = resp.json()
                if payment_data.get('status') == 'approved':
                    return payment_data
        except Exception as exc:
            _logger.exception("SOFIA ERP: Error verificando pago %s en Mercado Pago: %s", payment_id, exc)
        return None

    @http.route('/checkout/webhook/mercadopago', type='http', auth='none', methods=['POST'], csrf=False)
    def checkout_webhook_mercadopago(self, **post):
        """
        Webhook HTTP REST oficial de Mercado Pago (v1/v2):
        1. Recibe POST JSON plano (type='http', compatible con REST estándar).
        2. Valida firma HMAC x-signature si hay secreto configurado.
        3. Verifica el pago directamente contra la API de Mercado Pago (status == 'approved').
        4. Dispara el aprovisionamiento automático del tenant en Control Plane / Celery.
        """
        try:
            raw_body = request.httprequest.get_data(as_text=True) or ''
            data = json.loads(raw_body) if raw_body else {}
        except Exception:
            data = {}

        action = data.get('action') or data.get('type') or request.params.get('type') or request.params.get('topic')
        payment_id = (
            (data.get('data') or {}).get('id')
            or request.params.get('data.id')
            or request.params.get('id')
            or data.get('id')
        )

        _logger.info("SOFIA ERP: Webhook Mercado Pago recibido (action=%s, payment_id=%s)", action, payment_id)

        if payment_id and not self._verify_mp_webhook_signature(payment_id):
            _logger.warning("SOFIA ERP: Firma x-signature inválida en webhook para payment_id=%s", payment_id)
            return Response(json.dumps({"error": "invalid_signature"}), status=401, mimetype='application/json')

        if action in ['payment.created', 'payment.updated', 'payment'] and payment_id:
            payment_data = self._verify_mp_payment_approved(payment_id)
            if payment_data:
                metadata = payment_data.get('metadata') or {}
                subdomain = (metadata.get('subdomain') or '').strip().lower()
                email = (metadata.get('email') or '').strip().lower()
                company_name = metadata.get('company_name')
                plan = metadata.get('plan', 'pyme-pro')

                _logger.info("SOFIA ERP: Pago %s APROBADO para subdominio '%s'", payment_id, subdomain)
                if subdomain and email:
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
                        plan_code=plan_code,
                        billing_cycle=metadata.get('billing', 'anual'),
                    )

        return Response(json.dumps({"status": "ok"}), status=200, mimetype='application/json')

    @http.route('/checkout/success', type='http', auth='public', website=True)
    def checkout_success(self, **kwargs):
        """
        Pantalla de Confirmación de Pago y Aprovisionamiento Seguro:
        NUNCA confía en parámetros manipulables de la URL para crear un tenant.
        Exige verificación real server-to-server del payment_id ante Mercado Pago.
        """
        payment_id = kwargs.get('payment_id') or kwargs.get('collection_id')
        mode = kwargs.get('mode', 'live')
        subdomain = (kwargs.get('subdomain') or '').strip().lower()
        plan = kwargs.get('plan', 'pyme-pro')
        users = kwargs.get('users', '1')
        billing = kwargs.get('billing', 'anual')
        email = (kwargs.get('email') or '').strip()
        company = (kwargs.get('company') or '').strip()

        provisioning_result = None
        verified_payment = self._verify_mp_payment_approved(payment_id) if payment_id else None

        if verified_payment:
            # Usar metadata confiable proveniente directamente del pago aprobado en Mercado Pago
            metadata = verified_payment.get('metadata') or {}
            subdomain = (metadata.get('subdomain') or subdomain).strip().lower()
            email = (metadata.get('email') or email).strip().lower()
            company = metadata.get('company_name') or company
            plan = metadata.get('plan') or plan
            users = str(metadata.get('users') or users)
            billing = metadata.get('billing') or billing

            if subdomain:
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
                    plan_code=plan_code,
                    billing_cycle=billing,
                    users_count=users,
                )
        else:
            # Solo permitir modo demo si está explícitamente habilitado en parámetros del sistema
            demo_rec = request.env['ir.config_parameter'].sudo().search([('key', '=', 'sofia.allow_demo_checkout')], limit=1)
            allow_demo = ((demo_rec.value if demo_rec else 'False') or 'False').lower() in ['true', '1']
            if mode == 'demo' and allow_demo and subdomain:
                plan_code_map = {
                    'emprendedor': 'SOFIA-PLAN-EMP',
                    'pyme-pro': 'SOFIA-PLAN-PRO',
                    'corporativo': 'SOFIA-PLAN-CORP',
                }
                provisioning_result = trigger_control_plane_provisioning(
                    subdomain=subdomain,
                    company_name=company or f"Empresa {subdomain.capitalize()}",
                    admin_email=email or f"admin@{subdomain}.sofiaerp.com",
                    plan_code=plan_code_map.get(plan, 'SOFIA-PLAN-PRO'),
                )
            else:
                _logger.warning(
                    "SOFIA ERP: Acceso a /checkout/success sin pago verificado (payment_id=%s, subdomain=%s). Bloqueado.",
                    payment_id,
                    subdomain,
                )
                return request.redirect('/precios')

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

    @http.route('/cuenta-suspendida', type='http', auth='public', website=True)
    def account_suspended(self, **kwargs):
        """ Pantalla elegante de suspensión por vencimiento de periodo de gracia """
        tenant_host = (kwargs.get('tenant') or '').strip()
        return request.render('sofia_website_theme.account_suspended_page', {
            'tenant_host': tenant_host,
        })

    @http.route('/mi-cuenta', type='http', auth='user', website=True)
    def my_account_portal(self, **kwargs):
        """ Portal de Autogestión del Cliente (requiere autenticación): Upgrade de Plan, Usuarios Extra y Dominio Propio """
        return request.render('sofia_website_theme.my_account_portal_page', {
            'tenant': (kwargs.get('tenant') or '').strip(),
        })

    @http.route('/terminos', type='http', auth='public', website=True)
    def terms_of_service(self, **kwargs):
        return request.render('sofia_website_theme.terms_page', {})

    @http.route('/privacidad', type='http', auth='public', website=True)
    def privacy_policy(self, **kwargs):
        return request.render('sofia_website_theme.privacy_page', {})

    @http.route(['/verticales/<string:slug>', '/aplicaciones/<string:slug>'], type='http', auth='public', website=True)
    def vertical_or_app_detail(self, slug, **kwargs):
        catalog = {
            'bodegas': ('Bodegas y Minimarkets', 'Punto de Venta ultra rápido con lector de códigos, Yape/Plin, control de stock y Boletas SUNAT al instante.'),
            'ferreterias': ('Ferreterías y Materiales', 'Control multi-almacén, ventas por unidad/caja/metro, cotizaciones rápidas, Guías GRE y Facturación SUNAT.'),
            'retail': ('Retail y Tiendas', 'Gestión de tiendas, POS omnicanal, listas de precios, inventario en tiempo real e integración con Mercado Wanka.'),
            'comercio-electronico': ('Comercio Electrónico', 'Tienda online conectada a tu inventario y facturación SUNAT, con pagos Mercado Pago y envío a todo el Perú.'),
            'boticas': ('Boticas y Farmacias', 'Control por lotes, fechas de vencimiento, ventas fraccionadas en mostrador y emisión SUNAT inmediata.'),
            'odontologia': ('Clínicas y Odontología', 'Agenda de citas, historial comercial de pacientes, cobranzas y comprobantes electrónicos SUNAT.'),
            'servicios': ('Empresas de Servicios', 'Proyectos, cotizaciones, contratos recurrentes, partes de horas y facturación automatizada.'),
            'restaurante': ('Restaurantes y Cafés', 'Toma de pedidos en mesa, comandas a cocina, división de cuentas, caja rápida y Boletas/Facturas SUNAT.'),
            'manufactura': ('Manufactura e Industria', 'Listas de materiales (BOM), órdenes de producción, control de calidad, costos y Kardex valorizado.'),
            'gestion-de-flotas': ('Gestión de Flotas y Transporte', 'Control de vehículos, mantenimientos, combustible y Guías de Remisión Electrónica GRE 09/31.'),
            'recursos-humanos': ('Recursos Humanos', 'Gestión de colaboradores, asistencias, contratos, vacaciones y control interno.'),
            'contabilidad': ('Contabilidad & SIRE SUNAT', 'Plan Contable General Empresarial (PCGE), libros PLE, RVIE/RCE SIRE, detracciones SPOT y retenciones.'),
            'facturacion-electronica': ('Facturación Electrónica SUNAT', 'Emisión UBL 2.1 ilimitada, recuperación automática anti-1033, ticket 80mm y envío por correo/WhatsApp.'),
            'guias-remision': ('Guías de Remisión Electrónica (GRE)', 'Emisión oficial de Guías Remitente y Transportista conectada a tu inventario y despachos.'),
            'inventario': ('Inventario y Kardex Valorizado', 'Multi-almacén, trazabilidad por lotes/series, transferencias y reportes PLE 12.1 / 13.1.'),
            'ventas': ('CRM y Ventas', 'Embudo comercial, cotizaciones en 1 clic, seguimiento de clientes y facturación directa.'),
            'compras': ('Compras y Proveedores', 'Órdenes de compra, control de recepción, cuentas por pagar y validación de RUC SUNAT.'),
            'gastos': ('Gestión de Gastos', 'Rendición de gastos, caja chica, aprobación por jefatura y registro contable integrado.'),
        }
        clean_slug = (slug or '').strip().lower()
        title, summary = catalog.get(
            clean_slug,
            (clean_slug.replace('-', ' ').title() or 'Empresas en Perú', 'Solución integral en la nube con Facturación Electrónica SUNAT, inventario y gestión financiera.'),
        )
        is_app = request.httprequest.path.startswith('/aplicaciones/')
        return request.render('sofia_website_theme.vertical_detail_page', {
            'section_badge': 'Aplicación SOFIA ERP' if is_app else 'Vertical de Negocio Perú',
            'item_title': title,
            'item_summary': summary,
        })
