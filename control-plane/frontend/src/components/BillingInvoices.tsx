"use client";

import React from "react";
import { Receipt, CheckCircle, Download, Calendar, CreditCard } from "lucide-react";
import { TenantSummary } from "./TenantSelector";

interface BillingInvoicesProps {
  tenant: TenantSummary;
}

export const BillingInvoices: React.FC<BillingInvoicesProps> = ({ tenant }) => {
  const invoices = [
    {
      id: "INV-2026-0011",
      period: "Noviembre 2026",
      date: "01/11/2026",
      amount: "S/ 390.00",
      status: "PAID",
      description: `Suscripción Mensual SaaS (${tenant.planName}) + Almacenamiento`,
    },
    {
      id: "INV-2026-0010",
      period: "Octubre 2026",
      date: "01/10/2026",
      amount: "S/ 390.00",
      status: "PAID",
      description: `Suscripción Mensual SaaS (${tenant.planName})`,
    },
    {
      id: "INV-2026-0009",
      period: "Septiembre 2026",
      date: "01/09/2026",
      amount: "S/ 350.00",
      status: "PAID",
      description: `Suscripción Mensual SaaS (${tenant.planName})`,
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold text-sky-600 uppercase tracking-wider">
            Facturación SaaS
          </span>
          <h2 className="text-lg font-bold text-slate-900 mt-0.5">
            Historial de Facturación y Comprobantes SUNAT
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Próxima renovación:</span>
          <span className="text-xs font-bold text-slate-800">01 de Diciembre, 2026</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-slate-400 uppercase font-semibold">
              <th className="pb-3 pl-2">Comprobante</th>
              <th className="pb-3">Periodo / Concepto</th>
              <th className="pb-3">Fecha de Emisión</th>
              <th className="pb-3">Total</th>
              <th className="pb-3">Estado</th>
              <th className="pb-3 text-right pr-2">Descargas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3 pl-2 font-mono font-medium text-slate-800 flex items-center gap-2">
                  <Receipt className="w-4 h-4 text-sky-600" />
                  {inv.id}
                </td>
                <td className="py-3 text-slate-600">{inv.description}</td>
                <td className="py-3 text-slate-500">{inv.date}</td>
                <td className="py-3 font-semibold text-slate-900">{inv.amount}</td>
                <td className="py-3">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle className="w-3 h-3" /> Pagado
                  </span>
                </td>
                <td className="py-3 text-right pr-2">
                  <button className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-1 text-[11px]">
                    <Download className="w-3.5 h-3.5" /> PDF / XML
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
