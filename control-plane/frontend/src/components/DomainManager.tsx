"use client";

import React, { useState } from "react";
import { Globe, ShieldCheck, Clock, CheckCircle2, Copy, AlertCircle, RefreshCw } from "lucide-react";
import { TenantSummary } from "./TenantSelector";

interface DomainManagerProps {
  tenant: TenantSummary;
}

export const DomainManager: React.FC<DomainManagerProps> = ({ tenant }) => {
  const [copied, setCopied] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState<string | null>(null);

  const challengeKey = `_sofia-challenge.${tenant.domain}`;
  const challengeValue = `sofia-verification-${tenant.slug}-94f8b2c1`;

  const handleCopy = () => {
    navigator.clipboard?.writeText(challengeValue);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleVerify = () => {
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setVerificationStatus("VERIFIED");
    }, 1200);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold text-sky-600 uppercase tracking-wider">
            Conectividad & Marca
          </span>
          <h2 className="text-lg font-bold text-slate-900 mt-0.5">
            Dominios Personalizados & Certificados TLS
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5" /> Let's Encrypt ACME Activo
          </span>
        </div>
      </div>

      {/* Dominio Principal Activo */}
      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-700 shadow-sm">
            <Globe className="w-5 h-5 text-sky-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 text-sm">{tenant.domain}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-800">
                Principal
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Enrutamiento gestionado con Nginx Edge Gateway y terminación TLS 1.3
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin text-sky-600" : ""}`} />
            {verifying ? "Consultando DNS..." : "Revalidar DNS"}
          </button>
        </div>
      </div>

      {/* Instrucciones de Configuración DNS */}
      <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-3">
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-semibold text-amber-900">
              Configuración de DNS requerida para dominios propios
            </h4>
            <p className="text-xs text-amber-700 mt-0.5">
              Para validar la propiedad de tu dominio, crea los siguientes registros en tu proveedor de DNS (Cloudflare, GoDaddy, Route53):
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div className="bg-white rounded border border-amber-200/70 p-3 text-xs">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Registro 1 (CNAME)</span>
            <div className="flex justify-between items-center mt-1 font-mono text-slate-800">
              <span>{tenant.domain}</span>
              <span className="text-slate-400">→</span>
              <span className="text-sky-700 font-semibold">domains.sofiaerp.com</span>
            </div>
          </div>

          <div className="bg-white rounded border border-amber-200/70 p-3 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Registro 2 (TXT Desafío)</span>
              <button
                onClick={handleCopy}
                className="text-sky-600 hover:text-sky-800 text-[11px] font-medium inline-flex items-center gap-1"
              >
                <Copy className="w-3 h-3" /> {copied ? "Copiado" : "Copiar"}
              </button>
            </div>
            <div className="mt-1 font-mono text-[11px] text-slate-800 truncate">
              {challengeKey} = {challengeValue}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
