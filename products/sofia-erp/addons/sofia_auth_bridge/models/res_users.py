# -*- coding: utf-8 -*-
import logging
import os
import time
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ENTITLEMENT_CACHE_TTL_SECONDS = 600  # 10 minutos de caché local para resiliencia offline
CORPORATE_MASTER_DB = "sofia_tenant_sofiaerp"


class ResUsers(models.Model):
    _inherit = 'res.users'

    sofia_user_id = fields.Char(
        string='SOFIA Global User ID',
        index=True,
        help='Identificador único global del usuario en el Control Plane de SOFIA Platform',
        copy=False,
    )
    sofia_roles = fields.Char(
        string='Roles SOFIA Platform',
        help='Roles asignados en el Control Plane (ej. TENANT_ADMIN, OPERATOR)',
        copy=False,
    )
    sofia_last_sync = fields.Datetime(
        string='Última Sincronización SOFIA',
        readonly=True,
    )

    @api.model
    def _sofia_get_entitlement_limits(self):
        """
        Obtiene los límites contratados (max_users, plan_code) desde el Control Plane
        con caché local en ir.config_parameter para garantizar resiliencia offline (ADR-001).
        """
        icp = self.env['ir.config_parameter'].sudo()
        cached_max = icp.get_param('sofia.entitlements.max_users')
        cached_plan = icp.get_param('sofia.entitlements.plan_code', 'PLAN ACTUAL')
        last_sync_str = icp.get_param('sofia.entitlements.last_sync', '0')

        now_ts = int(time.time())
        try:
            last_sync_ts = int(float(last_sync_str))
        except (ValueError, TypeError):
            last_sync_ts = 0

        # Usar caché si sigue vigente
        if cached_max and (now_ts - last_sync_ts) < ENTITLEMENT_CACHE_TTL_SECONDS:
            try:
                return int(cached_max), cached_plan
            except ValueError:
                pass

        # Consultar Control Plane por red interna aislada
        base_url = (
            icp.get_param('sofia.control_plane_url')
            or os.getenv('SOFIA_CONTROL_PLANE_URL', 'http://control-plane-api:8000')
        ).rstrip('/')
        db_name = self.env.cr.dbname

        try:
            resp = requests.get(
                f"{base_url}/api/v1/tenants/by-db/{db_name}/entitlements",
                timeout=3,
            )
            if resp.status_code == 200:
                data = resp.json()
                limits = data.get('limits') or {}
                max_users = int(limits.get('max_users', 0))
                plan_code = data.get('plan_code') or data.get('tier', 'PLAN ACTUAL')
                if max_users > 0:
                    icp.set_param('sofia.entitlements.max_users', str(max_users))
                    icp.set_param('sofia.entitlements.plan_code', str(plan_code))
                    icp.set_param('sofia.entitlements.last_sync', str(now_ts))
                    return max_users, plan_code
        except Exception as exc:
            _logger.warning(
                "No se pudo sincronizar entitlements con Control Plane (%s). Usando caché local offline.",
                exc,
            )

        # Fallback offline seguro: usar último límite en caché si existe
        if cached_max:
            try:
                return int(cached_max), cached_plan
            except ValueError:
                pass

        return None, cached_plan

    @api.model
    def _sofia_check_user_seat_limit(self):
        """
        Verifica que el total de usuarios internos activos (excluyendo OdooBot id=1)
        no exceda el límite contratado en el plan SaaS del tenant.
        """
        if (
            self.env.context.get('install_mode')
            or self.env.context.get('module_uninstall')
            or self.env.context.get('sofia_bypass_user_limit')
            or self.env.cr.dbname == CORPORATE_MASTER_DB
        ):
            return

        max_users, plan_code = self._sofia_get_entitlement_limits()
        if not max_users or max_users <= 0:
            return

        active_internal_count = self.sudo().search_count([
            ('active', '=', True),
            ('share', '=', False),
            ('id', '!=', 1),
        ])

        if active_internal_count > max_users:
            raise UserError(_(
                "Has alcanzado el límite de usuarios activos de tu plan %(plan)s (%(limit)d usuarios contratados).\n\n"
                "Para agregar más colaboradores a tu equipo, ingresa a Mi Suscripción desde tu portal:\n"
                "/my/subscription",
                plan=plan_code,
                limit=max_users,
            ))

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any(not u.share and u.active for u in users):
            self._sofia_check_user_seat_limit()
        return users

    def write(self, vals):
        res = super().write(vals)
        if vals.get('active') or 'groups_id' in vals or 'group_ids' in vals:
            if any(not u.share and u.active for u in self):
                self._sofia_check_user_seat_limit()
        return res
