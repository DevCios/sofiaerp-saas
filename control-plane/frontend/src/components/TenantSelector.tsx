"use client";

import React from "react";
import { Building2, ExternalLink, ShieldCheck, Users, HardDrive } from "lucide-react";

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  domain: string;
  status: "ACTIVE" | "PAST_DUE" | "SUSPENDED";
  activeUsers: number;
  maxUsers: number;
  storageGb: number;
  maxStorageGb: number;
  planName: string;
}

interface TenantSelectorProps {
  tenants: TenantSummary[];
  onSelectTenant: (tenant: TenantSummary) => void;
  selectedTenantId?: string;
}

export const TenantSelector: React.FC<TenantSelectorProps> = ({
  tenants,
  onSelectTenant,
  selectedTenantId,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {tenants.map((t) => {
        const isSelected = t.id === selectedTenantId;
        const isSuspended = t.status === "SUSPENDED";

        return (
          <div
            key={t.id}
            onClick={() => !isSuspended && onSelectTenant(t)}
            className={`relative rounded-xl border p-5 transition-all cursor-pointer bg-white shadow-sm hover:shadow-md ${
              isSelected
                ? "border-sky-600 ring-2 ring-sky-100"
                : "border-slate-200 hover:border-slate-300"
            } ${isSuspended ? "opacity-60 cursor-not-allowed bg-slate-50" : ""}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-sky-50 text-sky-700">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 leading-snug">{t.name}</h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{t.domain}</p>
                </div>
              </div>
              <span
                className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full ${
                  t.status === "ACTIVE"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : t.status === "PAST_DUE"
                    ? "bg-amber-50 text-amber-700 border border-amber-200"
                    : "bg-rose-50 text-rose-700 border border-rose-200"
                }`}
              >
                {t.status === "ACTIVE" ? "Activo" : t.status === "PAST_DUE" ? "En Gracia" : "Suspendido"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-100 text-xs text-slate-600">
              <div className="flex items-center gap-1.5">
                <Users className="w-4 h-4 text-slate-400" />
                <span>
                  <strong>{t.activeUsers}</strong> / {t.maxUsers} usuarios
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-slate-400" />
                <span>
                  <strong>{t.storageGb}</strong> / {t.maxStorageGb} GB
                </span>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between pt-2">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                Plan {t.planName}
              </span>
              <a
                href={`https://${t.domain}`}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => isSuspended && e.preventDefault()}
                className="inline-flex items-center gap-1 text-xs font-semibold text-sky-600 hover:text-sky-800"
              >
                Ingresar al ERP <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        );
      })}
    </div>
  );
};
