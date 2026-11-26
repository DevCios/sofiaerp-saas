# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosExpressCashMove(models.Model):
    _name = 'pos.express.cash.move'
    _description = 'Movimiento de Efectivo POS Express'
    _order = 'id desc'

    session_id = fields.Many2one(
        'pos.express.session',
        string='Turno',
        required=True,
        ondelete='cascade',
        readonly=True,
    )
    date = fields.Datetime(string='Fecha/Hora', default=fields.Datetime.now, readonly=True)
    move_type = fields.Selection(
        [('in', 'Entrada de Efectivo'), ('out', 'Salida de Efectivo')],
        string='Tipo',
        required=True,
        readonly=True,
    )
    amount = fields.Float(string='Monto', required=True, readonly=True)
    note = fields.Char(string='Concepto', readonly=True)

    @api.model
    def register_cash_move(self, session_id, amount, move_type, note=''):
        session = self.env['pos.express.session'].browse(int(session_id))
        if not session.exists() or session.state != 'opened':
            return {'error': 'El turno está cerrado. No se puede registrar el movimiento.'}
        val = float(amount or 0.0)
        if val <= 0:
            return {'error': 'El monto debe ser mayor a cero.'}
        if move_type not in ('in', 'out'):
            return {'error': 'Tipo de movimiento inválido.'}

        move = self.create({
            'session_id': session.id,
            'move_type': move_type,
            'amount': val,
            'note': (note or '').strip(),
        })
        return {
            'success': True,
            'move_id': move.id,
            'net_cash_moves': session.net_cash_moves,
            'cash_expected': session.cash_real_expected,
        }
