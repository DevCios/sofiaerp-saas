# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosExpressController(http.Controller):

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload, ensure_ascii=False, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8')],
            status=status,
        )

    def _read_json_body(self):
        raw = request.httprequest.get_data(as_text=True) or '{}'
        try:
            return json.loads(raw)
        except Exception:
            return {}

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

    @http.route('/pos_express/api/data', type='http', auth='user', methods=['POST'], csrf=False)
    def api_get_data(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].get_pos_data(body.get('session_id'))
        return self._json_response(res)

    @http.route('/pos_express/api/checkout', type='http', auth='user', methods=['POST'], csrf=False)
    def api_checkout(self, **kw):
        body = self._read_json_body()
        try:
            res = request.env['pos.express.session'].submit_checkout(
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

    @http.route('/pos_express/api/customers', type='http', auth='user', methods=['POST'], csrf=False)
    def api_customers(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].search_customers(body.get('query', ''))
        return self._json_response({'customers': res})

    @http.route('/pos_express/api/consult_doc', type='http', auth='user', methods=['POST'], csrf=False)
    def api_consult_doc(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].consult_and_create_customer(body.get('doc_number', ''))
        return self._json_response(res)

    @http.route('/pos_express/api/tickets', type='http', auth='user', methods=['POST'], csrf=False)
    def api_tickets(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].search_tickets(
            session_id=body.get('session_id'),
            query=body.get('query', ''),
        )
        return self._json_response({'tickets': res})

    @http.route('/pos_express/api/ticket_detail', type='http', auth='user', methods=['POST'], csrf=False)
    def api_ticket_detail(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].get_ticket_data(body.get('move_id'))
        return self._json_response(res)

    @http.route('/pos_express/api/credit_note', type='http', auth='user', methods=['POST'], csrf=False)
    def api_credit_note(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].create_credit_note(
            move_id=body.get('move_id'),
            session_id=body.get('session_id'),
            reason=body.get('reason', ''),
        )
        return self._json_response(res)

    @http.route('/pos_express/api/cash_move', type='http', auth='user', methods=['POST'], csrf=False)
    def api_cash_move(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.cash.move'].register_cash_move(
            session_id=body.get('session_id'),
            amount=body.get('amount', 0.0),
            move_type=body.get('move_type', 'in'),
            note=body.get('note', ''),
        )
        return self._json_response(res)

    @http.route('/pos_express/api/close_session', type='http', auth='user', methods=['POST'], csrf=False)
    def api_close_session(self, **kw):
        body = self._read_json_body()
        res = request.env['pos.express.session'].close_session_from_pos(
            session_id=body.get('session_id'),
            counted_cash=body.get('counted_cash', 0.0),
            note=body.get('note', ''),
        )
        return self._json_response(res)
