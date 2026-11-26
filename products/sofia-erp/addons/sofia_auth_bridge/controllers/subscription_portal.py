# -*- coding: utf-8 -*-
import logging
import os
import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SOFIA_CENTRAL_PORTAL_URL = "https://sofiaerp.com"


class SofiaTenantSubscriptionPortal(http.Controller):
    """
    Panel de autogestión de suscripción SaaS dentro de cada Tenant (/my/subscription).
    Accesible ESTRICTAMENTE para Administradores del Tenant (base.group_system).
    Nunca visible para clientes finales del portal ni para empleados operativos.
    """

    @http.route(['/my/subscription', '/mi-suscripcion'], type='http', auth='user')
    def tenant_my_subscription(self, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            return request.redirect('/my')

        db_name = request.env.cr.dbname
        slug = db_name.replace('sofia_tenant_', '').replace('_', '-')
        company = request.env.company

        # Conteo real de usuarios internos activos (excluyendo OdooBot id=1)
        active_users = request.env['res.users'].sudo().search_count([
            ('active', '=', True),
            ('share', '=', False),
            ('id', '!=', 1),
        ])

        icp = request.env['ir.config_parameter'].sudo()
        base_url = (
            icp.get_param('sofia.control_plane_url')
            or os.getenv('SOFIA_CONTROL_PLANE_URL', 'http://control-plane-api:8000')
        ).rstrip('/')

        # Valores por defecto seguros (resiliencia offline)
        plan_code = icp.get_param('sofia.entitlements.plan_code', 'PYME-PRO')
        tier = 'PROFESSIONAL'
        sub_status = 'ACTIVE'
        is_grace_period = False
        try:
            max_users = int(icp.get_param('sofia.entitlements.max_users', '5'))
        except ValueError:
            max_users = 5
        storage_gb = 20

        # Consultar estado en vivo al Control Plane por red interna
        try:
            internal_key = os.getenv('INTERNAL_SERVICE_KEY', 'sofia_internal_mesh_key_change_in_prod')
            resp = requests.get(
                f"{base_url}/api/v1/tenants/by-db/{db_name}/entitlements",
                headers={"X-Internal-Service-Key": internal_key},
                timeout=3,
            )
            if resp.status_code == 200:
                data = resp.json()
                limits = data.get('limits') or {}
                plan_code = data.get('plan_code') or data.get('tier', plan_code)
                tier = data.get('tier', tier)
                sub_status = data.get('subscription_status', sub_status)
                is_grace_period = bool(data.get('is_grace_period', False))
                max_users = int(limits.get('max_users', max_users))
                storage_gb = int(limits.get('storage_gb', storage_gb))
                slug = data.get('tenant_slug') or slug
        except Exception as exc:
            _logger.warning("No se pudo consultar Control Plane desde /my/subscription: %s", exc)

        # Mapear plan actual al slug comercial de checkout
        plan_lower = str(plan_code or '').lower()
        if 'corp' in plan_lower or tier == 'ENTERPRISE':
            checkout_plan = 'corporativo'
            plan_display = 'Plan Corporativo'
            unit_price = 19.90
        elif 'emp' in plan_lower or tier == 'BASIC':
            checkout_plan = 'emprendedor'
            plan_display = 'Plan Emprendedor'
            unit_price = 9.90
        else:
            checkout_plan = 'pyme-pro'
            plan_display = 'Plan Pyme Pro'
            unit_price = 14.90

        usage_pct = min(100, int((active_users / max_users) * 100)) if max_users > 0 else 0
        central_url = (
            icp.get_param('sofia.central_web_url')
            or os.getenv('SOFIA_CENTRAL_WEB_URL', SOFIA_CENTRAL_PORTAL_URL)
        ).rstrip('/')

        values = {
            'page_name': 'sofia_subscription',
            'tenant_slug': slug,
            'tenant_host': f"{slug}.sofiaerp.com",
            'company_name': company.name or slug.upper(),
            'company_vat': company.vat or '',
            'plan_code': plan_code,
            'plan_display': plan_display,
            'checkout_plan': checkout_plan,
            'unit_price': unit_price,
            'tier': tier,
            'sub_status': sub_status,
            'is_grace_period': is_grace_period,
            'active_users': active_users,
            'max_users': max_users,
            'usage_pct': usage_pct,
            'storage_gb': storage_gb,
            'central_url': central_url,
        }
        return request.render('sofia_auth_bridge.portal_my_subscription', values)
