# -*- coding: utf-8 -*-
"""
Endpoints REST del Hub Central de Consultas Perú (RUC, DNI y Tipo de Cambio SUNAT) (ADR-013).
Consumibles por:
- SOFIA ERP (Odoo 20) vía X-Internal-Service-Key en red interna Docker.
- Apps externas, POS, eCommerce y clientes de apisunat.pro vía Bearer sk_live_...
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_api_client_or_admin
from app.core.database import get_db
from app.models import ExchangeRate
from app.services.lookup_service import (
    get_exchange_rate_cached,
    lookup_dni_cached,
    lookup_ruc_cached,
)

router = APIRouter(prefix="/api/v1/lookup", tags=["Consultas Perú (RUC / DNI / TC)"])


@router.get("/ruc/{ruc}")
async def api_lookup_ruc(
    ruc: str,
    refresh: bool = Query(default=False),
    _auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await lookup_ruc_cached(db, ruc, force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/dni/{dni}")
async def api_lookup_dni(
    dni: str,
    refresh: bool = Query(default=False),
    _auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await lookup_dni_cached(db, dni, force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/exchange-rate")
async def api_get_exchange_rate(
    date: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    refresh: bool = Query(default=False),
    _auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_exchange_rate_cached(db, rate_date=date, currency=currency, force_refresh=refresh)
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/exchange-rate/history")
async def api_exchange_rate_history(
    currency: str = Query(default="USD", min_length=3, max_length=3),
    limit: int = Query(default=30, ge=1, le=90),
    _auth=Depends(get_api_client_or_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.currency == currency.upper())
        .order_by(desc(ExchangeRate.rate_date))
        .limit(limit)
    )
    return [
        {
            "date": r.rate_date,
            "currency": r.currency,
            "buy_rate": float(r.buy_rate),
            "sell_rate": float(r.sell_rate),
            "source": r.source,
        }
        for r in res.scalars().all()
    ]
