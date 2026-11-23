"""
Pruebas Unitarias para el Servicio de Facturación Comercial SaaS y Máquina de Estados de Suscripción.
"""
from datetime import datetime, timedelta, timezone
import unittest
from app.services.billing_service import BillingService, SubscriptionState


class TestBillingService(unittest.TestCase):
    def test_invoice_calculation(self):
        # Base: $100, 2 usuarios extra ($24), 10 GB extra ($15)
        calc = BillingService.calculate_invoice_amount(
            base_price=100.0,
            extra_users=2,
            extra_storage_gb=10,
            apply_tax=True,
        )
        self.assertEqual(calc["subtotal_base"], 100.0)
        self.assertEqual(calc["subtotal_users"], 24.0)
        self.assertEqual(calc["subtotal_storage"], 15.0)
        self.assertEqual(calc["subtotal_neto"], 139.0)
        # 139 * 0.18 = 25.02
        self.assertEqual(calc["igv_amount"], 25.02)
        self.assertEqual(calc["total_amount"], 164.02)

    def test_subscription_state_transitions(self):
        now = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
        
        # 1. Periodo aún vigente
        future_end = now + timedelta(days=10)
        res_active = BillingService.evaluate_subscription_status(
            current_status=SubscriptionState.ACTIVE,
            period_end=future_end,
            is_paid=False,
            current_time=now,
        )
        self.assertEqual(res_active["new_status"], SubscriptionState.ACTIVE)
        self.assertFalse(res_active["is_service_blocked"])

        # 2. Vencido pero dentro de los 5 días de gracia (PAST_DUE)
        past_end_recent = now - timedelta(days=2)
        res_grace = BillingService.evaluate_subscription_status(
            current_status=SubscriptionState.ACTIVE,
            period_end=past_end_recent,
            is_paid=False,
            current_time=now,
        )
        self.assertEqual(res_grace["new_status"], SubscriptionState.PAST_DUE)
        self.assertFalse(res_grace["is_service_blocked"])

        # 3. Vencido y superó los 5 días de gracia (SUSPENDED)
        past_end_old = now - timedelta(days=8)
        res_suspended = BillingService.evaluate_subscription_status(
            current_status=SubscriptionState.PAST_DUE,
            period_end=past_end_old,
            is_paid=False,
            current_time=now,
        )
        self.assertEqual(res_suspended["new_status"], SubscriptionState.SUSPENDED)
        self.assertTrue(res_suspended["is_service_blocked"])

    def test_proforma_invoice_generation(self):
        calc = BillingService.calculate_invoice_amount(base_price=50.0)
        proforma = BillingService.generate_proforma_invoice(
            invoice_number="INV-2026-0001",
            tenant_name="Empresa Textil",
            plan_name="Básico",
            calculation=calc,
            billing_period="Noviembre 2026",
        )
        self.assertEqual(proforma["invoice_number"], "INV-2026-0001")
        self.assertEqual(proforma["customer_name"], "Empresa Textil")
        self.assertEqual(len(proforma["line_items"]), 3)
        self.assertEqual(proforma["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
