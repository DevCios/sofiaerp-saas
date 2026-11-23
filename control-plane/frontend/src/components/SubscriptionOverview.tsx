"use client";

import React from "react";
import { CreditCard, CheckCircle2, AlertTriangle, ArrowUpRight } from "lucide-react";
import { TenantSummary } from "./TenantSelector";

interface SubscriptionOverviewProps {
  tenant: TenantSummary;
}

export const SubscriptionOverview: React.FC<SubscriptionOverviewProps> = ({ tenant }) => {
  const storagePercent = Math.min(100, Math.round((tenant.storageGb / tenant.maxStorageGb) * 100));
  const userPercent = Math.min(100, Math.round((tenant.activeUsers / tenant.maxUsers) * 100));

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold text-sky-600 uppercase tracking-wider">
            Suscripción Comercial SOFIA
          </span>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Plan {tenant.planName} — {tenant.name}
          </h2>
        </div>
        <button className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs transition-colors shadow-sm">
          Ampliar Capacidad / Upgrade <ArrowUpRight className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* Métrica de Usuarios */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="font-medium text-slate-600">Usuarios Concurrentes Contratados</span>
            <span className="font-semibold text-slate-900">
              {tenant.activeUsers} de {tenant.maxUsers} en uso
            </span>
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all rounded-full ${
                userPercent > 85 ? "bg-rose-500" : "bg-sky-500"
              }`}
              style={{ width: `${userPercent}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-400">
            {tenant.maxUsers - tenant.activeUsers} licencias disponibles para asignación inmediata.
          </p>
        </div>

        {/* Métrica de Almacenamiento */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="font-medium text-slate-600">Almacenamiento NVMe + Filestore</span>
            <span className="font-semibold text-slate-900">
              {tenant.storageGb} GB de {tenant.maxStorageGb} GB
            </span>
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all rounded-full ${
                storagePercent > 85 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${storagePercent}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-400">
            Respaldos automáticos en Google Drive sincronizados diariamente.
          </p>
        </div>
      </div>
    </div>
  );
};
