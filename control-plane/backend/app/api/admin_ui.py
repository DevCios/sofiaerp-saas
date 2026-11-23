"""
Interfaz Gráfica Web para Administración de Clientes y Tenants de SOFIA Platform.
Permite visualizar, registrar y gestionar empresas cliente mediante interfaz web intuitiva sin comandos de terminal.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

admin_ui_router = APIRouter()

HTML_CONTENT = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOFIA ERP SaaS — Panel de Control de Clientes</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">

  <!-- Header -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
          S
        </div>
        <div>
          <span class="font-bold text-slate-900 text-lg">SOFIA Platform</span>
          <span class="text-xs text-slate-500 block -mt-0.5">Control Plane Multi-Tenant • Odoo 20 + SUNAT</span>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <a href="/api/docs" target="_blank" class="text-xs text-slate-600 hover:text-indigo-600 border border-slate-200 px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5">
          <i class="fa-solid fa-code"></i> API Docs
        </a>
        <div class="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Sistema Operativo
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

    <!-- Top Banner & Button -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Gestión de Clientes & Empresas</h1>
        <p class="text-sm text-slate-500 mt-1">Crea nuevas instancias ERP para tus clientes en 2 segundos con base de datos aislada y localización fiscal.</p>
      </div>
      <button onclick="openModal()" class="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm px-5 py-2.5 rounded-xl transition shadow-sm shadow-indigo-200">
        <i class="fa-solid fa-plus"></i> Crear Nuevo Cliente
      </button>
    </div>

    <!-- Metrics Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
      <div class="bg-white p-5 rounded-2xl border border-slate-200">
        <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Total de Clientes</div>
        <div id="metric-tenants" class="text-3xl font-bold text-slate-900 mt-2">--</div>
        <div class="text-xs text-emerald-600 font-medium mt-1 flex items-center gap-1"><i class="fa-solid fa-circle-check"></i> Base de datos por tenant</div>
      </div>
      <div class="bg-white p-5 rounded-2xl border border-slate-200">
        <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Motor Runtime</div>
        <div class="text-3xl font-bold text-slate-900 mt-2">Odoo 20</div>
        <div class="text-xs text-indigo-600 font-medium mt-1 flex items-center gap-1"><i class="fa-solid fa-flag"></i> Español (Perú) Nativo</div>
      </div>
      <div class="bg-white p-5 rounded-2xl border border-slate-200">
        <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Seguridad Perimetral</div>
        <div class="text-3xl font-bold text-emerald-600 mt-2">Blindado</div>
        <div class="text-xs text-slate-500 font-medium mt-1">Nginx + PgBouncer Tx Mode</div>
      </div>
    </div>

    <!-- Tenants Table -->
    <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
      <div class="p-5 border-b border-slate-100 flex items-center justify-between">
        <h2 class="text-base font-bold text-slate-900">Empresas Registradas</h2>
        <button onclick="loadTenants()" class="text-xs text-slate-500 hover:text-indigo-600 flex items-center gap-1 font-medium transition">
          <i class="fa-solid fa-rotate-right"></i> Actualizar
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
            <tr>
              <th class="px-6 py-3.5">Empresa / Razón Social</th>
              <th class="px-6 py-3.5">Subdominio & Acceso</th>
              <th class="px-6 py-3.5">Base de Datos</th>
              <th class="px-6 py-3.5">Estado</th>
              <th class="px-6 py-3.5">Fecha Alta</th>
              <th class="px-6 py-3.5 text-right">Acción</th>
            </tr>
          </thead>
          <tbody id="tenants-body" class="divide-y divide-slate-100">
            <tr>
              <td colspan="6" class="px-6 py-10 text-center text-slate-400">
                <i class="fa-solid fa-spinner fa-spin text-indigo-600 text-xl mb-2 block"></i>
                Cargando empresas cliente...
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </main>

  <!-- Modal: Crear Nuevo Cliente -->
  <div id="modal-new-tenant" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 transform transition-all">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h3 class="text-lg font-bold text-slate-900">Registrar Nuevo Cliente</h3>
          <p class="text-xs text-slate-500 mt-0.5">Se creará su base de datos y subdominio de forma automática.</p>
        </div>
        <button onclick="closeModal()" class="text-slate-400 hover:text-slate-600 text-lg w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-100 transition">&times;</button>
      </div>

      <form id="form-new-tenant" onsubmit="handleCreateTenant(event)" class="space-y-4 mt-5">
        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Razón Social / Nombre Comercial *</label>
          <input type="text" id="t-name" required placeholder="Ej: Avantgarde S.A.C." class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Subdominio (Slug de Acceso) *</label>
          <div class="flex items-center rounded-xl border border-slate-200 overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-600 transition">
            <input type="text" id="t-slug" required placeholder="avantgarde" onkeyup="sanitizeSlug(this)" class="flex-1 px-3.5 py-2.5 text-sm outline-hidden border-none">
            <span class="bg-slate-100 px-3 py-2.5 text-xs text-slate-500 font-medium border-l border-slate-200">.sofiaerp.com</span>
          </div>
          <p class="text-[11px] text-slate-400 mt-1">Solo letras minúsculas, números y guiones.</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Correo Electrónico del Administrador *</label>
          <input type="email" id="t-email" required placeholder="admin@empresa.pe" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Contraseña Inicial de Acceso *</label>
          <input type="password" id="t-pass" required placeholder="Mínimo 8 caracteres" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Plan Comercial</label>
          <select id="t-plan" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
            <option value="SOFIA-ERP-PRO">SOFIA ERP Profesional (Odoo 20 + SUNAT UBL 2.1)</option>
            <option value="SOFIA-ERP-ENTERPRISE">SOFIA ERP Enterprise (Multiproducto Completo)</option>
            <option value="SOFIA-ERP-BASIC">SOFIA ERP Básico</option>
          </select>
        </div>

        <div id="modal-error" class="hidden p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700"></div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
          <button type="button" onclick="closeModal()" class="px-4 py-2.5 rounded-xl text-slate-600 text-sm font-medium hover:bg-slate-100 transition">Cancelar</button>
          <button type="submit" id="btn-submit" class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition shadow-sm flex items-center gap-2">
            <span>Crear y Desplegar Cliente</span>
          </button>
        </div>
      </form>
    </div>
  </div>

  <script>
    function sanitizeSlug(input) {
      input.value = input.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
    }

    function openModal() {
      document.getElementById('modal-new-tenant').classList.remove('hidden');
      document.getElementById('modal-error').classList.add('hidden');
      document.getElementById('form-new-tenant').reset();
    }

    function closeModal() {
      document.getElementById('modal-new-tenant').classList.add('hidden');
    }

    async function loadTenants() {
      const tbody = document.getElementById('tenants-body');
      try {
        const res = await fetch('/api/v1/tenants');
        const tenants = await res.json();
        
        document.getElementById('metric-tenants').innerText = tenants.length;

        if (tenants.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="6" class="px-6 py-12 text-center text-slate-400">
                <i class="fa-regular fa-folder-open text-3xl mb-2 text-slate-300 block"></i>
                No hay empresas clientes registradas aún. Haz clic en "Crear Nuevo Cliente" arriba.
              </td>
            </tr>
          `;
          return;
        }

        tbody.innerHTML = tenants.map(t => {
          const domainUrl = 'http://' + t.slug + '.sofiaerp.com';
          const isLive = t.status === 'ACTIVE' || t.status === 'PROVISIONING';
          const badgeClass = t.status === 'ACTIVE' 
            ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
            : 'bg-amber-50 text-amber-700 border-amber-200';
          const statusText = t.status === 'ACTIVE' ? 'Activo' : 'Aprovisionando';

          return `
            <tr class="hover:bg-slate-50/70 transition">
              <td class="px-6 py-4 font-semibold text-slate-900">${t.name}</td>
              <td class="px-6 py-4">
                <a href="${domainUrl}" target="_blank" class="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-medium">
                  ${t.slug}.sofiaerp.com <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
              </td>
              <td class="px-6 py-4 font-mono text-xs text-slate-500">${t.database_name}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${badgeClass}">
                  <span class="w-1.5 h-1.5 rounded-full ${t.status === 'ACTIVE' ? 'bg-emerald-500' : 'bg-amber-500'}"></span>
                  ${statusText}
                </span>
              </td>
              <td class="px-6 py-4 text-xs text-slate-500">${new Date(t.created_at).toLocaleDateString()}</td>
              <td class="px-6 py-4 text-right">
                <a href="${domainUrl}" target="_blank" class="inline-flex items-center gap-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg transition">
                  Abrir ERP <i class="fa-solid fa-chevron-right text-[9px]"></i>
                </a>
              </td>
            </tr>
          `;
        }).join('');

      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-rose-500">Error al cargar clientes: ${err.message}</td></tr>`;
      }
    }

    async function handleCreateTenant(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-submit');
      const errBox = document.getElementById('modal-error');
      
      const payload = {
        name: document.getElementById('t-name').value.trim(),
        slug: document.getElementById('t-slug').value.trim(),
        admin_email: document.getElementById('t-email').value.trim(),
        admin_password: document.getElementById('t-pass').value.trim(),
        plan_code: document.getElementById('t-plan').value,
      };

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Desplegando instancia...`;
      errBox.classList.add('hidden');

      try {
        const res = await fetch('/api/v1/tenants', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error al aprovisionar tenant');
        }

        closeModal();
        loadTenants();
      } catch (err) {
        errBox.innerText = err.message;
        errBox.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Crear y Desplegar Cliente</span>`;
      }
    }

    document.addEventListener('DOMContentLoaded', loadTenants);
  </script>
</body>
</html>
"""

@admin_ui_router.get("/admin", response_class=HTMLResponse, summary="Panel Gráfico de Administración SaaS")
async def get_admin_dashboard():
    """Retorna la interfaz web interactiva para administración de clientes."""
    return HTML_CONTENT
