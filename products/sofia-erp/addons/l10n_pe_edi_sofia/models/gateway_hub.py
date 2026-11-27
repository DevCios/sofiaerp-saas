# -*- coding: utf-8 -*-
"""
Conector Centralizado Odoo 20 -> Sofia SUNAT Gateway Hub (ADR-013):
- Consulta RUC y DNI vía red interna Docker (SOFIA_GATEWAY_URL/api/v1/lookup/...).
- Sincronización diaria automática del Tipo de Cambio SUNAT (USD -> PEN) en res.currency.rate.
"""
import logging
import os

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _gateway_base_url():
    return (os.getenv("SOFIA_GATEWAY_URL") or "http://sunat-gateway-api:8010").rstrip("/")


def _gateway_headers():
    headers = {"Accept": "application/json"}
    internal_key = (os.getenv("INTERNAL_SERVICE_KEY") or "").strip()
    if internal_key:
        headers["X-Internal-Service-Key"] = internal_key
    return headers


class ResPartnerGatewayLookup(models.Model):
    _inherit = "res.partner"

    @api.model
    def sofia_gateway_lookup_ruc(self, ruc):
        """Consulta RUC en Sofia Gateway Hub (caché compartido PostgreSQL)."""
        clean = (ruc or "").strip()
        if len(clean) != 11 or not clean.isdigit():
            return {}
        try:
            r = requests.get(
                f"{_gateway_base_url()}/api/v1/lookup/ruc/{clean}",
                headers=_gateway_headers(),
                timeout=8,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            _logger.warning("SOFIA Gateway lookup RUC %s error: %s", clean, exc)
        return {}

    @api.model
    def sofia_gateway_lookup_dni(self, dni):
        """Consulta DNI en Sofia Gateway Hub (caché compartido PostgreSQL)."""
        clean = (dni or "").strip()
        if len(clean) != 8 or not clean.isdigit():
            return {}
        try:
            r = requests.get(
                f"{_gateway_base_url()}/api/v1/lookup/dni/{clean}",
                headers=_gateway_headers(),
                timeout=8,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            _logger.warning("SOFIA Gateway lookup DNI %s error: %s", clean, exc)
        return {}


class ResCurrencyRateGatewaySync(models.Model):
    _inherit = "res.currency.rate"

    @api.model
    def cron_sync_sunat_exchange_rate_from_gateway(self):
        """
        Cron diario Odoo 20: obtiene el Tipo de Cambio oficial SUNAT (USD -> PEN)
        desde Sofia Gateway Hub y actualiza res.currency.rate para todas las compañías en PEN.
        """
        try:
            r = requests.get(
                f"{_gateway_base_url()}/api/v1/lookup/exchange-rate",
                headers=_gateway_headers(),
                timeout=10,
            )
            if r.status_code != 200:
                _logger.warning("SOFIA Gateway TC devolvió HTTP %s", r.status_code)
                return False
            data = r.json()
        except Exception as exc:
            _logger.warning("SOFIA Gateway TC error de red: %s", exc)
            return False

        sell_rate = float(data.get("sell_rate") or 0.0)
        rate_date = data.get("date") or fields.Date.context_today(self)
        if sell_rate <= 0:
            return False

        usd = self.env["res.currency"].sudo().search([("name", "=", "USD")], limit=1)
        if not usd:
            return False

        # En Odoo, si la compañía opera en PEN (1 PEN = 1/sell_rate USD), inverse_company_rate = sell_rate
        companies = self.env["res.company"].sudo().search([("currency_id.name", "=", "PEN")])
        updated = 0
        for company in companies:
            existing = self.sudo().search(
                [("currency_id", "=", usd.id), ("company_id", "=", company.id), ("name", "=", rate_date)],
                limit=1,
            )
            vals = {"rate": 1.0 / sell_rate}
            if existing:
                existing.write(vals)
            else:
                self.sudo().create(
                    {
                        "currency_id": usd.id,
                        "company_id": company.id,
                        "name": rate_date,
                        "rate": 1.0 / sell_rate,
                    }
                )
            updated += 1
        _logger.info("SOFIA Gateway TC SUNAT sincronizado (%s): 1 USD = S/ %.4f (%s compañías)", rate_date, sell_rate, updated)
        return True
