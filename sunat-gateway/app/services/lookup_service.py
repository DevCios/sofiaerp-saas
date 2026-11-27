# -*- coding: utf-8 -*-
"""
Hub Central de Consultas Fiscales Perú (RUC, DNI y Tipo de Cambio SUNAT) (ADR-013).

Características:
- Validación algorítmica de RUC (dígito verificador módulo 11 SUNAT) y DNI (8 dígitos).
- Caché persistente compartido en PostgreSQL (TTL 7 días RUC / 30 días DNI / permanente por fecha TC).
- Cascada resiliente multi-proveedor (apis.net.pe v2/v1 -> apisperu) con fallback al último caché.
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import ExchangeRate, IdentityCache

settings = get_settings()
_logger = logging.getLogger(__name__)


def validate_peru_ruc(ruc: str) -> bool:
    """Valida formato (11 dígitos, prefijos válidos 10/15/16/17/20) y dígito verificador SUNAT."""
    clean = (ruc or "").strip()
    if not re.fullmatch(r"\d{11}", clean):
        return False
    if clean[:2] not in ("10", "15", "16", "17", "20"):
        return False
    factors = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(clean[i]) * factors[i] for i in range(10))
    rem = 11 - (total % 11)
    check = 0 if rem == 10 else (1 if rem == 11 else rem)
    return check == int(clean[10])


def validate_peru_dni(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", (dni or "").strip()))


def today_lima_str() -> str:
    return datetime.now(timezone.utc).astimezone(ZoneInfo(settings.LIMA_TZ)).strftime("%Y-%m-%d")


def _apis_net_pe_token() -> str:
    return (settings.APIS_NET_PE_TOKEN or os.getenv("APIS_NET_PE_TOKEN") or "").strip()


def _apisperu_token() -> str:
    return (settings.APISPERU_TOKEN or os.getenv("APISPERU_TOKEN") or "").strip()


async def _fetch_ruc_external(ruc: str) -> Optional[tuple[dict[str, Any], str]]:
    """Consulta proveedores externos de RUC y normaliza el contrato de salida."""
    token_v2 = _apis_net_pe_token()
    token_ap = _apisperu_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. apis.net.pe (v2 con token o v1 pública)
        try:
            if token_v2:
                r = await client.get(
                    f"https://api.apis.net.pe/v2/sunat/ruc?numero={ruc}",
                    headers={"Authorization": f"Bearer {token_v2}", "Accept": "application/json"},
                )
                src = "apis.net.pe/v2"
            else:
                r = await client.get(f"https://api.apis.net.pe/v1/ruc?numero={ruc}", headers={"Accept": "application/json"})
                src = "apis.net.pe/v1"
            if r.status_code == 200:
                d = r.json()
                name = (d.get("razonSocial") or d.get("nombre") or "").strip()
                if name:
                    return (
                        {
                            "ruc": ruc,
                            "business_name": name,
                            "trade_name": (d.get("nombreComercial") or name).strip(),
                            "status": (d.get("estado") or "").strip(),
                            "condition": (d.get("condicion") or "").strip(),
                            "address": (d.get("direccion") or "").strip(),
                            "ubigeo": (d.get("ubigeo") or "").strip(),
                            "department": (d.get("departamento") or "").strip(),
                            "province": (d.get("provincia") or "").strip(),
                            "district": (d.get("distrito") or "").strip(),
                        },
                        src,
                    )
        except Exception as exc:
            _logger.warning("Lookup RUC apis.net.pe falló para %s: %s", ruc, exc)

        # 2. apisperu (si token configurado)
        if token_ap:
            try:
                r = await client.get(f"https://dniruc.apisperu.com/api/v1/ruc/{ruc}?token={token_ap}")
                if r.status_code == 200:
                    d = r.json()
                    name = (d.get("razonSocial") or "").strip()
                    if name:
                        return (
                            {
                                "ruc": ruc,
                                "business_name": name,
                                "trade_name": (d.get("nombreComercial") or name).strip(),
                                "status": (d.get("estado") or "").strip(),
                                "condition": (d.get("condicion") or "").strip(),
                                "address": (d.get("direccion") or "").strip(),
                                "ubigeo": (d.get("ubigeo") or "").strip(),
                                "department": (d.get("departamento") or "").strip(),
                                "province": (d.get("provincia") or "").strip(),
                                "district": (d.get("distrito") or "").strip(),
                            },
                            "apisperu",
                        )
            except Exception as exc:
                _logger.warning("Lookup RUC apisperu falló para %s: %s", ruc, exc)

    return None


async def _fetch_dni_external(dni: str) -> Optional[tuple[dict[str, Any], str]]:
    token_v2 = _apis_net_pe_token()
    token_ap = _apisperu_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if token_v2:
                r = await client.get(
                    f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}",
                    headers={"Authorization": f"Bearer {token_v2}", "Accept": "application/json"},
                )
                src = "apis.net.pe/v2"
            else:
                r = await client.get(f"https://api.apis.net.pe/v1/dni?numero={dni}", headers={"Accept": "application/json"})
                src = "apis.net.pe/v1"
            if r.status_code == 200:
                d = r.json()
                first = (d.get("nombres") or "").strip()
                pat = (d.get("apellidoPaterno") or "").strip()
                mat = (d.get("apellidoMaterno") or "").strip()
                full = (d.get("nombre") or d.get("nombreCompleto") or f"{first} {pat} {mat}").strip()
                if full:
                    return (
                        {
                            "dni": dni,
                            "full_name": " ".join(full.split()),
                            "first_names": first,
                            "paternal_surname": pat,
                            "maternal_surname": mat,
                        },
                        src,
                    )
        except Exception as exc:
            _logger.warning("Lookup DNI apis.net.pe falló para %s: %s", dni, exc)

        if token_ap:
            try:
                r = await client.get(f"https://dniruc.apisperu.com/api/v1/dni/{dni}?token={token_ap}")
                if r.status_code == 200:
                    d = r.json()
                    first = (d.get("nombres") or "").strip()
                    pat = (d.get("apellidoPaterno") or "").strip()
                    mat = (d.get("apellidoMaterno") or "").strip()
                    full = f"{first} {pat} {mat}".strip()
                    if full:
                        return (
                            {
                                "dni": dni,
                                "full_name": " ".join(full.split()),
                                "first_names": first,
                                "paternal_surname": pat,
                                "maternal_surname": mat,
                            },
                            "apisperu",
                        )
            except Exception as exc:
                _logger.warning("Lookup DNI apisperu falló para %s: %s", dni, exc)

    return None


async def _fetch_exchange_rate_external(rate_date: str) -> Optional[tuple[float, float, str, str]]:
    """Retorna (buy_rate, sell_rate, actual_date, source) desde SUNAT/apis.net.pe."""
    token_v2 = _apis_net_pe_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if token_v2:
                r = await client.get(
                    f"https://api.apis.net.pe/v2/sunat/tipo-cambio?date={rate_date}",
                    headers={"Authorization": f"Bearer {token_v2}", "Accept": "application/json"},
                )
                src = "sunat/apis.net.pe-v2"
            else:
                r = await client.get(
                    f"https://api.apis.net.pe/v1/tipo-cambio-sunat?fecha={rate_date}",
                    headers={"Accept": "application/json"},
                )
                src = "sunat/apis.net.pe-v1"
            if r.status_code == 200:
                d = r.json()
                buy = float(d.get("precioCompra") or d.get("compra") or 0)
                sell = float(d.get("precioVenta") or d.get("venta") or 0)
                actual_date = str(d.get("fecha") or rate_date)[:10]
                if buy > 0 and sell > 0:
                    return buy, sell, actual_date, src
        except Exception as exc:
            _logger.warning("Lookup TC apis.net.pe falló para %s: %s", rate_date, exc)

        # Fallback público tipo de cambio USD->PEN
        try:
            r = await client.get("https://open.er-api.com/v6/latest/USD")
            if r.status_code == 200:
                pen = float((r.json().get("rates") or {}).get("PEN") or 0)
                if pen > 0:
                    return round(pen - 0.005, 4), round(pen + 0.005, 4), rate_date, "open.er-api-fallback"
        except Exception as exc:
            _logger.warning("Lookup TC fallback falló: %s", exc)

    return None


async def lookup_ruc_cached(db: AsyncSession, ruc: str, force_refresh: bool = False) -> dict[str, Any]:
    clean = (ruc or "").strip()
    if not validate_peru_ruc(clean):
        raise ValueError(f"RUC '{clean}' inválido (debe tener 11 dígitos y dígito verificador SUNAT válido).")

    now = datetime.now(timezone.utc)
    cached = (
        await db.execute(select(IdentityCache).where(IdentityCache.doc_type == "RUC", IdentityCache.doc_number == clean))
    ).scalar_one_or_none()

    if cached and not force_refresh and cached.expires_at > now:
        return {**cached.payload, "source": cached.source, "cached": True, "stale_fallback": False}

    fetched = await _fetch_ruc_external(clean)
    if fetched:
        payload, src = fetched
        exp = now + timedelta(days=settings.RUC_CACHE_TTL_DAYS)
        if cached:
            cached.payload = payload
            cached.source = src
            cached.fetched_at = now
            cached.expires_at = exp
        else:
            db.add(IdentityCache(doc_type="RUC", doc_number=clean, payload=payload, source=src, fetched_at=now, expires_at=exp))
        await db.commit()
        return {**payload, "source": src, "cached": False, "stale_fallback": False}

    if cached:
        return {**cached.payload, "source": cached.source, "cached": True, "stale_fallback": True}

    raise LookupError(f"No se pudo consultar el RUC {clean} en los proveedores externos. Configura APIS_NET_PE_TOKEN o APISPERU_TOKEN.")


async def lookup_dni_cached(db: AsyncSession, dni: str, force_refresh: bool = False) -> dict[str, Any]:
    clean = (dni or "").strip()
    if not validate_peru_dni(clean):
        raise ValueError(f"DNI '{clean}' inválido (debe tener exactamente 8 dígitos).")

    now = datetime.now(timezone.utc)
    cached = (
        await db.execute(select(IdentityCache).where(IdentityCache.doc_type == "DNI", IdentityCache.doc_number == clean))
    ).scalar_one_or_none()

    if cached and not force_refresh and cached.expires_at > now:
        return {**cached.payload, "source": cached.source, "cached": True, "stale_fallback": False}

    fetched = await _fetch_dni_external(clean)
    if fetched:
        payload, src = fetched
        exp = now + timedelta(days=settings.DNI_CACHE_TTL_DAYS)
        if cached:
            cached.payload = payload
            cached.source = src
            cached.fetched_at = now
            cached.expires_at = exp
        else:
            db.add(IdentityCache(doc_type="DNI", doc_number=clean, payload=payload, source=src, fetched_at=now, expires_at=exp))
        await db.commit()
        return {**payload, "source": src, "cached": False, "stale_fallback": False}

    if cached:
        return {**cached.payload, "source": cached.source, "cached": True, "stale_fallback": True}

    raise LookupError(f"No se pudo consultar el DNI {clean} en los proveedores externos. Configura APIS_NET_PE_TOKEN o APISPERU_TOKEN.")


async def get_exchange_rate_cached(
    db: AsyncSession,
    rate_date: Optional[str] = None,
    currency: str = "USD",
    force_refresh: bool = False,
) -> dict[str, Any]:
    target_date = (rate_date or today_lima_str()).strip()[:10]
    curr = (currency or "USD").strip().upper()

    existing = (
        await db.execute(
            select(ExchangeRate).where(ExchangeRate.rate_date == target_date, ExchangeRate.currency == curr)
        )
    ).scalar_one_or_none()
    if existing and not force_refresh:
        return {
            "date": existing.rate_date,
            "currency": existing.currency,
            "buy_rate": float(existing.buy_rate),
            "sell_rate": float(existing.sell_rate),
            "source": existing.source,
            "cached": True,
            "fallback_from_date": None,
        }

    fetched = await _fetch_exchange_rate_external(target_date)
    if fetched:
        buy, sell, actual_date, src = fetched
        now = datetime.now(timezone.utc)
        if existing:
            existing.buy_rate = buy
            existing.sell_rate = sell
            existing.source = src
            existing.fetched_at = now
        else:
            db.add(
                ExchangeRate(
                    rate_date=target_date,
                    currency=curr,
                    buy_rate=buy,
                    sell_rate=sell,
                    source=src,
                    fetched_at=now,
                )
            )
        await db.commit()
        return {
            "date": target_date,
            "currency": curr,
            "buy_rate": buy,
            "sell_rate": sell,
            "source": src,
            "cached": False,
            "fallback_from_date": actual_date if actual_date != target_date else None,
        }

    # Fallback al último tipo de cambio registrado en BD (fines de semana / feriados / caída externa)
    last_rate = (
        await db.execute(
            select(ExchangeRate)
            .where(ExchangeRate.currency == curr, ExchangeRate.rate_date <= target_date)
            .order_by(desc(ExchangeRate.rate_date))
            .limit(1)
        )
    ).scalar_one_or_none()
    if last_rate:
        return {
            "date": target_date,
            "currency": last_rate.currency,
            "buy_rate": float(last_rate.buy_rate),
            "sell_rate": float(last_rate.sell_rate),
            "source": last_rate.source,
            "cached": True,
            "fallback_from_date": last_rate.rate_date,
        }

    raise LookupError(f"No se pudo obtener el Tipo de Cambio SUNAT para {target_date}.")
