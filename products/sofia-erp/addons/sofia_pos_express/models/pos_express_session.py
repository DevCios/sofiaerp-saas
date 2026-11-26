# -*- coding: utf-8 -*-
import datetime
import logging
import urllib.parse

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosExpressSession(models.Model):
    _name = 'pos.express.session'
    _description = 'Turno de Caja POS Express'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(string='Turno / Sesión', required=True, copy=False, readonly=True, default='/')
    config_id = fields.Many2one('pos.express.config', string='Caja', required=True, readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='config_id.company_id',
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Cajero',
        required=True,
        readonly=True,
        default=lambda self: self.env.uid,
    )
    state = fields.Selection(
        [('opened', 'Abierto'), ('closed', 'Cerrado')],
        string='Estado',
        required=True,
        default='opened',
        readonly=True,
    )
    start_at = fields.Datetime(string='Apertura', default=fields.Datetime.now, readonly=True)
    stop_at = fields.Datetime(string='Cierre', readonly=True, copy=False)

    opening_balance = fields.Float(string='Fondo Inicial (Efectivo)', default=0.0)
    cash_real_expected = fields.Float(string='Efectivo Esperado', compute='_compute_cash_totals', store=True)
    cash_real_transaction = fields.Float(string='Ventas Efectivo', compute='_compute_cash_totals', store=True)
    cash_real_bank = fields.Float(string='Ventas Bancos / Yape / Tarjeta', compute='_compute_cash_totals', store=True)
    cash_real_other = fields.Float(string='Ventas Otros', compute='_compute_cash_totals', store=True)
    net_cash_moves = fields.Float(string='Mov. Caja Neto', compute='_compute_cash_totals', store=True)
    cash_register_balance_end_real = fields.Float(string='Efectivo Contado', copy=False)
    cash_register_difference = fields.Float(string='Diferencia', compute='_compute_cash_difference', store=True)
    closing_notes = fields.Text(string='Notas de Cierre')

    move_ids = fields.One2many('account.move', 'pos_express_session_id', string='Comprobantes')
    payment_ids = fields.One2many('account.payment', 'pos_express_session_id', string='Pagos')
    cash_move_ids = fields.One2many('pos.express.cash.move', 'session_id', string='Entradas / Salidas')
    picking_ids = fields.One2many('stock.picking', 'pos_express_session_id', string='Salidas de Stock')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.express.session') or '/'
        return super().create(vals_list)

    @api.depends(
        'opening_balance',
        'payment_ids.amount',
        'payment_ids.journal_id.type',
        'cash_move_ids.amount',
        'cash_move_ids.move_type',
    )
    def _compute_cash_totals(self):
        for session in self:
            t_cash = t_bank = t_other = 0.0
            for p in session.payment_ids:
                if p.journal_id.type == 'cash':
                    t_cash += p.amount
                elif p.journal_id.type == 'bank':
                    t_bank += p.amount
                else:
                    t_other += p.amount
            net = sum(m.amount if m.move_type == 'in' else -m.amount for m in session.cash_move_ids)
            session.cash_real_transaction = t_cash
            session.cash_real_bank = t_bank
            session.cash_real_other = t_other
            session.net_cash_moves = net
            session.cash_real_expected = session.opening_balance + t_cash + net

    @api.depends('cash_real_expected', 'cash_register_balance_end_real')
    def _compute_cash_difference(self):
        for session in self:
            session.cash_register_difference = session.cash_register_balance_end_real - session.cash_real_expected

    def action_pos_express_close(self):
        self.write({'state': 'closed', 'stop_at': fields.Datetime.now()})

    def action_open_terminal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos_express?pos_session_id={self.id}',
            'target': 'self',
        }

    # -------------------------------------------------------------------------
    # Helpers internos (Odoo 20 + SUNAT + NRUS)
    # -------------------------------------------------------------------------
    @api.model
    def _get_stock_location(self, company, config=False):
        if config and config.stock_location_id:
            return config.stock_location_id
        if config and config.picking_type_id and config.picking_type_id.default_location_src_id:
            return config.picking_type_id.default_location_src_id
        wh = self.env['stock.warehouse'].sudo().search([('company_id', '=', company.id)], limit=1)
        if wh and wh.lot_stock_id:
            return wh.lot_stock_id
        return self.env['stock.location'].sudo().search([
            ('usage', '=', 'internal'),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ], limit=1)

    @api.model
    def _get_or_create_default_partner(self, company):
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search([
            ('vat', '=', '00000000'),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            partner = Partner.search([
                ('name', 'ilike', 'Consumidor Final'),
                '|', ('company_id', '=', False), ('company_id', '=', company.id),
            ], limit=1)
        if not partner:
            dni_type = self.env['l10n_latam.identification.type'].sudo().search([('l10n_pe_vat_code', '=', '1')], limit=1)
            partner = Partner.with_company(company).create({
                'name': 'Consumidor Final',
                'vat': '00000000',
                'company_id': company.id,
                'l10n_latam_identification_type_id': dni_type.id if dni_type else False,
            })
        return partner

    @api.model
    def _build_gateway_consult_url(self, move):
        """Genera enlace directo al Portal Público de Consulta de Sofia Gateway (/consulta)."""
        company = move.company_id
        ruc = (company.vat or '').strip()
        doc_type = move.l10n_latam_document_type_id.code if move.l10n_latam_document_type_id else '03'
        serie, num = '', ''
        raw_name = (move.name or '').replace(' ', '')
        parts = raw_name.split('-')
        if len(parts) >= 2:
            serie = parts[-2][-4:].upper()
            num = parts[-1].lstrip('0') or '1'
        issue_date = move.invoice_date.strftime('%Y-%m-%d') if move.invoice_date else fields.Date.today().strftime('%Y-%m-%d')
        params = urllib.parse.urlencode({
            'ruc': ruc,
            'tipo': doc_type,
            'serie': serie,
            'num': num,
            'fecha': issue_date,
            'total': f'{move.amount_total:.2f}',
        })
        return f'https://gateway.sofiaerp.com/consulta?{params}'

    # -------------------------------------------------------------------------
    # API: get_pos_data (carga ultracompacta para el terminal /pos_express)
    # -------------------------------------------------------------------------
    @api.model
    def get_pos_data(self, session_id):
        session = self.sudo().browse(int(session_id))
        if not session.exists() or session.state != 'opened':
            return {'error': 'Turno no encontrado o cerrado.'}

        config = session.config_id
        company = config.company_id
        is_nrus = getattr(company, 'l10n_pe_tax_regime', 'general') == 'nrus'
        provider = getattr(company, 'l10n_pe_edi_provider', 'sunat') or 'sunat'
        test_env = bool(getattr(company, 'l10n_pe_edi_test_env', True))

        # Métodos de pago
        methods = []
        for j in config.payment_journal_ids.filtered(lambda x: x.company_id == company and x.active):
            nl = j.name.lower()
            code = 'cash' if ('efectivo' in nl or j.type == 'cash') else (
                'yape' if 'yape' in nl else (
                    'plin' if 'plin' in nl else (
                        'card' if any(k in nl for k in ('tarjeta', 'pos', 'visa', 'master', 'izipay', 'niubiz')) else 'bank'
                    )
                )
            )
            methods.append({'id': j.id, 'name': j.name, 'type': j.type, 'code': code})
        prio = {'cash': 0, 'yape': 1, 'plin': 2, 'card': 3, 'bank': 4}
        methods.sort(key=lambda m: prio.get(m['code'], 9))

        # Diarios de venta SUNAT (en NRUS excluye Facturas 01)
        sales = []
        active_journals = config.journal_ids.filtered(lambda x: x.company_id == company and x.active)
        if not active_journals:
            active_journals = self.env['account.journal'].sudo().search([
                ('company_id', '=', company.id), ('type', '=', 'sale'), ('active', '=', True)
            ])
        for j in active_journals:
            nl = j.name.lower()
            jcode = (j.code or '').upper()
            is_fac = ('factura' in nl or jcode.startswith('F')) and not ('boleta' in nl or jcode.startswith('B'))
            code_type = '01' if is_fac else '03'
            if is_nrus and code_type == '01':
                continue
            sales.append({'id': j.id, 'name': j.name, 'code': j.code, 'code_type': code_type})
        sales.sort(key=lambda x: 0 if x['code_type'] == '03' else 1)

        # Categorías y catálogo de productos (hasta 1500 para respuesta < 50ms)
        categs = self.env['product.category'].sudo().search_read([], fields=['id', 'name'], order='name asc')
        stock_loc = self._get_stock_location(company, config=config)
        prod_env = self.env['product.product'].sudo().with_company(company)
        if stock_loc:
            prod_env = prod_env.with_context(location=stock_loc.id)

        products = prod_env.search_read(
            [('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company.id)],
            fields=['id', 'name', 'list_price', 'qty_available', 'default_code', 'barcode', 'categ_id', 'type'],
            limit=1500,
            order='name asc',
        )

        # Estadísticas del turno
        moves = self.env['account.move'].sudo().search([
            ('pos_express_session_id', '=', session.id),
            ('state', '=', 'posted'),
        ])
        invoices = moves.filtered(lambda m: m.move_type == 'out_invoice')
        refunds = moves.filtered(lambda m: m.move_type == 'out_refund')
        sales_total = sum(invoices.mapped('amount_total')) - sum(refunds.mapped('amount_total'))
        partner = self._get_or_create_default_partner(company)

        return {
            'session_id': session.id,
            'session_name': session.name,
            'config_name': config.name,
            'header_title': config.header_title or company.name or 'POS Express',
            'user_name': self.env.user.name,
            'company_info': {
                'id': company.id,
                'name': company.name,
                'vat': company.vat or '',
                'phone': company.phone or '',
                'street': company.street or '',
                'currency_symbol': company.currency_id.symbol or 'S/',
                'is_nrus': is_nrus,
                'provider': provider,
                'test_env': test_env,
                'ticket_footer': config.ticket_footer or '',
                'yape_info': config.yape_info or '',
            },
            'payment_methods': methods,
            'sales_journals': sales,
            'product_categories': categs,
            'catalog': products,
            'price_includes_tax': config.price_includes_tax,
            'enable_discount': config.enable_discount,
            'opening_balance': session.opening_balance,
            'sales_count': len(invoices),
            'sales_total': round(sales_total, 2),
            'cash_total': round(session.cash_real_transaction, 2),
            'bank_total': round(session.cash_real_bank, 2),
            'net_cash_moves': round(session.net_cash_moves, 2),
            'cash_expected': round(session.cash_real_expected, 2),
            'default_partner': {
                'id': partner.id,
                'name': partner.name,
                'vat': partner.vat or '00000000',
            } if partner else None,
        }

    # -------------------------------------------------------------------------
    # API: submit_checkout (Emisión SUNAT + Sofia Gateway + Stock + Pago Mixto)
    # -------------------------------------------------------------------------
    @api.model
    def submit_checkout(
        self,
        session_id,
        partner_id,
        lines,
        amount_paid,
        doc_type_code,
        payment_journal_id,
        sales_journal_id,
        note=False,
        second_payment_journal_id=False,
        second_payment_amount=0.0,
    ):
        session = self.sudo().browse(int(session_id))
        if not session.exists() or session.state != 'opened':
            return {'error': 'El turno de caja se encuentra cerrado.'}
        if not lines:
            return {'error': 'El carrito está vacío.'}

        config = session.config_id
        company = config.company_id
        is_nrus = getattr(company, 'l10n_pe_tax_regime', 'general') == 'nrus'
        is_factura = (doc_type_code == '01')

        if is_nrus and is_factura:
            return {'error': 'Tu empresa está en Régimen Nuevo RUS (NRUS): SUNAT no permite emitir Facturas (01). Emite una Boleta (03).'}

        partner = self.env['res.partner'].sudo().browse(int(partner_id)) if partner_id else False
        if not partner or not partner.exists():
            partner = self._get_or_create_default_partner(company)

        if is_factura:
            vat = (partner.vat or '').strip()
            if len(vat) != 11 or not vat.isdigit():
                return {'error': f'Para Factura (01) es obligatorio un cliente con RUC válido de 11 dígitos (actual: "{vat or "ninguno"}").'}

        # Impuesto NRUS 0% Inafecto si aplica
        nrus_tax = False
        if is_nrus:
            nrus_tax = self.env['account.tax'].sudo().search([
                ('company_id', '=', company.id),
                ('type_tax_use', '=', 'sale'),
                ('l10n_pe_edi_tax_code', '=', '9998'),
                ('amount', '=', 0.0),
            ], limit=1)

        invoice_lines = []
        total_estimate = 0.0
        for line in lines:
            prod = self.env['product.product'].sudo().with_company(company).browse(int(line['product_id']))
            if not prod.exists():
                return {'error': 'Uno de los productos del carrito ya no existe.'}

            if is_nrus and nrus_tax:
                taxes = nrus_tax
            else:
                taxes = prod.taxes_id.filtered(lambda t: t.company_id.id == company.id)
                if not taxes and company.account_sale_tax_id:
                    taxes = company.account_sale_tax_id

            qty = float(line.get('qty', 1.0))
            price_unit = float(line.get('price', 0.0))
            discount = float(line.get('discount', 0.0))

            if config.price_includes_tax and taxes and not taxes[0].price_include and taxes[0].amount > 0:
                price_unit = price_unit / (1.0 + (taxes[0].amount / 100.0))

            invoice_lines.append((0, 0, {
                'product_id': prod.id,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'tax_ids': [(6, 0, taxes.ids)] if taxes else False,
            }))
            total_estimate += qty * float(line.get('price', 0.0)) * (1.0 - discount / 100.0)

        if not is_factura and total_estimate > 700.0:
            vat = (partner.vat or '').strip()
            if not vat or vat == '00000000':
                return {'error': 'Por norma SUNAT, las Boletas mayores a S/ 700.00 requieren DNI o RUC del cliente.'}

        # Diario y tipo de documento LATAM
        journal = self.env['account.journal'].sudo().browse(int(sales_journal_id)) if sales_journal_id else False
        if not journal or not journal.exists() or journal.company_id != company:
            journal = config.journal_ids.filtered(lambda j: j.company_id == company and j.active)[:1]
        if not journal:
            return {'error': 'No hay un diario de ventas activo configurado en la caja.'}

        latam_doc_type = self.env['l10n_latam.document.type'].sudo().search([
            ('country_id.code', '=', 'PE'),
            ('code', '=', doc_type_code),
        ], limit=1)

        move_vals = {
            'move_type': 'out_invoice',
            'company_id': company.id,
            'partner_id': partner.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': invoice_lines,
            'pos_express_session_id': session.id,
        }
        if latam_doc_type:
            move_vals['l10n_latam_document_type_id'] = latam_doc_type.id
        if 'l10n_pe_edi_operation_type' in self.env['account.move']._fields:
            move_vals['l10n_pe_edi_operation_type'] = '0101'
        if note:
            move_vals['narration'] = note

        move = self.env['account.move'].sudo().with_company(company).create(move_vals)
        move.action_post()

        # Envío automático a SUNAT / Sofia Gateway sin bloquear el cobro si SUNAT está saturado
        sunat_status = 'PENDIENTE'
        sunat_msg = ''
        if config.auto_send_sunat and hasattr(move, '_l10n_pe_edi_post_invoice'):
            try:
                edi_res = move._l10n_pe_edi_post_invoice() or {}
                st = getattr(move, 'l10n_pe_edi_status', False)
                if st == 'sent' or edi_res.get('success'):
                    sunat_status = 'ACEPTADO'
                elif edi_res.get('level') == 'danger':
                    sunat_status = 'OBSERVADO / REVISAR'
                    sunat_msg = str(edi_res.get('message') or '')[:160]
                else:
                    sunat_status = 'EN COLA'
                    sunat_msg = str(edi_res.get('message') or 'Firmado localmente y encolado en Sofia Gateway.')[:160]
            except Exception as exc:
                _logger.warning("POS Express: aviso enviando %s a SUNAT: %s", move.name, exc)
                sunat_status = 'EN COLA'
                sunat_msg = str(exc)[:140]

        # Rebaja de stock nativa Odoo 20
        picking_name = False
        if config.auto_deduct_stock:
            storable_lines = []
            for line in lines:
                p = self.env['product.product'].sudo().browse(int(line['product_id']))
                if getattr(p, 'is_storable', False) or p.type == 'product':
                    storable_lines.append((p, float(line.get('qty', 1.0))))
            picking_type = config.picking_type_id or self.env['stock.picking.type'].sudo().search([
                ('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company.id)
            ], limit=1)
            if storable_lines and picking_type:
                try:
                    src_loc = self._get_stock_location(company, config=config) or picking_type.default_location_src_id
                    dst_loc = partner.with_company(company).property_stock_customer or self.env.ref('stock.stock_location_customers')
                    picking = self.env['stock.picking'].sudo().with_company(company).create({
                        'picking_type_id': picking_type.id,
                        'company_id': company.id,
                        'partner_id': partner.id,
                        'origin': f'{session.name} / {move.name}',
                        'location_id': src_loc.id,
                        'location_dest_id': dst_loc.id,
                        'move_type': 'direct',
                        'pos_express_session_id': session.id,
                    })
                    for prod, qty in storable_lines:
                        self.env['stock.move'].sudo().with_company(company).create({
                            'description_picking': prod.name,
                            'company_id': company.id,
                            'product_id': prod.id,
                            'product_uom_qty': qty,
                            'product_uom': prod.uom_id.id,
                            'picking_id': picking.id,
                            'location_id': src_loc.id,
                            'location_dest_id': dst_loc.id,
                        })
                    picking.action_confirm()
                    picking.action_assign()
                    for sm in picking.move_ids:
                        sm.quantity = sm.product_uom_qty
                    picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
                    picking_name = picking.name
                except Exception as exc:
                    _logger.warning("POS Express: no se pudo validar salida de stock para %s: %s", move.name, exc)

        # Registro y conciliación de pago(s) (Odoo 20: account_type)
        payment_breakdown = []
        if move.amount_total > 0 and payment_journal_id:
            pj1 = self.env['account.journal'].sudo().browse(int(payment_journal_id))
            if not pj1.exists() or pj1.company_id != company:
                pj1 = config.payment_journal_ids[:1]
            amt2 = round(float(second_payment_amount or 0.0), 2)
            pj2 = False
            if second_payment_journal_id and amt2 > 0:
                cand = self.env['account.journal'].sudo().browse(int(second_payment_journal_id))
                if cand.exists() and cand.company_id == company and cand.id != pj1.id:
                    pj2 = cand
                    amt2 = min(amt2, round(move.amount_total, 2))
            amt1 = round(max(0.0, move.amount_total - (amt2 if pj2 else 0.0)), 2)

            to_pay = []
            if pj1 and amt1 > 0:
                to_pay.append((pj1, amt1))
            if pj2 and amt2 > 0:
                to_pay.append((pj2, amt2))

            for pj, p_amt in to_pay:
                pml = pj.inbound_payment_method_line_ids[:1]
                payment = self.env['account.payment'].sudo().with_company(company).create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner.id,
                    'amount': p_amt,
                    'currency_id': move.currency_id.id,
                    'journal_id': pj.id,
                    'company_id': company.id,
                    'payment_method_line_id': pml.id if pml else False,
                    'pos_express_session_id': session.id,
                })
                payment.action_post()
                payment_breakdown.append(f'{pj.name}: {company.currency_id.symbol or "S/"} {p_amt:.2f}')
                p_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                )
                m_lines = move.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                )
                if p_lines and m_lines:
                    (p_lines + m_lines).reconcile()

        return {
            'success': True,
            'ticket': self._serialize_ticket(
                move,
                config,
                amount_paid=float(amount_paid or move.amount_total),
                payment_summary=' + '.join(payment_breakdown),
                picking_name=picking_name,
                sunat_status=sunat_status,
                sunat_msg=sunat_msg,
            ),
        }

    def _serialize_ticket(self, move, config=None, amount_paid=None, payment_summary='', picking_name=False, sunat_status='', sunat_msg=''):
        company = move.company_id
        is_factura = bool(move.l10n_latam_document_type_id and move.l10n_latam_document_type_id.code == '01')
        paid = float(amount_paid) if amount_paid is not None else move.amount_total
        phone = getattr(move.partner_id, 'mobile', False) or move.partner_id.phone or ''
        return {
            'move_id': move.id,
            'name': move.name,
            'doc_badge': 'FACTURA ELECTRÓNICA' if is_factura else 'BOLETA DE VENTA ELECTRÓNICA',
            'cpe_url': self._build_gateway_consult_url(move),
            'sunat_status': sunat_status or ('ACEPTADO' if getattr(move, 'l10n_pe_edi_status', '') == 'sent' else 'EN COLA'),
            'sunat_msg': sunat_msg,
            'company_name': company.name,
            'company_vat': company.vat or '',
            'company_address': company.street or '',
            'company_phone': company.phone or '',
            'currency_symbol': company.currency_id.symbol or 'S/',
            'is_nrus': getattr(company, 'l10n_pe_tax_regime', 'general') == 'nrus',
            'ticket_footer': config.ticket_footer if config else '',
            'yape_info': config.yape_info if config else '',
            'payment_summary': payment_summary,
            'cashier': self.env.user.name,
            'partner': move.partner_id.name,
            'partner_phone': phone.strip(),
            'vat': move.partner_id.vat or '',
            'date': move.invoice_date.strftime('%d/%m/%Y') if move.invoice_date else datetime.date.today().strftime('%d/%m/%Y'),
            'time': datetime.datetime.now().strftime('%H:%M:%S'),
            'amount_untaxed': round(move.amount_untaxed, 2),
            'amount_tax': round(move.amount_tax, 2),
            'amount_total': round(move.amount_total, 2),
            'amount_paid': round(paid, 2),
            'change': round(max(0.0, paid - move.amount_total), 2),
            'stock_picking': picking_name or '',
            'lines': [
                {
                    'name': l.product_id.name or l.name,
                    'qty': l.quantity,
                    'price': round(l.price_unit, 2),
                    'discount': l.discount,
                    'subtotal': round(l.price_total, 2),
                }
                for l in move.invoice_line_ids
            ],
        }

    # -------------------------------------------------------------------------
    # API: Historial, Reimpresión, Nota de Crédito, Clientes RUC/DNI y Cierre
    # -------------------------------------------------------------------------
    @api.model
    def get_ticket_data(self, move_id):
        move = self.env['account.move'].sudo().browse(int(move_id))
        if not move.exists() or move.company_id != self.env.company:
            return {'error': 'Comprobante no encontrado.'}
        cfg = move.pos_express_session_id.config_id if move.pos_express_session_id else None
        return {'success': True, 'ticket': self._serialize_ticket(move, config=cfg)}

    @api.model
    def search_tickets(self, session_id=False, query=''):
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'posted'),
        ]
        if session_id:
            domain.append(('pos_express_session_id', '=', int(session_id)))
        if query:
            domain += ['|', ('name', 'ilike', query.strip()), ('partner_id.name', 'ilike', query.strip())]
        moves = self.env['account.move'].sudo().search(domain, order='id desc', limit=30)
        return [{
            'id': m.id,
            'name': m.name,
            'date': m.invoice_date.strftime('%d/%m/%Y') if m.invoice_date else '',
            'partner': m.partner_id.name,
            'amount': round(m.amount_total, 2),
            'payment_state': m.payment_state,
            'sunat_status': getattr(m, 'l10n_pe_edi_status', '') or 'queued',
        } for m in moves]

    @api.model
    def create_credit_note(self, move_id, session_id, reason=''):
        move = self.env['account.move'].sudo().browse(int(move_id))
        if not move.exists() or move.company_id != self.env.company:
            return {'error': 'Comprobante no encontrado.'}
        if move.state != 'posted' or move.payment_state == 'reversed':
            return {'error': 'El comprobante no se puede anular o ya fue anulado.'}
        vals = {
            'ref': (reason or '').strip() or f'Anulación de {move.name}',
            'journal_id': move.journal_id.id,
            'pos_express_session_id': int(session_id) if session_id else False,
        }
        if 'l10n_pe_edi_refund_reason' in self.env['account.move']._fields:
            vals['l10n_pe_edi_refund_reason'] = '01'
        cn = move.sudo().with_company(move.company_id)._reverse_moves([vals], cancel=True)
        if cn and hasattr(cn, '_l10n_pe_edi_post_invoice'):
            try:
                cn._l10n_pe_edi_post_invoice()
            except Exception as exc:
                _logger.warning("POS Express: aviso enviando NC %s a SUNAT: %s", cn.name, exc)
        return {
            'success': True,
            'credit_note_name': cn.name if cn else 'N/A',
            'refund_amount': round(move.amount_total, 2),
        }

    @api.model
    def search_customers(self, query=''):
        domain = ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
        q = (query or '').strip()
        if q:
            domain += ['|', ('name', 'ilike', q), ('vat', 'ilike', q)]
        return self.env['res.partner'].sudo().search_read(domain, fields=['id', 'name', 'vat'], limit=20)

    @api.model
    def consult_and_create_customer(self, doc_number):
        """Busca cliente por DNI/RUC o consulta en vivo a SUNAT/RENIEC (sofiaerp_pe_vat)."""
        clean = (doc_number or '').strip()
        if not clean.isdigit() or len(clean) not in (8, 11):
            return {'error': 'Ingresa un DNI (8 dígitos) o RUC (11 dígitos) válido.'}
        company = self.env.company
        Partner = self.env['res.partner'].sudo().with_company(company)
        existing = Partner.search([
            ('vat', '=', clean),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ], limit=1)
        if existing:
            return {'id': existing.id, 'name': existing.name, 'vat': existing.vat, 'exists': True}

        pe_country = self.env.ref('base.pe', raise_if_not_found=False)
        vat_code = '6' if len(clean) == 11 else '1'
        id_type = self.env['l10n_latam.identification.type'].sudo().search([('l10n_pe_vat_code', '=', vat_code)], limit=1)
        new_p = Partner.create({
            'name': f'Cliente {clean}',
            'vat': clean,
            'company_id': company.id,
            'country_id': pe_country.id if pe_country else False,
            'l10n_latam_identification_type_id': id_type.id if id_type else False,
        })
        try:
            if len(clean) == 11 and hasattr(new_p, 'ConsultarRUC'):
                new_p.ConsultarRUC(clean)
            elif len(clean) == 8 and hasattr(new_p, 'ConsultarDNI'):
                new_p.ConsultarDNI(clean)
        except Exception as exc:
            _logger.warning("POS Express: consulta RUC/DNI %s fallback: %s", clean, exc)

        return {'id': new_p.id, 'name': new_p.name, 'vat': new_p.vat, 'exists': False}

    @api.model
    def close_session_from_pos(self, session_id, counted_cash, note=''):
        session = self.sudo().browse(int(session_id))
        if not session.exists() or session.state == 'closed':
            return {'error': 'El turno ya se encuentra cerrado.'}
        counted = float(counted_cash or 0.0)
        session.write({
            'cash_register_balance_end_real': counted,
            'closing_notes': (note or '').strip(),
            'state': 'closed',
            'stop_at': fields.Datetime.now(),
        })
        return {
            'success': True,
            'session_name': session.name,
            'expected_cash': round(session.cash_real_expected, 2),
            'counted_cash': round(session.cash_register_balance_end_real, 2),
            'difference': round(session.cash_register_difference, 2),
            'total_sales': round(session.cash_real_transaction + session.cash_real_bank + session.cash_real_other, 2),
        }
