from odoo import api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import os
import requests
import time
import logging

_logger = logging.getLogger(__name__)

APISNETPE_FREE_URL = 'https://api.apis.net.pe/v1/tipo-cambio-sunat'
APISNETPE_FREE_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36')


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    inverse_company_rate_buy = fields.Float(
        string="Tipo de cambio Compra",
        digits=0,
    )

    @api.model
    def _build_rate_vals(self, currency, rate_date, company, buy, sell):
        return {
            'currency_id': currency.id,
            'name': rate_date,
            'company_id': company.id,
            'company_rate': 1.0 / sell if sell else 0.0,
            'inverse_company_rate': sell,
            'inverse_company_rate_buy': buy,
            'rate': 1.0 / sell if sell else 0.0,
        }

    @api.model
    def sync_from_migo(self, currency, fecha=None, company=None):
        company = company or self.env.company
        provider, token = self.env['api.data.provider.credential']._get_credentials('currency_rate')
        if provider != 'migo':
            _logger.info("Company '%s' ignorada (Proveedor es %s).", company.name, provider)
            return
        if not token:
            _logger.error("No se ha configurado el token del proveedor para la compania %s", company.name)
            return 0.0, 0.0

        if currency.name == 'USD':
            url = "https://api.migo.pe/api/v2/tipo-cambio/sunat/ultimo"
            params = {}
            adjust_to_sunat_date = False
        elif currency.name == 'EUR':
            url = "https://api.migo.pe/api/v2/tipo-cambio/sbs/ultimo"
            params = {
                "moneda": currency.name
            }
            adjust_to_sunat_date = True
        else:
            _logger.info("Moneda '%s' ignorada. Solo se sincroniza USD por SUNAT y EUR por SBS.", currency.name)
            return

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

        try:
            _logger.info("Iniciando solicitud a Migo. URL: %s | Params: %s", url, params)
            response = requests.get(url, params=params, headers=headers, timeout=10)
            _logger.info("Respuesta de Migo HTTP %s | Body: %s", response.status_code, response.text)

            if response.status_code != 200:
                _logger.error("Migo API returned status %s: %s", response.status_code, response.text)
                return

            try:
                data = response.json()
            except ValueError:
                _logger.error("Migo devolvio un JSON invalido: %s", response.text)
                return

            if not data.get('success'):
                _logger.error("Migo devolvio success=False: %s", response.text)
                return

            buy = float(data.get('precio_compra', 0))
            sell = float(data.get('precio_venta', 0))
            migo_fecha = data.get('fecha')

            if not buy or not sell or not migo_fecha:
                return
            rate_date = fields.Date.to_date(migo_fecha)
            if adjust_to_sunat_date:
                rate_date += relativedelta(days=1)

            existing = self.search([
                ('currency_id', '=', currency.id),
                ('name', '=', rate_date),
                ('company_id', '=', company.id)
            ], limit=1)

            vals = self._build_rate_vals(currency, rate_date, company, buy, sell)

            if existing:
                existing.write(vals)
                _logger.info("Tasa actualizada para %s: fecha origen %s, fecha Odoo %s", currency.name, migo_fecha, rate_date)
            else:
                self.create(vals)
                _logger.info("Tasa creada para %s: fecha origen %s, fecha Odoo %s", currency.name, migo_fecha, rate_date)

            return buy, sell

        except Exception as e:
            _logger.error("Error al consultar Migo: %s", str(e))
            return

    @api.model
    def sync_from_apisnetpe_free(self, currency, fecha=None, company=None):
        """Sincroniza el TC del día (o de una fecha) con el endpoint público
        v1 de apis.net.pe (sin token, solo USD). El endpoint aplica
        rate-limiting agresivo: se reintenta con pausas ante HTTP 429.
        """
        company = company or self.env.company
        provider, token = self.env['api.data.provider.credential']._get_credentials('currency_rate')
        if provider != 'apisnetpe_free':
            _logger.info("Company '%s' ignorada (Proveedor es %s).", company.name, provider)
            return
        if currency.name != 'USD':
            _logger.info("Moneda '%s' ignorada. El endpoint gratuito solo soporta USD.", currency.name)
            return

        rate_date = fecha or fields.Date.context_today(self.with_context(tz='America/Lima'))
        date_str = fields.Date.to_string(rate_date)

        # 1. Intentar primero mediante Sofia Gateway Hub (caché diario compartido + Decolecta, sin HTTP 429)
        gw_url = (os.environ.get('SOFIA_GATEWAY_URL') or '').strip().rstrip('/')
        if gw_url:
            try:
                gw_headers = {'Accept': 'application/json'}
                gw_key = (os.environ.get('INTERNAL_SERVICE_KEY') or '').strip()
                if gw_key:
                    gw_headers['X-Internal-Service-Key'] = gw_key
                gw_resp = requests.get(
                    f'{gw_url}/api/v1/lookup/exchange-rate',
                    params={'date': date_str},
                    headers=gw_headers,
                    timeout=10,
                )
                if gw_resp.status_code == 200:
                    gw_data = gw_resp.json()
                    buy = float(gw_data.get('buy_rate') or 0)
                    sell = float(gw_data.get('sell_rate') or 0)
                    if buy > 0 and sell > 0:
                        existing = self.search([
                            ('currency_id', '=', currency.id),
                            ('name', '=', rate_date),
                            ('company_id', '=', company.id),
                        ], limit=1)
                        vals = self._build_rate_vals(currency, rate_date, company, buy, sell)
                        if existing:
                            existing.write(vals)
                        else:
                            self.create(vals)
                        _logger.info(
                            "TC SUNAT sincronizado vía Sofia Gateway para %s (%s): compra %s, venta %s",
                            currency.name, company.name, buy, sell,
                        )
                        return buy, sell
            except Exception as exc:
                _logger.info("Sofia Gateway TC fallback a apis.net.pe: %s", exc)

        params = {'fecha': date_str}
        headers = {'User-Agent': APISNETPE_FREE_UA, 'Accept': 'application/json'}

        data = None
        for attempt in range(3):
            try:
                _logger.info("Solicitud a apis.net.pe (v1). URL: %s | Params: %s", APISNETPE_FREE_URL, params)
                response = requests.get(APISNETPE_FREE_URL, params=params, headers=headers, timeout=15)
                _logger.info("Respuesta apis.net.pe HTTP %s | Body: %s", response.status_code, response.text)
                if response.status_code == 429 and attempt < 2:
                    time.sleep(15)
                    continue
                if response.status_code != 200:
                    _logger.error("apis.net.pe v1 returned status %s: %s", response.status_code, response.text)
                    return
                data = response.json()
                break
            except ValueError:
                _logger.error("apis.net.pe devolvio un JSON invalido: %s", response.text)
                return
            except Exception as e:
                _logger.error("Error al consultar apis.net.pe: %s", str(e))
                return

        if not data:
            return

        buy = float(data.get('compra') or 0)
        sell = float(data.get('venta') or 0)
        migo_fecha = data.get('fecha')
        if not buy or not sell or not migo_fecha:
            _logger.error("apis.net.pe devolvio datos incompletos: %s", data)
            return

        rate_date = fields.Date.to_date(migo_fecha)

        existing = self.search([
            ('currency_id', '=', currency.id),
            ('name', '=', rate_date),
            ('company_id', '=', company.id)
        ], limit=1)

        vals = self._build_rate_vals(currency, rate_date, company, buy, sell)

        if existing:
            existing.write(vals)
            _logger.info("Tasa actualizada para %s (%s): compra %s, venta %s", currency.name, company.name, buy, sell)
        else:
            self.create(vals)
            _logger.info("Tasa creada para %s (%s): compra %s, venta %s", currency.name, company.name, buy, sell)

        return buy, sell

    @api.model
    def sync_range_from_migo(self, currency, date_from, date_to, company=None):
        """Sincroniza tipo de cambio SUNAT (USD) para un rango de fechas.

        Crea/actualiza una tasa por cada día devuelto por Migo, incluyendo
        fines de semana (donde Migo repite el último valor hábil).
        Retorna (created, updated, skipped).
        """
        company = company or self.env.company
        provider, token = self.env['api.data.provider.credential']._get_credentials('currency_rate')
        if provider != 'migo':
            raise UserError(self.env._(
                "El proveedor configurado (%(provider)s) no soporta histórico SUNAT.",
                provider=provider,
            ))
        if not token:
            raise UserError(self.env._(
                "No se ha configurado el token del proveedor para la compañía %(company)s.",
                company=company.name,
            ))
        if currency.name != 'USD':
            raise UserError(self.env._("El histórico SUNAT solo está disponible para USD."))

        if isinstance(date_from, str):
            date_from = fields.Date.to_date(date_from)
        if isinstance(date_to, str):
            date_to = fields.Date.to_date(date_to)

        url = "https://api.migo.pe/api/v2/tipo-cambio/sunat/historico"
        params = {
            'fecha_inicio': fields.Date.to_string(date_from),
            'fecha_fin': fields.Date.to_string(date_to),
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }

        try:
            _logger.info("Iniciando solicitud histórico a Migo. URL: %s | Params: %s", url, params)
            response = requests.get(url, params=params, headers=headers, timeout=20)
            _logger.info("Respuesta histórico Migo HTTP %s | Body: %s", response.status_code, response.text)
        except Exception as e:
            _logger.error("Error de conexión consultando histórico Migo: %s", str(e))
            raise UserError(self.env._("Error de conexión con Migo: %(error)s", error=str(e)))

        if response.status_code != 200:
            _logger.error("Migo histórico API returned status %s: %s", response.status_code, response.text)
            raise UserError(self.env._(
                "Migo devolvió HTTP %(status)s. Revise el token o el rango.",
                status=response.status_code,
            ))

        try:
            data = response.json()
        except ValueError:
            raise UserError(self.env._(
                "Migo devolvió una respuesta JSON inválida: %(body)s",
                body=response.text,
            ))

        if not data.get('success'):
            msg = data.get('message') or self.env._("Migo no devolvió datos para el rango solicitado.")
            raise UserError(self.env._("%(msg)s", msg=msg))

        items = data.get('data') or []
        if not items:
            raise UserError(self.env._("Migo no devolvió ningún registro para el rango solicitado."))

        created = 0
        updated = 0
        skipped = 0

        for item in items:
            buy_raw = item.get('precio_compra')
            sell_raw = item.get('precio_venta')
            migo_fecha = item.get('fecha')

            if buy_raw in (None, '') or sell_raw in (None, '') or not migo_fecha:
                skipped += 1
                continue

            try:
                buy = float(buy_raw)
                sell = float(sell_raw)
            except (TypeError, ValueError):
                skipped += 1
                continue

            if not buy or not sell:
                skipped += 1
                continue

            rate_date = fields.Date.to_date(migo_fecha)

            existing = self.search([
                ('currency_id', '=', currency.id),
                ('name', '=', rate_date),
                ('company_id', '=', company.id),
            ], limit=1)

            vals = self._build_rate_vals(currency, rate_date, company, buy, sell)

            if existing:
                existing.write(vals)
                updated += 1
            else:
                self.create(vals)
                created += 1

        _logger.info(
            "Histórico sincronizado para %s (%s): %d creadas, %d actualizadas, %d saltadas",
            currency.name, company.name, created, updated, skipped,
        )
        return created, updated, skipped

    @api.model
    def cron_sync_exchange_rates(self):
        currencies = self.env['res.currency'].search([('name', 'in', ['USD', 'EUR'])])
        if not currencies:
            return

        fecha = fields.Date.context_today(self.with_context(tz='America/Lima'))

        for company in self.env['res.company'].search([]):
            provider, token = self.env['api.data.provider.credential']._get_credentials('currency_rate')

            if provider == 'migo':
                if not token:
                    continue
                for currency in currencies:
                    try:
                        self.sync_from_migo(currency, fecha, company=company)
                    except Exception as e:
                        _logger.error("Error en cron de para %s: %s", company.name, str(e))
            elif provider == 'apisnetpe_free':
                for currency in currencies:
                    try:
                        self.sync_from_apisnetpe_free(currency, fecha, company=company)
                    except Exception as e:
                        _logger.error("Error en cron de para %s: %s", company.name, str(e))
            else:
                _logger.info("Company '%s' ignorada por cron (Proveedor es %s).", company.name, provider)
