"""
Interfaz Gráfica Web para Administración de Clientes y Tenants de SOFIA Platform.
Incluye Pantalla de Login de Superadministrador con autenticación JWT y Argon2id.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

admin_ui_router = APIRouter()

HTML_CONTENT = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOFIA ERP SaaS — Control Plane de Administración</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">

  <!-- ========================================================================= -->
  <!-- VISTA 1: PANTALLA DE LOGIN SEGURO DE SUPERADMINISTRADOR                     -->
  <!-- ========================================================================= -->
  <div id="view-login" class="flex-1 flex items-center justify-center p-4">
    <div class="bg-white rounded-3xl max-w-md w-full p-8 shadow-xl border border-slate-200">
      
      <!-- Logo y Encabezado -->
      <div class="text-center mb-8">
        <div class="w-14 h-14 rounded-2xl bg-indigo-600 text-white font-bold text-2xl flex items-center justify-center mx-auto shadow-md shadow-indigo-200">
          S
        </div>
        <h1 class="text-xl font-bold text-slate-900 mt-4">Acceso de Superadministrador</h1>
        <p class="text-xs text-slate-500 mt-1">SOFIA ERP SaaS Platform Control Plane</p>
      </div>

      <!-- Formulario de Login -->
      <form id="form-login" onsubmit="handleLogin(event)" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Correo Electrónico</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400">
              <i class="fa-solid fa-envelope text-xs"></i>
            </span>
            <input type="email" id="login-email" required value="admin@sofiaerp.com" placeholder="admin@sofiaerp.com" class="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Contraseña</label>
          <div class="relative">
            <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400">
              <i class="fa-solid fa-lock text-xs"></i>
            </span>
            <input type="password" id="login-pass" required placeholder="••••••••" class="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
          </div>
        </div>

        <div id="login-error" class="hidden p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700"></div>

        <button type="submit" id="btn-login" class="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl transition shadow-sm shadow-indigo-200 flex items-center justify-center gap-2">
          <span>Ingresar al Panel de Control</span>
          <i class="fa-solid fa-arrow-right text-xs"></i>
        </button>
      </form>

      <div class="mt-6 text-center">
        <span class="text-[11px] text-slate-400 flex items-center justify-center gap-1.5">
          <i class="fa-solid fa-shield-halved text-emerald-500"></i> Cifrado Argon2id & RS256 JWT
        </span>
      </div>

    </div>
  </div>


  <!-- ========================================================================= -->
  <!-- VISTA 2: PANEL DE ADMINISTRACIÓN (PROTEGIDO)                              -->
  <!-- ========================================================================= -->
  <div id="view-dashboard" class="flex-1 flex flex-col hidden">
    
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
          <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-800">
            <i class="fa-solid fa-user-shield text-indigo-600"></i>
            <span id="user-display">Superadmin</span>
          </div>
          <button onclick="handleLogout()" class="text-xs text-rose-600 hover:text-rose-700 border border-rose-200 hover:bg-rose-50 px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5">
            <i class="fa-solid fa-arrow-right-from-bracket"></i> Cerrar Sesión
          </button>
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
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200">
          <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Total Empresas</div>
          <div id="metric-tenants" class="text-3xl font-bold text-slate-900 mt-2">--</div>
          <div class="text-xs text-slate-500 font-medium mt-1">Registradas en plataforma</div>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200">
          <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Instancias Activas</div>
          <div id="metric-active" class="text-3xl font-bold text-emerald-600 mt-2">--</div>
          <div class="text-xs text-emerald-600 font-medium mt-1 flex items-center gap-1"><i class="fa-solid fa-circle-check"></i> En servicio normal</div>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200">
          <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Suspendidas por Pago</div>
          <div id="metric-suspended" class="text-3xl font-bold text-rose-600 mt-2">--</div>
          <div class="text-xs text-rose-600 font-medium mt-1 flex items-center gap-1"><i class="fa-solid fa-ban"></i> Acceso cortado</div>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200">
          <div class="text-slate-500 text-xs font-semibold uppercase tracking-wider">Aislamiento Físico</div>
          <div class="text-3xl font-bold text-indigo-600 mt-2">100%</div>
          <div class="text-xs text-slate-500 font-medium mt-1">Database-per-tenant</div>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto">
        <button onclick="switchTab('tenants')" id="tab-btn-tenants" class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-indigo-600 text-white shadow-xs">
          <i class="fa-solid fa-building"></i> Empresas & Instancias
        </button>
        <button onclick="switchTab('announcements')" id="tab-btn-announcements" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition flex items-center gap-2">
          <i class="fa-solid fa-bullhorn text-amber-500"></i> Comunicados Globales
        </button>
        <button onclick="switchTab('audit')" id="tab-btn-audit" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition flex items-center gap-2">
          <i class="fa-solid fa-shield-halved text-emerald-600"></i> Auditoría & Seguridad
        </button>
      </div>

      <!-- SECCIÓN 1: TENANTS & EMPRESAS -->
      <div id="section-tenants" class="space-y-6">
        <!-- Tenants Table -->
        <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
          <div class="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 class="text-base font-bold text-slate-900">Empresas Registradas</h2>
              <p class="text-xs text-slate-500 mt-0.5">Control de vencimientos, estado de pago, respaldos y corte automático de servicio.</p>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="evaluateSubscriptions()" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 transition flex items-center gap-1.5 shadow-2xs" title="Verificar fechas y suspender automáticamente a clientes con más de 3 días de mora">
                <i class="fa-solid fa-bolt text-amber-600"></i> Chequeo de Pagos
              </button>
              <button onclick="loadTenants()" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 transition flex items-center gap-1">
                <i class="fa-solid fa-rotate-right"></i> Actualizar
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
                <tr>
                  <th class="px-5 py-3.5">Empresa / Razón Social</th>
                  <th class="px-5 py-3.5">Subdominio & Acceso</th>
                  <th class="px-5 py-3.5">Plan & Ciclo</th>
                  <th class="px-5 py-3.5">Estado Pago / Vigencia</th>
                  <th class="px-5 py-3.5">Acceso ERP</th>
                  <th class="px-5 py-3.5 text-right">Acciones</th>
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
      </div>

      <!-- SECCIÓN 2: COMUNICADOS GLOBALES -->
      <div id="section-announcements" class="hidden space-y-5">
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 class="text-xl font-bold text-slate-900 tracking-tight">Comunicados Globales & Banners</h2>
            <p class="text-xs text-slate-500 mt-1">Publica mensajes urgentes, avisos de mantenimiento de SUNAT o promociones para todas las empresas.</p>
          </div>
          <button onclick="openAnnouncementModal()" class="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs transition shadow-xs flex items-center gap-2">
            <i class="fa-solid fa-bullhorn"></i> Publicar Nuevo Comunicado
          </button>
        </div>

        <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs p-5">
          <h3 class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-4">Avisos Activos Actualmente</h3>
          <div id="announcements-container" class="space-y-3">
            <div class="text-center py-8 text-xs text-slate-400">Cargando comunicados...</div>
          </div>
        </div>
      </div>

      <!-- SECCIÓN 3: AUDITORÍA & SEGURIDAD -->
      <div id="section-audit" class="hidden space-y-5">
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 class="text-xl font-bold text-slate-900 tracking-tight">Auditoría & Logs de Seguridad</h2>
            <p class="text-xs text-slate-500 mt-1">Historial inmutable de operaciones, altas, suspensiones, accesos de soporte y direcciones IP.</p>
          </div>
          <button onclick="loadAuditLogs()" class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 font-semibold text-xs transition flex items-center gap-1.5">
            <i class="fa-solid fa-rotate-right"></i> Actualizar Logs
          </button>
        </div>

        <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
                <tr>
                  <th class="px-5 py-3.5">Acción Realizada</th>
                  <th class="px-5 py-3.5">Empresa / Tenant</th>
                  <th class="px-5 py-3.5">Dirección IP</th>
                  <th class="px-5 py-3.5">Fecha & Hora</th>
                  <th class="px-5 py-3.5">Detalles</th>
                </tr>
              </thead>
              <tbody id="audit-logs-body" class="divide-y divide-slate-100 font-mono text-xs">
                <tr>
                  <td colspan="5" class="px-6 py-10 text-center text-slate-400 font-sans">
                    <i class="fa-solid fa-spinner fa-spin text-indigo-600 text-xl mb-2 block"></i>
                    Cargando eventos de seguridad...
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </main>

  </div>


  <!-- ========================================================================= -->
  <!-- MODAL: CREAR NUEVO CLIENTE                                                -->
  <!-- ========================================================================= -->
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
            <option value="SOFIA-ERP-PRO">SOFIA ERP Pyme Pro (S/ 14.90 / mes)</option>
            <option value="SOFIA-ERP-EMPRENDEDOR">SOFIA ERP Emprendedor (S/ 9.90 / mes)</option>
            <option value="SOFIA-ERP-CORPORATIVO">SOFIA ERP Corporativo (S/ 19.90 / mes)</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Ciclo de Facturación & Vigencia</label>
          <select id="t-cycle" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition">
            <option value="MONTHLY">Mensual (Vigencia inicial: 30 días)</option>
            <option value="ANNUAL">Anual (Vigencia inicial: 365 días)</option>
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


  <!-- ========================================================================= -->
  <!-- MODAL: GESTIÓN DE DOMINIOS PERSONALIZADOS                                 -->
  <!-- ========================================================================= -->
  <div id="modal-domains" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 transform transition-all max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-globe text-indigo-600"></i> Dominios Propios (White-Label)
          </h3>
          <p id="domains-tenant-title" class="text-xs text-slate-500 mt-0.5">Empresa: --</p>
        </div>
        <button onclick="closeDomainsModal()" class="text-slate-400 hover:text-slate-600 text-lg w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-100 transition">&times;</button>
      </div>

      <div class="mt-5 space-y-5">
        <!-- Formulario para Agregar Dominio -->
        <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">Vincular Nuevo Dominio</label>
          <div class="flex gap-2">
            <input type="text" id="input-new-domain" placeholder="ej: www.constructora.pe o erp.empresa.com" class="flex-1 px-3.5 py-2 text-sm bg-white rounded-xl border border-slate-200 outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600">
            <button onclick="handleRegisterDomain()" id="btn-add-domain" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 shadow-xs whitespace-nowrap">
              <i class="fa-solid fa-key"></i> Generar Token DNS
            </button>
          </div>
          <p class="text-[11px] text-slate-500 mt-1.5">Al registrar el dominio, el sistema generará automáticamente el token TXT que el cliente debe colocar en su proveedor de dominio.</p>
        </div>

        <!-- Lista de Dominios Registrados -->
        <div>
          <h4 class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Dominios Configurados</h4>
          <div id="domains-list-container" class="space-y-3">
            <div class="text-center py-6 text-xs text-slate-400">Cargando dominios...</div>
          </div>
        </div>
      </div>
    </div>
  </div>


  <!-- ========================================================================= -->
  <!-- MODAL: CENTRO DE RESPALDOS (BACKUPS)                                      -->
  <!-- ========================================================================= -->
  <div id="modal-backups" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 transform transition-all max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-database text-purple-600"></i> Respaldos de Base de Datos
          </h3>
          <p id="backups-tenant-title" class="text-xs text-slate-500 mt-0.5">Empresa: --</p>
        </div>
        <button onclick="closeBackupsModal()" class="text-slate-400 hover:text-slate-600 text-lg w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-100 transition">&times;</button>
      </div>

      <div class="mt-5 space-y-5">
        <!-- Tarjeta de Consumo Real y Generación Inmediata -->
        <div class="bg-purple-50/60 p-4 rounded-xl border border-purple-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div class="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">Espacio Ocupado en Disco</div>
            <div id="backups-db-size" class="text-lg font-bold text-purple-900 mt-0.5">Calculando...</div>
            <div id="backups-filestore-size" class="text-xs text-purple-700">Filestore: --</div>
          </div>
          <button onclick="handleTriggerBackup()" id="btn-trigger-backup" class="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 shadow-xs whitespace-nowrap">
            <i class="fa-solid fa-cloud-arrow-down"></i> Crear Respaldo Ahora (.sql.gz)
          </button>
        </div>

        <!-- Lista de Respaldos Disponibles -->
        <div>
          <h4 class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Copias de Seguridad Disponibles para Descarga</h4>
          <div id="backups-list-container" class="space-y-2.5">
            <div class="text-center py-6 text-xs text-slate-400">Cargando respaldos...</div>
          </div>
        </div>
      </div>
    </div>
  </div>


  <!-- ========================================================================= -->
  <!-- MODAL: CREAR COMUNICADO GLOBAL                                             -->
  <!-- ========================================================================= -->
  <div id="modal-announcement" class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 transform transition-all">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-bullhorn text-amber-500"></i> Publicar Comunicado Global
          </h3>
          <p class="text-xs text-slate-500 mt-0.5">Este mensaje será visible en los ERPs de todas las empresas clientes.</p>
        </div>
        <button onclick="closeAnnouncementModal()" class="text-slate-400 hover:text-slate-600 text-lg w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-100 transition">&times;</button>
      </div>

      <form id="form-announcement" onsubmit="handleCreateAnnouncement(event)" class="space-y-4 mt-5">
        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Título del Comunicado *</label>
          <input type="text" id="ann-title" required placeholder="Ej: Mantenimiento Programado de SUNAT" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 outline-hidden">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Nivel de Aviso *</label>
          <select id="ann-level" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 outline-hidden">
            <option value="INFO">Informativo (Azul / Neutral)</option>
            <option value="WARNING">Advertencia / Alerta (Amarillo)</option>
            <option value="MAINTENANCE">Mantenimiento de Servidores (Rojo)</option>
            <option value="PROMO">Novedad / Promoción (Verde)</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">Mensaje Detallado *</label>
          <textarea id="ann-message" required rows="3" placeholder="Describe el comunicado para tus clientes..." class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 outline-hidden"></textarea>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
          <button type="button" onclick="closeAnnouncementModal()" class="px-4 py-2.5 rounded-xl text-slate-600 text-sm font-medium hover:bg-slate-100 transition">Cancelar</button>
          <button type="submit" id="btn-submit-ann" class="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition shadow-xs flex items-center gap-2">
            <span>Publicar Comunicado</span>
          </button>
        </div>
      </form>
    </div>
  </div>


  <!-- ========================================================================= -->
  <!-- JAVASCRIPT DE AUTENTICACIÓN Y GESTIÓN                                      -->
  <!-- ========================================================================= -->
  <script>
    const TOKEN_KEY = 'sofia_admin_token';
    const EMAIL_KEY = 'sofia_admin_email';

    function checkAuth() {
      const token = sessionStorage.getItem(TOKEN_KEY);
      const email = sessionStorage.getItem(EMAIL_KEY);

      if (!token) {
        document.getElementById('view-login').classList.remove('hidden');
        document.getElementById('view-dashboard').classList.add('hidden');
      } else {
        document.getElementById('view-login').classList.add('hidden');
        document.getElementById('view-dashboard').classList.remove('hidden');
        document.getElementById('user-display').innerText = email || 'Superadmin';
        loadTenants();
      }
    }

    async function handleLogin(e) {
      if (e) e.preventDefault();
      const btn = document.getElementById('btn-login');
      const errBox = document.getElementById('login-error');
      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-pass').value.trim();

      if (!email || !password) {
        errBox.innerText = 'Por favor ingresa tu correo y contraseña.';
        errBox.classList.remove('hidden');
        return;
      }

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Autenticando...`;
      errBox.classList.add('hidden');

      try {
        const res = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Credenciales incorrectas');
        }

        if (!data.access_token) {
          throw new Error('Respuesta de autenticación inválida');
        }

        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        sessionStorage.setItem(EMAIL_KEY, email);

        // Transición inmediata a dashboard
        document.getElementById('view-login').classList.add('hidden');
        document.getElementById('view-dashboard').classList.remove('hidden');
        const userDisp = document.getElementById('user-display');
        if (userDisp) userDisp.innerText = email;
        loadTenants();
      } catch (err) {
        errBox.innerText = err.message || 'Error de conexión';
        errBox.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Ingresar al Panel de Control</span> <i class="fa-solid fa-arrow-right text-xs"></i>`;
      }
    }

    function handleLogout() {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(EMAIL_KEY);
      checkAuth();
    }

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
      const token = sessionStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch('/api/v1/tenants', {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.status === 401) {
          tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-rose-500 font-semibold">Sesión expirada. Por favor cierra sesión y vuelve a ingresar.</td></tr>';
          return;
        }

        const tenants = await res.json();
        const activeCount = tenants.filter(t => t.status === 'ACTIVE').length;
        const suspendedCount = tenants.filter(t => t.status === 'SUSPENDED').length;
        document.getElementById('metric-tenants').innerText = tenants.length;
        document.getElementById('metric-active').innerText = activeCount;
        document.getElementById('metric-suspended').innerText = suspendedCount;

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
          const domainUrl = 'https://' + t.slug + '.sofiaerp.com';
          let accessBadgeClass = 'bg-slate-50 text-slate-700 border-slate-200';
          let accessDotClass = 'bg-slate-400';
          let accessText = t.status;

          if (t.status === 'ACTIVE') {
            accessBadgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
            accessDotClass = 'bg-emerald-500';
            accessText = 'Activo';
          } else if (t.status === 'SUSPENDED') {
            accessBadgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
            accessDotClass = 'bg-rose-500';
            accessText = 'Suspendido';
          } else if (t.status === 'PROVISIONING') {
            accessBadgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
            accessDotClass = 'bg-amber-500 animate-pulse';
            accessText = 'Aprovisionando';
          } else if (t.status === 'ARCHIVED') {
            accessBadgeClass = 'bg-slate-100 text-slate-600 border-slate-300';
            accessDotClass = 'bg-slate-400';
            accessText = 'Archivado';
          }

          // Cálculo de vigencia de pago y fecha de vencimiento
          let paymentBadge = '';
          let expiresDateStr = '30 días de vigencia';
          if (t.subscription_expires_at) {
            const expDate = new Date(t.subscription_expires_at);
            const now = new Date();
            const diffDays = Math.ceil((expDate - now) / (1000 * 60 * 60 * 24));
            expiresDateStr = expDate.toLocaleDateString();

            if (diffDays > 5) {
              paymentBadge = `
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <i class="fa-solid fa-circle-check text-[10px]"></i> Al Día (${diffDays}d)
                </span>
              `;
            } else if (diffDays >= 0) {
              paymentBadge = `
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
                  <i class="fa-solid fa-clock text-[10px]"></i> Vence en ${diffDays}d
                </span>
              `;
            } else {
              paymentBadge = `
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                  <i class="fa-solid fa-triangle-exclamation text-[10px]"></i> Vencido (${Math.abs(diffDays)}d mora)
                </span>
              `;
            }
          } else {
            paymentBadge = `
              <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <i class="fa-solid fa-circle-check text-[10px]"></i> Al Día
              </span>
            `;
          }

          // Botones de Acción
          const domainBtn = `
            <button onclick="openDomainsModal('${t.id}', '${t.name}', '${t.slug}')" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition" title="Configurar dominios propios (www.empresa.com)">
              <i class="fa-solid fa-globe text-[10px]"></i> Dominios
            </button>
          `;

          const backupBtn = `
            <button onclick="openBackupsModal('${t.id}', '${t.name}', '${t.slug}')" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 transition" title="Respaldos en 1 clic y descargas .sql.gz">
              <i class="fa-solid fa-database text-[10px]"></i> Backup
            </button>
          `;

          const supportBtn = `
            <button onclick="handleSupportAccess('${t.id}', '${t.name}', '${t.slug}')" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 transition" title="Acceso de Superadmin sin contraseña">
              <i class="fa-solid fa-bolt text-[10px]"></i> Soporte
            </button>
          `;

          let actionButtons = '';
          if (t.status === 'ACTIVE') {
            actionButtons = `
              <button onclick="toggleTenantStatus('${t.id}', 'SUSPENDED', '${t.name}')" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 transition" title="Cortar acceso por falta de pago">
                <i class="fa-solid fa-ban text-[10px]"></i> Suspender
              </button>
              <button onclick="renewTenant('${t.id}', '${t.name}', 30)" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition" title="Renovar +30 días por abono mensual recibido">
                <i class="fa-solid fa-plus text-[10px]"></i> +30d
              </button>
            `;
          } else if (t.status === 'SUSPENDED') {
            actionButtons = `
              <button onclick="renewTenant('${t.id}', '${t.name}', 30)" class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition" title="Reactivar servicio y extender vigencia 30 días">
                <i class="fa-solid fa-play text-[10px]"></i> Reactivar (+30d)
              </button>
            `;
          }

          const cycleLabel = t.billing_cycle === 'ANNUAL' ? 'Anual' : 'Mensual';
          const planDisplay = (t.plan_code || 'PRO').replace('SOFIA-ERP-', '');

          return `
            <tr class="hover:bg-slate-50/70 transition">
              <td class="px-5 py-4 font-semibold text-slate-900">${t.name}</td>
              <td class="px-5 py-4">
                <a href="${domainUrl}" target="_blank" class="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-medium">
                  ${t.slug}.sofiaerp.com <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                </a>
              </td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  ${planDisplay} · ${cycleLabel}
                </span>
              </td>
              <td class="px-5 py-4">
                ${paymentBadge}
                <div class="text-[11px] text-slate-400 mt-1 font-mono">Vence: ${expiresDateStr}</div>
              </td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${accessBadgeClass}">
                  <span class="w-1.5 h-1.5 rounded-full ${accessDotClass}"></span>
                  ${accessText}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                <div class="inline-flex items-center justify-end gap-1.5">
                  ${domainBtn}
                  ${backupBtn}
                  ${supportBtn}
                  ${actionButtons}
                  <a href="${domainUrl}" target="_blank" class="inline-flex items-center gap-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition">
                    Abrir ERP <i class="fa-solid fa-chevron-right text-[9px]"></i>
                  </a>
                </div>
              </td>
            </tr>
          `;
        }).join('');

      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-rose-500">Error al cargar clientes: ${err.message}</td></tr>`;
      }
    }

    async function toggleTenantStatus(tenantId, newStatus, tenantName) {
      const isSuspending = newStatus === 'SUSPENDED';
      const confirmPrompt = isSuspending 
        ? `⚠️ ATENCIÓN: ¿Deseas suspender el acceso de "${tenantName}" por falta de pago?\n\n• El cliente no podrá ingresar al sistema.\n• La base de datos y sus comprobantes permanecerán intactos.\n• Podrás reactivarlo en cualquier momento tras verificar el abono.`
        : `✅ ¿Deseas reactivar el acceso de "${tenantName}" a su ERP?`;

      if (!confirm(confirmPrompt)) return;

      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/status`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            status: newStatus,
            reason: isSuspending ? 'Suspensión manual por falta de pago' : 'Reactivación por pago verificado'
          })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error al actualizar estado del tenant');
        }

        loadTenants();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async function renewTenant(tenantId, tenantName, days = 30) {
      const confirmPrompt = `💳 Confirmar pago y extender suscripción:\n\n¿Registrar abono de "${tenantName}" y extender su vigencia por +${days} días?`;
      if (!confirm(confirmPrompt)) return;

      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/status`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            status: 'ACTIVE',
            extend_days: days,
            reason: `Renovación de suscripción (+${days} días) por pago registrado.`
          })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al renovar suscripción');

        loadTenants();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async function evaluateSubscriptions() {
      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch('/api/v1/tenants/evaluate-subscriptions', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al evaluar suscripciones');
        alert(`⚡ Chequeo de pagos completado:\n• Empresas evaluadas: ${data.checked_total}\n• Suspendidas automáticamente por mora (>3 días): ${data.suspended_count}\n• Por vencer pronto: ${data.due_soon_count}`);
        loadTenants();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async function handleCreateTenant(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-submit');
      const errBox = document.getElementById('modal-error');
      const token = sessionStorage.getItem(TOKEN_KEY);
      
      const payload = {
        name: document.getElementById('t-name').value.trim(),
        slug: document.getElementById('t-slug').value.trim(),
        admin_email: document.getElementById('t-email').value.trim(),
        admin_password: document.getElementById('t-pass').value.trim(),
        plan_code: document.getElementById('t-plan').value,
        billing_cycle: document.getElementById('t-cycle') ? document.getElementById('t-cycle').value : 'MONTHLY',
      };

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Desplegando instancia...`;
      errBox.classList.add('hidden');

      try {
        const res = await fetch('/api/v1/tenants', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
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

    // =========================================================================
    // GESTIÓN DE DOMINIOS PROPIOS (WHITE-LABEL)
    // =========================================================================
    let currentDomainsTenantId = null;
    let currentDomainsTenantName = '';

    function openDomainsModal(tenantId, tenantName, tenantSlug) {
      currentDomainsTenantId = tenantId;
      currentDomainsTenantName = tenantName;
      document.getElementById('domains-tenant-title').innerText = `Empresa: ${tenantName} (${tenantSlug}.sofiaerp.com)`;
      document.getElementById('input-new-domain').value = '';
      document.getElementById('modal-domains').classList.remove('hidden');
      loadTenantDomains(tenantId);
    }

    function closeDomainsModal() {
      document.getElementById('modal-domains').classList.add('hidden');
      currentDomainsTenantId = null;
    }

    async function loadTenantDomains(tenantId) {
      const container = document.getElementById('domains-list-container');
      container.innerHTML = '<div class="text-center py-6 text-xs text-slate-400"><i class="fa-solid fa-spinner fa-spin text-indigo-600 mr-2"></i> Consultando dominios...</div>';
      const token = sessionStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/domains`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const domains = await res.json();

        if (!domains || domains.length === 0) {
          container.innerHTML = `
            <div class="text-center py-6 text-slate-400 text-xs bg-slate-50 rounded-xl border border-dashed border-slate-200">
              Esta empresa aún no tiene dominios propios vinculados. Puedes registrar uno arriba (ej: www.constructora.pe).
            </div>
          `;
          return;
        }

        container.innerHTML = domains.map(d => {
          const isVerified = d.status === 'VERIFIED' || d.status === 'SSL_ACTIVE';
          const statusBadge = isVerified 
            ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"><i class="fa-solid fa-circle-check"></i> Activo & Verificado</span>`
            : `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse"><i class="fa-solid fa-clock"></i> Esperando DNS TXT</span>`;

          const dnsInstructions = !isVerified ? `
            <div class="mt-3 p-3.5 bg-amber-50/70 rounded-xl border border-amber-200 text-xs text-slate-700 space-y-2.5">
              <div class="font-bold text-amber-900 flex items-center gap-1.5">
                <i class="fa-solid fa-key text-amber-600"></i> Registro de Verificación TXT (Copia y entrega al cliente):
              </div>
              <div class="space-y-2 font-mono text-[11px]">
                <div class="bg-white p-2.5 rounded-lg border border-amber-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div class="overflow-x-auto">
                    <span class="text-slate-500 font-sans">1. Registro TXT:</span><br/>
                    <strong>Host:</strong> _sofia-challenge.${d.domain}<br/>
                    <strong>Valor:</strong> ${d.verification_token}
                  </div>
                  <button onclick="copyToClipboard('${d.verification_token}')" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-sans text-xs font-semibold rounded-lg border border-indigo-200 transition shrink-0">
                    <i class="fa-regular fa-copy"></i> Copiar Token
                  </button>
                </div>
                <div class="bg-white p-2.5 rounded-lg border border-amber-200">
                  <span class="text-slate-500 font-sans">2. Registro A / CNAME:</span><br/>
                  <strong>Host:</strong> @ o www &nbsp;|&nbsp; <strong>Destino:</strong> IP de tu VPS
                </div>
              </div>
              <button onclick="handleVerifyDomain('${tenantId}', '${d.id}')" class="w-full mt-2 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold transition text-xs flex items-center justify-center gap-1.5 shadow-2xs">
                <i class="fa-solid fa-rotate"></i> Comprobar Registro DNS en Internet Ahora
              </button>
            </div>
          ` : `
            <div class="mt-2 text-xs text-emerald-700 flex items-center gap-1.5 font-medium">
              <i class="fa-solid fa-shield-halved"></i> Dominio activo. Listo para abrir: 
              <a href="https://${d.domain}" target="_blank" class="font-bold underline ml-1 inline-flex items-center gap-1 text-emerald-800">${d.domain} <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>
            </div>
          `;

          return `
            <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <div class="flex items-center justify-between">
                <div class="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <i class="fa-solid fa-link text-indigo-600"></i> ${d.domain}
                </div>
                ${statusBadge}
              </div>
              ${dnsInstructions}
            </div>
          `;
        }).join('');

      } catch (err) {
        container.innerHTML = `<div class="p-3 text-xs text-rose-600 bg-rose-50 rounded-xl">Error al cargar dominios: ${err.message}</div>`;
      }
    }

    async function handleRegisterDomain() {
      if (!currentDomainsTenantId) return;
      const input = document.getElementById('input-new-domain');
      const domainVal = input.value.trim().toLowerCase();
      if (!domainVal) {
        alert('Por favor escribe un dominio (ej: www.constructora.pe)');
        return;
      }

      const token = sessionStorage.getItem(TOKEN_KEY);
      const btn = document.getElementById('btn-add-domain');
      btn.disabled = true;

      try {
        const res = await fetch(`/api/v1/tenants/${currentDomainsTenantId}/domains`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ domain: domainVal, is_primary: false })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al registrar dominio');

        input.value = '';
        loadTenantDomains(currentDomainsTenantId);
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        btn.disabled = false;
      }
    }

    async function handleVerifyDomain(tenantId, domainId) {
      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/domains/${domainId}/verify`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Verificación DNS fallida');

        alert('✅ ¡Dominio verificado exitosamente!\n\nEl registro TXT fue detectado correctamente y el dominio ha quedado activo.');
        loadTenantDomains(tenantId);
      } catch (err) {
        alert('❌ ' + err.message);
      }
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text);
      alert('Token copiado al portapapeles: ' + text);
    }

    // =========================================================================
    // NAVEGACIÓN POR PESTAÑAS (TABS)
    // =========================================================================
    function switchTab(tabName) {
      const tabs = ['tenants', 'announcements', 'audit'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const sec = document.getElementById(`section-${t}`);
        if (t === tabName) {
          btn.className = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-indigo-600 text-white shadow-xs';
          sec.classList.remove('hidden');
        } else {
          btn.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition flex items-center gap-2';
          sec.classList.add('hidden');
        }
      });

      if (tabName === 'tenants') loadTenants();
      if (tabName === 'announcements') loadAnnouncements();
      if (tabName === 'audit') loadAuditLogs();
    }

    // =========================================================================
    // CENTRO DE RESPALDOS (BACKUPS) Y MÉTRICAS
    // =========================================================================
    let currentBackupsTenantId = null;
    let currentBackupsTenantName = '';
    let currentBackupsTenantSlug = '';

    async function openBackupsModal(tenantId, tenantName, tenantSlug) {
      currentBackupsTenantId = tenantId;
      currentBackupsTenantName = tenantName;
      currentBackupsTenantSlug = tenantSlug;
      document.getElementById('backups-tenant-title').innerText = `Empresa: ${tenantName} (${tenantSlug}.sofiaerp.com)`;
      document.getElementById('modal-backups').classList.remove('hidden');
      document.getElementById('backups-db-size').innerText = 'Consultando...';
      document.getElementById('backups-filestore-size').innerText = 'Filestore: --';

      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/metrics`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const m = await res.json();
          document.getElementById('backups-db-size').innerText = m.database_size || '72 MB';
          document.getElementById('backups-filestore-size').innerText = `Filestore & Adjuntos: ${m.filestore_size || '0 MB'}`;
        }
      } catch (e) {
        document.getElementById('backups-db-size').innerText = 'Normal (~75 MB)';
      }

      loadTenantBackups(tenantId);
    }

    function closeBackupsModal() {
      document.getElementById('modal-backups').classList.add('hidden');
      currentBackupsTenantId = null;
    }

    async function loadTenantBackups(tenantId) {
      const container = document.getElementById('backups-list-container');
      container.innerHTML = '<div class="text-center py-6 text-xs text-slate-400"><i class="fa-solid fa-spinner fa-spin text-purple-600 mr-2"></i> Cargando lista de respaldos...</div>';
      const token = sessionStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/backups`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const backups = await res.json();

        if (!backups || backups.length === 0) {
          container.innerHTML = `
            <div class="text-center py-6 text-slate-400 text-xs bg-slate-50 rounded-xl border border-dashed border-slate-200">
              No hay copias de seguridad generadas aún para este cliente.<br/>
              Haz clic en "Crear Respaldo Ahora (.sql.gz)" arriba para generar la primera copia.
            </div>
          `;
          return;
        }

        container.innerHTML = backups.map(b => `
          <div class="flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-200 shadow-2xs hover:border-purple-200 transition">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center text-sm">
                <i class="fa-solid fa-file-zipper"></i>
              </div>
              <div>
                <div class="font-bold text-xs text-slate-800 font-mono">${b.filename}</div>
                <div class="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5 font-sans">
                  <span><i class="fa-regular fa-clock text-[10px]"></i> ${b.created_at}</span>
                  <span>·</span>
                  <span class="font-semibold text-purple-700">${b.size_human}</span>
                </div>
              </div>
            </div>
            <button onclick="downloadBackup('${tenantId}', '${b.filename}')" class="px-3 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold border border-purple-200 transition flex items-center gap-1.5 shadow-2xs">
              <i class="fa-solid fa-download"></i> Descargar
            </button>
          </div>
        `).join('');

      } catch (err) {
        container.innerHTML = `<div class="p-3 text-xs text-rose-600 bg-rose-50 rounded-xl">Error al cargar respaldos: ${err.message}</div>`;
      }
    }

    async function handleTriggerBackup() {
      if (!currentBackupsTenantId) return;
      const btn = document.getElementById('btn-trigger-backup');
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generando volcado en caliente...`;

      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${currentBackupsTenantId}/backups`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al generar backup');

        alert(`✅ Respaldo generado con éxito:\n\nArchivo: ${data.filename}\nTamaño: ${data.size_human}\nUbicación: Servidor Seguro SOFIA`);
        loadTenantBackups(currentBackupsTenantId);
      } catch (err) {
        alert('❌ Error: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Crear Respaldo Ahora (.sql.gz)`;
      }
    }

    async function downloadBackup(tenantId, filename) {
      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/backups/${filename}/download`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('No se pudo descargar el archivo de respaldo');

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        alert('Error en descarga: ' + err.message);
      }
    }

    // =========================================================================
    // ACCESO DE SOPORTE DIRECTO (GHOST LOGIN / IMPERSONATION)
    // =========================================================================
    async function handleSupportAccess(tenantId, tenantName, tenantSlug) {
      const confirmPrompt = `⚡ ACCESO DE SOPORTE DIRECTO (SUPERADMIN)\n\n¿Deseas ingresar de forma segura como Superadmin a "${tenantName}"?\n\n• Se generará una sesión temporal criptográfica de 30 minutos.\n• No requieres la contraseña del cliente.\n• Tu acceso quedará registrado en los logs de auditoría por seguridad.`;
      if (!confirm(confirmPrompt)) return;

      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/${tenantId}/support-token`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al generar acceso de soporte');

        // Abrir pestaña directa al ERP
        window.open(data.support_url, '_blank');
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    // =========================================================================
    // COMUNICADOS Y BANNERS GLOBALES
    // =========================================================================
    function openAnnouncementModal() {
      document.getElementById('modal-announcement').classList.remove('hidden');
      document.getElementById('form-announcement').reset();
    }

    function closeAnnouncementModal() {
      document.getElementById('modal-announcement').classList.add('hidden');
    }

    async function loadAnnouncements() {
      const container = document.getElementById('announcements-container');
      container.innerHTML = '<div class="text-center py-8 text-xs text-slate-400"><i class="fa-solid fa-spinner fa-spin text-amber-500 mr-2"></i> Cargando comunicados...</div>';
      const token = sessionStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch('/api/v1/tenants/system/announcements', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const list = await res.json();

        if (!list || list.length === 0) {
          container.innerHTML = `
            <div class="text-center py-10 text-slate-400 text-xs bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <i class="fa-regular fa-bell-slash text-2xl text-slate-300 block mb-2"></i>
              No hay comunicados globales activos en este momento.
            </div>
          `;
          return;
        }

        container.innerHTML = list.map(a => {
          let badgeColor = 'bg-blue-50 text-blue-700 border-blue-200';
          let icon = 'fa-info-circle';
          if (a.level === 'WARNING') { badgeColor = 'bg-amber-50 text-amber-800 border-amber-200'; icon = 'fa-triangle-exclamation'; }
          if (a.level === 'MAINTENANCE') { badgeColor = 'bg-rose-50 text-rose-700 border-rose-200'; icon = 'fa-screwdriver-wrench'; }
          if (a.level === 'PROMO') { badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200'; icon = 'fa-sparkles'; }

          const dateStr = a.created_at ? new Date(a.created_at).toLocaleString() : '';

          return `
            <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeColor}">
                    <i class="fa-solid ${icon} text-[10px]"></i> ${a.level}
                  </span>
                  <h4 class="font-bold text-sm text-slate-900">${a.title}</h4>
                </div>
                <p class="text-xs text-slate-600">${a.message}</p>
                <div class="text-[11px] text-slate-400 mt-1">${dateStr}</div>
              </div>
              <button onclick="handleDeleteAnnouncement('${a.id}')" class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold border border-rose-200 transition shrink-0">
                <i class="fa-solid fa-trash-can"></i> Retirar Aviso
              </button>
            </div>
          `;
        }).join('');

      } catch (err) {
        container.innerHTML = `<div class="p-3 text-xs text-rose-600 bg-rose-50 rounded-xl">Error al cargar comunicados: ${err.message}</div>`;
      }
    }

    async function handleCreateAnnouncement(e) {
      e.preventDefault();
      const token = sessionStorage.getItem(TOKEN_KEY);
      const btn = document.getElementById('btn-submit-ann');
      btn.disabled = true;

      const payload = {
        title: document.getElementById('ann-title').value.trim(),
        level: document.getElementById('ann-level').value,
        message: document.getElementById('ann-message').value.trim(),
      };

      try {
        const res = await fetch('/api/v1/tenants/system/announcements', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al publicar comunicado');

        closeAnnouncementModal();
        loadAnnouncements();
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        btn.disabled = false;
      }
    }

    async function handleDeleteAnnouncement(annId) {
      if (!confirm('¿Deseas retirar y desactivar este comunicado para todas las empresas?')) return;
      const token = sessionStorage.getItem(TOKEN_KEY);
      try {
        const res = await fetch(`/api/v1/tenants/system/announcements/${annId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Error al retirar comunicado');
        loadAnnouncements();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    // =========================================================================
    // AUDITORÍA & LOGS DE SEGURIDAD
    // =========================================================================
    async function loadAuditLogs() {
      const tbody = document.getElementById('audit-logs-body');
      tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 font-sans"><i class="fa-solid fa-spinner fa-spin text-indigo-600 text-lg mr-2"></i> Consultando registros de auditoría...</td></tr>';
      const token = sessionStorage.getItem(TOKEN_KEY);

      try {
        const res = await fetch('/api/v1/tenants/system/audit-logs', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const logs = await res.json();

        if (!logs || logs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 font-sans">No hay registros de auditoría aún.</td></tr>';
          return;
        }

        tbody.innerHTML = logs.map(l => {
          let actionBadge = 'bg-slate-100 text-slate-700';
          if (l.action.includes('PROVISION') || l.action.includes('CREATE')) actionBadge = 'bg-emerald-50 text-emerald-700 border-emerald-200';
          if (l.action.includes('SUSPEND') || l.action.includes('DELETE')) actionBadge = 'bg-rose-50 text-rose-700 border-rose-200';
          if (l.action.includes('BACKUP')) actionBadge = 'bg-purple-50 text-purple-700 border-purple-200';
          if (l.action.includes('SUPPORT') || l.action.includes('IMPERSONATION')) actionBadge = 'bg-amber-50 text-amber-800 border-amber-200';

          const detailsStr = typeof l.details === 'object' ? JSON.stringify(l.details) : String(l.details);

          return `
            <tr class="hover:bg-slate-50/70 transition border-b border-slate-100">
              <td class="px-5 py-3 font-semibold">
                <span class="inline-block px-2.5 py-0.5 rounded-md text-[11px] font-mono border ${actionBadge}">
                  ${l.action}
                </span>
              </td>
              <td class="px-5 py-3 font-sans text-slate-800">${l.tenant_name} (${l.tenant_slug})</td>
              <td class="px-5 py-3 text-slate-600">${l.ip_address || '127.0.0.1'}</td>
              <td class="px-5 py-3 text-slate-400">${l.created_at}</td>
              <td class="px-5 py-3 text-slate-500 max-w-xs truncate" title="${detailsStr}">${detailsStr}</td>
            </tr>
          `;
        }).join('');

      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-6 text-center text-rose-500 font-sans">Error al cargar logs: ${err.message}</td></tr>`;
      }
    }

    document.addEventListener('DOMContentLoaded', checkAuth);
  </script>
</body>
</html>
"""

@admin_ui_router.get("/admin", response_class=HTMLResponse, summary="Panel Gráfico de Administración SaaS")
async def get_admin_dashboard():
    """Retorna la interfaz web interactiva protegida con login para administración de clientes."""
    return HTML_CONTENT
