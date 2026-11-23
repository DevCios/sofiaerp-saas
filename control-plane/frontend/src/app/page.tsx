"use client";

import React, { useState } from "react";
import { TenantSelector, TenantSummary } from "../components/TenantSelector";
import { SubscriptionOverview } from "../components/SubscriptionOverview";
import { DomainManager } from "../components/DomainManager";
import { BillingInvoices } from "../components/BillingInvoices";
import { Layers, LogOut, Settings, Globe, CreditCard, Activity } from "lucide-react";

const INITIAL_TENANTS: TenantSummary[] = [
  {
    id: "1",
    name: "Constructora del Sur S.A.C.",
    slug: "constructora-sur",
    domain: "erp.constructorasur.pe",
    status: "ACTIVE",
    activeUsers: 4,
    maxUsers: 10,
    storageGb: 4.2,
    maxStorageGb: 20,
    planName: "Profesional",
  },
  {
    id: "2",
    name: "Minera Andina de Exploraciones",
    slug: "minera-andina",
    domain: "erp.mineraandina.com",
    status: "ACTIVE",
    activeUsers: 8,
    maxUsers: 15,
    storageGb: 11.5,
    maxStorageGb: 30,
    planName: "Empresarial",
  },
  {
    id: "3",
    name: "Comercializadora Textil Lima",
    slug: "textil-lima",
    domain: "textil.erp.sofiaerp.com",
    status: "PAST_DUE",
    activeUsers: 3,
    maxUsers: 5,
    storageGb: 2.1,
    maxStorageGb: 10,
    planName: "Básico",
  },
];

type ActiveTab = "overview" | "domains" | "billing";

export default function CustomerPortalPage() {
  const [tenants] = useState<TenantSummary[]>(INITIAL_TENANTS);
  const [selectedTenant, setSelectedTenant] = useState<TenantSummary>(INITIAL_TENANTS[0]);
  const [currentTab, setCurrentTab] = useState<ActiveTab>("overview");

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Barra de Navegación Superior */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-600 flex items-center justify-center text-white font-bold tracking-tight shadow-sm">
              S
            </div>
            <div>
              <span className="font-bold text-slate-900 tracking-tight text-base">SOFIA Platform</span>
              <span className="text-[11px] text-slate-500 block -mt-0.5">Portal Central de Acceso SaaS</span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Plataforma Operativa (Odoo 20 + SUNAT UBL 2.1)</span>
            </div>
            <button className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 transition">
              <Settings className="w-4 h-4" /> Configuración
            </button>
            <button className="flex items-center gap-1.5 text-rose-600 hover:text-rose-700 transition">
              <LogOut className="w-4 h-4" /> Salir
            </button>
          </div>
        </div>
      </header>

      {/* Contenido Principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Mis Empresas & Suscripciones</h1>
          <p className="text-sm text-slate-500 mt-1">
            Selecciona la empresa con la que deseas operar hoy o administra sus capacidades, dominios y facturación comercial.
          </p>
        </div>

        {/* Selector de Empresas */}
        <TenantSelector
          tenants={tenants}
          onSelectTenant={(t) => setSelectedTenant(t)}
          selectedTenantId={selectedTenant.id}
        />

        {/* Pestañas de Navegación del Tenant Seleccionado */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setCurrentTab("overview")}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              currentTab === "overview"
                ? "bg-sky-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-200/60"
            }`}
          >
            <Activity className="w-4 h-4" /> Resumen de Suscripción & Recursos
          </button>
          <button
            onClick={() => setCurrentTab("domains")}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              currentTab === "domains"
                ? "bg-sky-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-200/60"
            }`}
          >
            <Globe className="w-4 h-4" /> Dominios & SSL (ACME)
          </button>
          <button
            onClick={() => setCurrentTab("billing")}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              currentTab === "billing"
                ? "bg-sky-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-200/60"
            }`}
          >
            <CreditCard className="w-4 h-4" /> Facturación & Comprobantes
          </button>
        </div>

        {/* Contenido según la pestaña activa */}
        {currentTab === "overview" && <SubscriptionOverview tenant={selectedTenant} />}
        {currentTab === "domains" && <DomainManager tenant={selectedTenant} />}
        {currentTab === "billing" && <BillingInvoices tenant={selectedTenant} />}
      </main>

      <footer className="border-t border-slate-200 py-4 bg-white text-center text-xs text-slate-400">
        SOFIA ERP SaaS Multi-Tenant Platform — Operando conforme a normativas SUNAT Perú y Odoo Community 20.
      </footer>
    </div>
  );
}
