"""
Servicio de Facturación Comercial SaaS y Máquina de Estados de Suscripciones (Sección 15.1 y ADR-001).
Administra el cálculo de importes, emisión de facturas de suscripción y transiciones de morosidad.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID


class SubscriptionState:
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class BillingService:
    # Tarifas estándar de add-ons (USD por mes)
    PRICE_PER_EXTRA_USER = 12.00
    PRICE_PER_EXTRA_STORAGE_GB = 1.50
    TAX_RATE_IGV = 0.18  # 18% IGV Perú

    # Días de gracia para pago antes de suspender el servicio
    GRACE_PERIOD_DAYS = 5

    @classmethod
    def calculate_invoice_amount(
        cls,
        base_price: float,
        extra_users: int = 0,
        extra_storage_gb: int = 0,
        apply_tax: bool = True,
    ) -> Dict[str, float]:
        """
        Calcula el desglose del cobro mensual recurrente:
        Subtotal = Plan Base + (Usuarios Extra * Tarifa) + (Almacenamiento Extra * Tarifa)
        Total = Subtotal + IGV
        """
        subtotal_base = float(base_price)
        subtotal_users = float(extra_users) * cls.PRICE_PER_EXTRA_USER
        subtotal_storage = float(extra_storage_gb) * cls.PRICE_PER_EXTRA_STORAGE_GB

        subtotal_neto = subtotal_base + subtotal_users + subtotal_storage
        igv_amount = round(subtotal_neto * cls.TAX_RATE_IGV, 2) if apply_tax else 0.00
        total_amount = round(subtotal_neto + igv_amount, 2)

        return {
            "subtotal_base": subtotal_base,
            "subtotal_users": subtotal_users,
            "subtotal_storage": subtotal_storage,
            "subtotal_neto": subtotal_neto,
            "igv_amount": igv_amount,
            "total_amount": total_amount,
        }

    @classmethod
    def evaluate_subscription_status(
        cls,
        current_status: str,
        period_end: datetime,
        is_paid: bool,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Máquina de estados para determinar la vigencia de la suscripción del tenant:
        - Si está pagado -> ACTIVE
        - Si expiró pero está dentro del periodo de gracia -> PAST_DUE (servicio activo con alertas)
        - Si expiró y superó el periodo de gracia -> SUSPENDED (bloqueo en proxy)
        """
        now = current_time or datetime.now(timezone.utc)
        
        if is_paid:
            return {
                "new_status": SubscriptionState.ACTIVE,
                "is_service_blocked": False,
                "reason": "Suscripción al día y pagada.",
            }

        if now <= period_end:
            return {
                "new_status": current_status,
                "is_service_blocked": False,
                "reason": "Periodo actual vigente.",
            }

        grace_deadline = period_end + timedelta(days=cls.GRACE_PERIOD_DAYS)
        if now <= grace_deadline:
            return {
                "new_status": SubscriptionState.PAST_DUE,
                "is_service_blocked": False,
                "grace_deadline": grace_deadline,
                "reason": f"Pago pendiente. Servicio en periodo de gracia hasta {grace_deadline.strftime('%Y-%m-%d')}.",
            }

        return {
            "new_status": SubscriptionState.SUSPENDED,
            "is_service_blocked": True,
            "reason": "Periodo de gracia expirado sin regularización de pago. Tenant suspendido temporalmente.",
        }

    @classmethod
    def generate_proforma_invoice(
        cls,
        invoice_number: str,
        tenant_name: str,
        plan_name: str,
        calculation: Dict[str, float],
        billing_period: str,
    ) -> Dict[str, Any]:
        """Genera el comprobante proforma comercial de SOFIA Platform."""
        return {
            "invoice_number": invoice_number,
            "issuer": "SOFIA Platform S.A.C.",
            "issuer_ruc": "20609999999",
            "customer_name": tenant_name,
            "plan_name": plan_name,
            "billing_period": billing_period,
            "line_items": [
                {"description": f"Suscripción Mensual - Plan {plan_name}", "amount": calculation["subtotal_base"]},
                {"description": "Usuarios Concurrentes Adicionales", "amount": calculation["subtotal_users"]},
                {"description": "Cuota de Almacenamiento NVMe Extra", "amount": calculation["subtotal_storage"]},
            ],
            "subtotal": calculation["subtotal_neto"],
            "tax_igv": calculation["igv_amount"],
            "total_payable": calculation["total_amount"],
            "currency": "USD",
        }
