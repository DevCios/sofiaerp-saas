# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
import jwt
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SofiaAuthController(http.Controller):

    @http.route('/sofia/auth/callback', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def sofia_sso_callback(self, token=None, **kwargs):
        """
        Punto de entrada para el inicio de sesión federado desde SOFIA Central.
        Valida criptográficamente el token sin requerir llamada síncrona a la API central (Resiliencia Offline).
        """
        if not token:
            return request.redirect('/web/login?error=missing_token')

        try:
            # 1. Validación Criptográfica Local Offline Estricta (RS256 con Clave Pública Local)
            # Odoo valida contra el archivo de clave pública /etc/sofia/keys/jwt_public.pem
            key_path = '/etc/sofia/keys/jwt_public.pem'
            try:
                with open(key_path, 'r') as f:
                    pub_key = f.read()
            except FileNotFoundError:
                _logger.critical("Clave pública RSA no encontrada en '%s'. Imposible autenticar de forma segura.", key_path)
                return request.redirect('/web/login?error=auth_infrastructure_error')

            try:
                payload = jwt.decode(token, pub_key, algorithms=['RS256'], audience='sofia-platform')
            except jwt.ExpiredSignatureError:
                _logger.warning("Intento de autenticación SSO con token JWT expirado.")
                return request.redirect('/web/login?error=token_expired')
            except jwt.InvalidTokenError as e:
                _logger.error("Token JWT inválido o firma RS256 rechazada: %s", str(e))
                return request.redirect('/web/login?error=invalid_token_signature')

            user_email = payload.get('email')
            sofia_user_id = payload.get('sub')
            roles = payload.get('roles', [])

            if not user_email:
                return request.redirect('/web/login?error=invalid_token_payload')

            # 2. Búsqueda o autoprovisionamiento de usuario local
            env = request.env(user=http.ROOT_USER)
            user = env['res.users'].sudo().search([('login', '=', user_email)], limit=1)

            admin_group = env.ref('base.group_system', raise_if_not_found=False)
            internal_group = env.ref('base.group_user', raise_if_not_found=False)

            groups_to_assign = [internal_group.id] if internal_group else []
            if "TENANT_ADMIN" in roles and admin_group:
                groups_to_assign.append(admin_group.id)

            if not user:
                # Autoprovisionar nuevo usuario local en Odoo
                user_vals = {
                    'name': payload.get('name', user_email),
                    'login': user_email,
                    'email': user_email,
                    'sofia_user_id': sofia_user_id,
                    'sofia_roles': ",".join(roles),
                    'sofia_last_sync': datetime.now(),
                }
                if groups_to_assign:
                    user_vals['groups_id'] = [(6, 0, groups_to_assign)]

                user = env['res.users'].sudo().create(user_vals)
                _logger.info("Usuario Odoo autoprovisionado vía SOFIA Central: %s", user_email)
            else:
                update_vals = {
                    'sofia_user_id': sofia_user_id,
                    'sofia_roles': ",".join(roles),
                    'sofia_last_sync': datetime.now(),
                }
                if groups_to_assign:
                    update_vals['groups_id'] = [(4, gid) for gid in groups_to_assign]
                user.sudo().write(update_vals)

            # 3. Autenticación y creación de sesión Odoo
            request.session.uid = user.id
            request.session.login = user.login
            request.session.session_token = user._compute_session_token(request.session.sid)

            return request.redirect('/web')

        except Exception as e:
            _logger.error("Error crítico en validación SSO de SOFIA: %s", str(e), exc_info=True)
            return request.redirect('/web/login?error=auth_failed')

    @http.route('/sofia/runtime/status', type='http', auth='none', methods=['GET'], csrf=False)
    def sofia_runtime_status(self):
        """
        Endpoint de diagnóstico y telemetría de salud invocado por el Edge Proxy o Control Plane.
        Retorna el estado de conectividad sin exponer credenciales ni nombres de tablas internas.
        """
        try:
            db_name = request.env.cr.dbname
            data = {
                "runtime": "odoo-community-20",
                "status": "online",
                "database_active": True,
                "database": db_name,
            }
            return request.make_response(
                json.dumps(data),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            return request.make_response(
                json.dumps({"status": "degraded", "error": str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
