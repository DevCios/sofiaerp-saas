# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 86400  # 24 horas para sesiones de app .exe / .apk


class PosExpressController(http.Controller):

    # -------------------------------------------------------------------------
    # Helpers de CORS y Token HMAC para POS Express Desktop (.exe) / Android (.apk)
    # -------------------------------------------------------------------------
    def _cors_headers(self):
        origin = request.httprequest.headers.get('Origin') or '*'
        return [
            ('Access-Control-Allow-Origin', origin),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Headers', 'Content-Type, X-POS-Token, Authorization'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
        ]

    def _json_response(self, payload, status=200):
        headers = [('Content-Type', 'application/json; charset=utf-8')] + self._cors_headers()
        return request.make_response(
            json.dumps(payload, ensure_ascii=False, default=str),
            headers=headers,
            status=status,
        )

    def _read_json_body(self):
        raw = request.httprequest.get_data(as_text=True) or '{}'
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _signing_secret(self):
        param = request.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'database.secret')], limit=1
        )
        return (param.value or 'sofia_pos_express_fallback_secret').encode('utf-8')

    def _issue_pos_token(self, uid, company_id):
        exp = int(time.time()) + TOKEN_TTL_SECONDS
        payload = f'{uid}:{company_id}:{exp}'.encode('utf-8')
        sig = hmac.new(self._signing_secret(), payload, hashlib.sha256).hexdigest()
        raw = f'{uid}:{company_id}:{exp}:{sig}'.encode('utf-8')
        return base64.urlsafe_b64encode(raw).decode('ascii')

    def _resolve_api_env(self):
        """
        Resuelve el entorno autenticado:
        1) Si viene sesión web Odoo activa (auth='user'), usa request.env.
        2) Si viene header X-POS-Token (desde app .exe / .apk), valida HMAC y devuelve env del usuario.
        """
        token = (request.httprequest.headers.get('X-POS-Token') or '').strip()
        if token:
            try:
                decoded = base64.urlsafe_b64decode(token.encode('ascii')).decode('utf-8')
                uid_s, cid_s, exp_s, sig = decoded.split(':')
                if int(exp_s) < int(time.time()):
                    return None
                expected = hmac.new(
                    self._signing_secret(),
                    f'{uid_s}:{cid_s}:{exp_s}'.encode('utf-8'),
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(sig, expected):
                    return None
                uid = int(uid_s)
                cid = int(cid_s)
                user = request.env['res.users'].sudo().browse(uid)
                if not user.exists() or not user.active:
                    return None
                return request.env(
                    user=uid,
                    context=dict(request.env.context, allowed_company_ids=[cid]),
                )
            except Exception:
                return None

        if request.session.uid:
            return request.env
        return None

    def _preflight_if_options(self):
        if request.httprequest.method == 'OPTIONS':
            return request.make_response('', headers=self._cors_headers(), status=204)
        return None

    # -------------------------------------------------------------------------
    # Terminal Web Standalone (/pos_express)
    # -------------------------------------------------------------------------
    @http.route('/pos_express', type='http', auth='user', website=False)
    def pos_express_terminal(self, pos_session_id=None, **kw):
        Session = request.env['pos.express.session'].sudo()
        session = False
        if pos_session_id and str(pos_session_id).isdigit():
            cand = Session.browse(int(pos_session_id))
            if cand.exists() and cand.state == 'opened' and cand.company_id == request.env.company:
                session = cand

        if not session:
            cfg = request.env['pos.express.config'].sudo().ensure_default_config(request.env.company)
            session = cfg.current_session_id
            if not session:
                session = Session.create({'config_id': cfg.id, 'user_id': request.env.uid})

        action = request.env.ref('sofia_pos_express.action_pos_express_config', raise_if_not_found=False)
        back_url = f'/odoo/action-{action.id}' if action else '/odoo'

        html = request.env['ir.ui.view'].sudo()._render_template(
            'sofia_pos_express.pos_express_terminal',
            {'session_id': session.id, 'session_name': session.name, 'back_url': back_url},
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # -------------------------------------------------------------------------
    # Login por Token para App Instalable Windows (.exe) y Android (.apk)
    # -------------------------------------------------------------------------
    @http.route('/pos_express/api/app_login', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_app_login(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        body = self._read_json_body()
        login = (body.get('login') or '').strip()
        password = body.get('password') or ''
        if not login or not password:
            return self._json_response({'error': 'Ingresa correo/usuario y contraseña.'}, status=400)

        user = request.env['res.users'].sudo().search(
            [('login', '=', login), ('active', '=', True)], limit=1
        )
        if not user:
            return self._json_response({'error': 'Usuario o contraseña incorrectos.'}, status=401)

        try:
            credential = {'login': login, 'password': password, 'type': 'password'}
            user_check_env = request.env(user=user.id)
            if hasattr(user_check_env['res.users'], '_check_credentials'):
                user_check_env['res.users']._check_credentials(credential, {'interactive': False})
            else:
                request.env.cr.execute("SELECT password FROM res_users WHERE id = %s", (user.id,))
                row = request.env.cr.fetchone()
                if not row or not row[0] or not user._crypt_context().verify(password, row[0]):
                    return self._json_response({'error': 'Usuario o contraseña incorrectos.'}, status=401)
        except Exception as exc:
            _logger.warning("POS Express app_login falló para '%s': %s", login, exc)
            return self._json_response({'error': 'Usuario o contraseña incorrectos.'}, status=401)

        company = user.company_id
        user_env = request.env(
            user=user.id,
            context=dict(request.env.context, allowed_company_ids=[company.id]),
        )

        cfg = user_env['pos.express.config'].sudo().ensure_default_config(company)
        session = cfg.current_session_id
        if not session:
            session = user_env['pos.express.session'].sudo().create({
                'config_id': cfg.id,
                'user_id': user.id,
            })

        token = self._issue_pos_token(user.id, company.id)
        pos_data = user_env['pos.express.session'].get_pos_data(session.id)
        return self._json_response({
            'success': True,
            'token': token,
            'session_id': session.id,
            'session_name': session.name,
            'pos_data': pos_data,
        })

    # -------------------------------------------------------------------------
    # APIs JSON (compatibles con Web /pos_express + App .exe / .apk vía X-POS-Token)
    # -------------------------------------------------------------------------
    @http.route('/pos_express/api/data', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_get_data(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'Sesión expirada. Inicia sesión nuevamente.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].get_pos_data(body.get('session_id'))
        return self._json_response(res)

    @http.route('/pos_express/api/checkout', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_checkout(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'Sesión expirada. Inicia sesión nuevamente.'}, status=401)
        body = self._read_json_body()
        try:
            res = env['pos.express.session'].submit_checkout(
                session_id=body.get('session_id'),
                partner_id=body.get('partner_id'),
                lines=body.get('lines') or [],
                amount_paid=body.get('amount_paid', 0.0),
                doc_type_code=body.get('doc_type_code', '03'),
                payment_journal_id=body.get('payment_journal_id'),
                sales_journal_id=body.get('sales_journal_id'),
                note=body.get('note', ''),
                second_payment_journal_id=body.get('second_payment_journal_id'),
                second_payment_amount=body.get('second_payment_amount', 0.0),
            )
            return self._json_response(res)
        except Exception as exc:
            _logger.exception("Error en POS Express checkout")
            return self._json_response({'error': str(exc)}, status=400)

    @http.route('/pos_express/api/customers', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_customers(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].search_customers(body.get('query', ''))
        return self._json_response({'customers': res})

    @http.route('/pos_express/api/consult_doc', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_consult_doc(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].consult_and_create_customer(body.get('doc_number', ''))
        return self._json_response(res)

    @http.route('/pos_express/api/tickets', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_tickets(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].search_tickets(
            session_id=body.get('session_id'),
            query=body.get('query', ''),
        )
        return self._json_response({'tickets': res})

    @http.route('/pos_express/api/ticket_detail', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_ticket_detail(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].get_ticket_data(body.get('move_id'))
        return self._json_response(res)

    @http.route('/pos_express/api/credit_note', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_credit_note(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].create_credit_note(
            move_id=body.get('move_id'),
            session_id=body.get('session_id'),
            reason=body.get('reason', ''),
        )
        return self._json_response(res)

    @http.route('/pos_express/api/cash_move', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_cash_move(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.cash.move'].register_cash_move(
            session_id=body.get('session_id'),
            amount=body.get('amount', 0.0),
            move_type=body.get('move_type', 'in'),
            note=body.get('note', ''),
        )
        return self._json_response(res)

    @http.route('/pos_express/api/close_session', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def api_close_session(self, **kw):
        pre = self._preflight_if_options()
        if pre is not None:
            return pre
        env = self._resolve_api_env()
        if not env:
            return self._json_response({'error': 'No autenticado.'}, status=401)
        body = self._read_json_body()
        res = env['pos.express.session'].close_session_from_pos(
            session_id=body.get('session_id'),
            counted_cash=body.get('counted_cash', 0.0),
            note=body.get('note', ''),
        )
        return self._json_response(res)
