# -*- coding: utf-8 -*-
"""
Servicio puro de cálculo de comisiones de Mercado Wanka.
Regla oficial:
- Comisión variable sobre el valor total (price_total): 5.0% por defecto (o tasa personalizada por vendedor / categoría).
- Cargo fijo por uso de plataforma: S/ 0.50 por orden/venta.
- Mercado Wanka SOLO factura al vendedor la comisión + uso de plataforma.
"""

DEFAULT_COMMISSION_RATE = 5.0
DEFAULT_PLATFORM_FEE = 0.50


def resolve_commission_rate(seller=None, category=None) -> float:
    if seller and getattr(seller, 'marketplace_custom_commission_rate', 0.0) > 0:
        return float(seller.marketplace_custom_commission_rate)
    if category and getattr(category, 'marketplace_commission_rate', 0.0) > 0:
        return float(category.marketplace_commission_rate)
    return DEFAULT_COMMISSION_RATE


def compute_line_commission(price_total: float, rate_pct: float) -> float:
    return round((float(price_total or 0.0) * float(rate_pct or 0.0)) / 100.0, 2)


def compute_order_commission_breakdown(line_commissions: list[float], amount_total: float, platform_fee: float = DEFAULT_PLATFORM_FEE) -> dict:
    var_total = round(sum(float(c or 0.0) for c in line_commissions), 2)
    fee = round(float(platform_fee if platform_fee is not None else DEFAULT_PLATFORM_FEE), 2)
    comm_total = round(var_total + fee, 2)
    seller_net = round(max(0.0, float(amount_total or 0.0) - comm_total), 2)
    return {
        'commission_variable': var_total,
        'platform_fee': fee,
        'commission_total': comm_total,
        'seller_net': seller_net,
    }
