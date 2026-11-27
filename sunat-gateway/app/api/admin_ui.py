# -*- coding: utf-8 -*-
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PANEL_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sofia Gateway — Pasarela Resiliente SUNAT</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <style>
    :root {
      /* Sistema de Diseño Oficial SOFIA / Odoo 20 */
      --o20-navbar: #66598F;
      --o20-navbar-h: #554979;
      --o20-primary: #714B67;
      --o20-primary-h: #5C3B53;
      --o20-primary-soft: #EAE6F8;
      --o20-teal: #017E84;
      --o20-teal-h: #01666B;
      --o20-teal-soft: #D9F2EE;
      --bg: #F6F7F9;
      --card: #FFFFFF;
      --card2: #F9FAFB;
      --border: #E2E5EC;
      --text: #1F2937;
      --muted: #6B7280;
      --ok: #0F766E;
      --warn: #B45309;
      --err: #B91C1C;
      --info: #5B4B8A;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
    .hidden { display: none !important; }

    /* Top Navbar Centrado Estilo SOFIA Platform / Odoo 20 */
    header { background: var(--o20-navbar); color: #FFFFFF; box-shadow: 0 1px 3px rgba(17,24,39,.12); position: sticky; top: 0; z-index: 30; }
    .nav-inner { max-width: 1280px; margin: 0 auto; padding: 0 24px; min-height: 56px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
    .brand { font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 10px; letter-spacing: -0.01em; color: #FFFFFF; }
    .brand-mark { width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,.20); display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 15px; }
    .brand-sub { display: block; font-size: 11px; font-weight: 400; color: rgba(255,255,255,.78); margin-top: -1px; }

    /* Contenedor Principal Centrado (igual que SOFIA Platform max-w-7xl) */
    .container { max-width: 1280px; margin: 28px auto; padding: 0 24px; }
    .hero-banner { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; box-shadow: 0 1px 2px rgba(16,24,40,.03); }
    .hero-banner h1 { margin: 0; font-size: 21px; font-weight: 700; letter-spacing: -0.02em; color: var(--text); }
    .hero-banner p { margin: 4px 0 0 0; font-size: 13px; color: var(--muted); }

    /* Tabs de Navegación (Pill Bar Estilo SOFIA Platform) */
    .tabs { display: flex; align-items: center; gap: 6px; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 20px; flex-wrap: wrap; }
    .tab { background: transparent; border: none; color: #4B5563; padding: 8px 14px; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 12.5px; transition: background .15s, color .15s; }
    .tab:hover { background: #EAECEF; color: var(--text); }
    .tab.active { background: var(--o20-primary); color: #FFFFFF; box-shadow: 0 1px 2px rgba(113,75,103,.25); }

    .badge { padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
    .b-ok { background: var(--o20-teal-soft); color: var(--ok); }
    .b-warn { background: #FDE8D7; color: var(--warn); }
    .b-err { background: #FDE2E2; color: var(--err); }
    .b-info { background: var(--o20-primary-soft); color: var(--info); }
    .b-nav { background: rgba(255,255,255,.16); color: #FFFFFF; }

    /* KPIs Pastel Estilo Odoo 20 */
    .grid4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 22px; }
    .grid3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 22px; }
    .kpi { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; }
    .kpi-purple { background: #F4F1FB; border-color: #DED7F2; }
    .kpi-teal { background: #EBF8F6; border-color: #C4E8E2; }
    .kpi-peach { background: #FEF3E8; border-color: #F7D8BA; }
    .kpi-rose { background: #FDF0F0; border-color: #F6CECE; }
    .kpi .lbl { color: #4B5563; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .kpi .val { font-size: 28px; font-weight: 700; margin-top: 6px; color: var(--text); }
    .kpi .sub { font-size: 11.5px; color: var(--muted); margin-top: 4px; font-weight: 500; }

    /* Tarjetas de Escritorio */
    .desk-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; cursor: pointer; transition: border-color .15s, box-shadow .15s, transform .15s; }
    .desk-card:hover { border-color: var(--o20-primary); box-shadow: 0 4px 12px rgba(113,75,103,.10); transform: translateY(-1px); }
    .desk-card .title { font-weight: 700; font-size: 15px; margin-bottom: 6px; color: var(--o20-primary); }
    .desk-card .desc { font-size: 12.5px; color: var(--muted); line-height: 1.5; }

    /* Contenedores y Tablas */
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px 20px; margin-bottom: 18px; box-shadow: 0 1px 2px rgba(16,24,40,.03); }
    .card h3 { margin: 0 0 14px 0; font-size: 15px; font-weight: 700; color: var(--text); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    thead tr { background: var(--card2); }
    th, td { padding: 10px 10px; border-bottom: 1px solid #EEF0F4; text-align: left; }
    tbody tr:hover { background: #F9FAFB; }
    th { color: #4B5563; font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: .03em; }
    code { background: #F3F4F6; color: #374151; padding: 2px 5px; border-radius: 4px; font-size: 12px; }
    input, select, textarea { background: #FFFFFF; border: 1px solid #D1D5DB; color: var(--text); padding: 8px 10px; border-radius: 6px; width: 100%; font-size: 13px; transition: border-color .15s, box-shadow .15s; }
    input:focus, select:focus, textarea:focus { outline: none; border-color: var(--o20-primary); box-shadow: 0 0 0 3px rgba(113,75,103,.12); }
    label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }

    /* Botones Estilo Odoo 20 */
    .btn { background: var(--o20-primary); color: #FFFFFF; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; transition: background .15s; }
    .btn:hover { background: var(--o20-primary-h); }
    .btn-teal { background: var(--o20-teal); color: #FFFFFF; }
    .btn-teal:hover { background: var(--o20-teal-h); }
    .btn-sm { padding: 4px 10px; font-size: 12px; }
    .btn-sec { background: #FFFFFF; border: 1px solid #D1D5DB; color: #374151; }
    .btn-sec:hover { background: #F3F4F6; }
    .btn-nav { background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25); color: #FFFFFF; }
    .btn-nav:hover { background: rgba(255,255,255,.25); }
    .btn-err { background: #DC2626; color: #FFFFFF; }
    .btn-err:hover { background: #B91C1C; }

    /* Login Card */
    .login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; background: linear-gradient(180deg, #F4F1FB 0%, #F6F7F9 100%); }
    .login-box { max-width: 400px; width: 100%; background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 30px; box-shadow: 0 10px 25px rgba(102,89,143,.10); }
    .login-logo { width: 46px; height: 46px; border-radius: 10px; background: var(--o20-primary); color: #FFFFFF; font-weight: 800; font-size: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px auto; }
    .row-actions { display: flex; gap: 6px; flex-wrap: wrap; }
    .sunat-pill { display: flex; gap: 8px; align-items: center; font-size: 12px; flex-wrap: wrap; }
    pre { background: #1F2937; border: 1px solid var(--border); padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 12px; color: #E5E7EB; }
  </style>
</head>
<body>

<div id="loginView" class="login-wrap">
  <div class="login-box">
    <div class="login-logo">S</div>
    <h2 style="margin:0 0 4px 0;text-align:center;color:var(--text)">Sofia Gateway</h2>
    <p style="color:var(--muted);font-size:12.5px;text-align:center;margin:0 0 22px 0">Pasarela Resiliente SUNAT Híbrida · <code>gateway.sofiaerp.com</code></p>
    <div style="margin-bottom:12px">
      <label>Correo Administrador</label>
      <input id="loginEmail" type="email" value="admin@sofiaerp.com" />
    </div>
    <div style="margin-bottom:18px">
      <label>Contraseña</label>
      <input id="loginPass" type="password" placeholder="Contraseña" />
    </div>
    <button class="btn" style="width:100%;padding:10px" onclick="doLogin()">Ingresar al Panel</button>
    <p id="loginErr" style="color:var(--err);font-size:12px;margin-top:10px;text-align:center"></p>
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);text-align:center">
      <a href="/consulta" style="font-size:12.5px;font-weight:600;color:var(--o20-teal);text-decoration:none">¿Buscas tu comprobante? Ir al Portal de Consulta Pública →</a>
    </div>
  </div>
</div>

<div id="appView" class="hidden">
  <header>
    <div class="nav-inner">
      <div class="brand">
        <span class="brand-mark">S</span>
        <div>
          <span>Sofia Gateway</span>
          <span class="brand-sub">Pasarela Resiliente SUNAT • Modo Híbrido</span>
        </div>
      </div>
      <div class="sunat-pill">
        <span id="sunatBetaStatus" class="badge b-nav">SUNAT Beta: ...</span>
        <span id="sunatProdStatus" class="badge b-nav">SUNAT Prod: ...</span>
        <a href="/consulta" target="_blank" class="btn btn-sm btn-nav" style="text-decoration:none">Consulta Pública</a>
        <a href="https://api.sofiaerp.com/admin" target="_blank" class="btn btn-sm btn-nav" style="text-decoration:none">SOFIA Platform</a>
        <button class="btn btn-sm btn-nav" onclick="refreshAll()">Actualizar</button>
        <button class="btn btn-sm btn-nav" onclick="logout()">Salir</button>
      </div>
    </div>
  </header>

  <div class="container">
    <!-- Banner Principal Centrado (idéntico a SOFIA Platform) -->
    <div class="hero-banner">
      <div>
        <h1>Gestión de Emisión &amp; Cola SUNAT</h1>
        <p>Tenants SOFIA ERP firman localmente con su <code>.pfx</code> · Apps externas pueden firmar en Bóveda Gateway.</p>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <select id="globalRucFilter" onchange="onRucFilterChange()" style="width:auto;min-width:260px;padding:7px 12px">
          <option value="">Todas las Empresas (Vista Global)</option>
        </select>
        <span id="activeEnvBadge" class="badge b-info">Global</span>
      </div>
    </div>

    <!-- KPIs Pastel Siempre Visibles (idéntico a SOFIA Platform) -->
    <div class="grid4">
      <div class="kpi kpi-purple">
        <div class="lbl">Comprobantes Totales</div>
        <div class="val" id="kTotal">0</div>
        <div class="sub">Procesados en pasarela</div>
      </div>
      <div class="kpi kpi-teal">
        <div class="lbl">Aceptados SUNAT</div>
        <div class="val" style="color:var(--ok)" id="kAccepted">0</div>
        <div class="sub" style="color:var(--ok)">Con CDR oficial</div>
      </div>
      <div class="kpi kpi-peach">
        <div class="lbl">En Cola / Contingencia</div>
        <div class="val" style="color:var(--warn)" id="kQueued">0</div>
        <div class="sub" style="color:var(--warn)">Reintento automático activo</div>
      </div>
      <div class="kpi kpi-rose">
        <div class="lbl">Observados / Rechazados</div>
        <div class="val" style="color:var(--err)" id="kRejected">0</div>
        <div class="sub" style="color:var(--err)">Requieren revisión</div>
      </div>
    </div>

    <!-- Barra de Pestañas Pill (idéntica a SOFIA Platform) -->
    <nav class="tabs">
      <button class="tab active" data-tab="desk" onclick="showTab('desk', this)">Escritorio</button>
      <button class="tab" data-tab="documents" onclick="showTab('documents', this)">Documentos</button>
      <button class="tab" data-tab="summaries" onclick="showTab('summaries', this)">Resúmenes (RC/RA)</button>
      <button class="tab" data-tab="contingencies" onclick="showTab('contingencies', this)">Contingencias</button>
      <button class="tab" data-tab="observations" onclick="showTab('observations', this)">Observaciones</button>
      <button class="tab" data-tab="issuers" onclick="showTab('issuers', this)">Empresas y Certificados</button>
      <button class="tab" data-tab="clients" onclick="showTab('clients', this)">Credenciales / API Keys</button>
      <button class="tab" data-tab="connectors" onclick="showTab('connectors', this)">Conectores IA (MCP)</button>
      <button class="tab" data-tab="tester" onclick="showTab('tester', this)">Probador Rápido</button>
    </nav>

    <!-- TAB 1: ESCRITORIO -->
    <div id="tab-desk">

      <div class="grid3">
        <div class="desk-card" onclick="openTab('documents')">
          <div class="title">Documentos</div>
          <div class="desc">Bandeja de Facturas, Boletas y Notas. Descarga de XML/CDR, reintentos y recuperación anti-1033.</div>
        </div>
        <div class="desk-card" onclick="openTab('summaries')">
          <div class="title">Resúmenes y Bajas (RC / RA)</div>
          <div class="desc">Resúmenes Diarios de Boletas y Comunicaciones de Baja con seguimiento automático de Ticket SUNAT.</div>
        </div>
        <div class="desk-card" onclick="openTab('contingencies')">
          <div class="title">Contingencias y Colas</div>
          <div class="desc">Monitor de envíos en reintento, ventana nocturna y alertas antes de vencer el plazo legal de 3 días.</div>
        </div>
        <div class="desk-card" onclick="openTab('observations')">
          <div class="title">Resumen de Observaciones</div>
          <div class="desc">Comprobantes aceptados con observaciones (&gt;= 4000) y rechazos SUNAT (2xxx/3xxx) para corrección rápida.</div>
        </div>
        <div class="desk-card" onclick="openTab('issuers')">
          <div class="title">Empresas y Certificados</div>
          <div class="desc">Empresas auto-sincronizadas desde SOFIA ERP (firma local) o con certificado <code>.pfx</code> en bóveda.</div>
        </div>
        <div class="desk-card" onclick="openTab('clients')">
          <div class="title">Credenciales y API Keys</div>
          <div class="desc">Llaves <code>sk_live_...</code> aisladas por RUC y Webhooks firmados HMAC-SHA256 para POS/apps externas.</div>
        </div>
        <div class="desk-card" onclick="openTab('connectors')">
          <div class="title">Conectores IA (Claude / ChatGPT / MCP)</div>
          <div class="desc">Conecta Claude, ChatGPT, Cursor o n8n vía Remote MCP (<code>/mcp</code>) y OpenAPI AI (<code>/openapi-ai.json</code>).</div>
        </div>
        <div class="desk-card" onclick="openTab('tester')">
          <div class="title">Probador Rápido (Beta)</div>
          <div class="desc">Emite una factura de prueba contra SUNAT Beta y verifica la firma XMLDSig y el CDR oficial.</div>
        </div>
      </div>
    </div>

    <!-- TAB 2: DOCUMENTOS -->
    <div id="tab-documents" class="hidden">
      <div class="card">
        <h3>Bandeja de Comprobantes (Últimos 50)</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr>
                <th>RUC Emisor</th><th>Comprobante</th><th>Fecha</th><th>Total</th>
                <th>Estado</th><th>SUNAT</th><th>Intentos</th><th>Acciones</th>
              </tr>
            </thead>
            <tbody id="docsTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2B: RESÚMENES Y BAJAS (RC/RA) -->
    <div id="tab-summaries" class="hidden">
      <div class="card">
        <h3>Resúmenes Diarios (RC) y Comunicaciones de Baja (RA)</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr>
                <th>RUC</th><th>Resumen / Baja</th><th>Fecha</th><th>Ticket SUNAT</th>
                <th>Estado</th><th>Detalle SUNAT</th><th>Intentos</th><th>Acciones</th>
              </tr>
            </thead>
            <tbody id="summariesTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: CONTINGENCIAS -->
    <div id="tab-contingencies" class="hidden">
      <div class="card">
        <h3>Contingencias, Colas Activas y Plazo Legal SUNAT (3 días)</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr>
                <th>RUC</th><th>Comprobante</th><th>Fecha</th><th>Estado</th>
                <th>Intentos</th><th>Horas Restantes</th><th>Último Mensaje</th><th>Acciones</th>
              </tr>
            </thead>
            <tbody id="contTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 4: OBSERVACIONES -->
    <div id="tab-observations" class="hidden">
      <div class="card">
        <h3>Resumen de Observaciones (&gt;= 4000) y Rechazos (2xxx / 3xxx)</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr>
                <th>RUC</th><th>Comprobante</th><th>Fecha</th><th>Estado</th>
                <th>Código SUNAT</th><th>Detalle / Notas</th><th>Acciones</th>
              </tr>
            </thead>
            <tbody id="obsTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: EMPRESAS Y CERTIFICADOS -->
    <div id="tab-issuers" class="hidden">
      <div class="card">
        <h3>Registrar o Actualizar Empresa Emisora (RUC)</h3>
        <div class="form-grid">
          <div><label>RUC (11 dígitos)</label><input id="issRuc" placeholder="20600994345" maxlength="11" /></div>
          <div><label>Razón Social</label><input id="issName" placeholder="MI EMPRESA S.A.C." /></div>
          <div><label>Dirección Fiscal</label><input id="issAddr" placeholder="AV. JAVIER PRADO 123, LIMA" /></div>
          <div><label>Ubigeo (6 dígitos)</label><input id="issUbigeo" value="150101" maxlength="6" /></div>
          <div>
            <label>Entorno SUNAT</label>
            <select id="issBeta">
              <option value="true">SUNAT Beta (Pruebas MODDATOS)</option>
              <option value="false">SUNAT Producción Real</option>
            </select>
          </div>
          <div>
            <label>Régimen Tributario</label>
            <select id="issNrus">
              <option value="false">General / MYPE / RER (Facturas + Boletas)</option>
              <option value="true">Nuevo RUS — NRUS (Solo Boletas sin IGV)</option>
            </select>
          </div>
          <div>
            <label>Política de Envío</label>
            <select id="issPolicy">
              <option value="INSTANT_WITH_RETRY">Inmediato + Reintentos Inteligentes</option>
              <option value="SCHEDULED_NIGHT">Ventana Nocturna (01:00 - 05:00 Lima)</option>
            </select>
          </div>
          <div>
            <label>Modo de Firma Digital</label>
            <select id="issSigningMode">
              <option value="tenant_local">Híbrido SOFIA ERP (firma local en Tenant Odoo)</option>
              <option value="gateway_vault">Bóveda Sofia Gateway (subir .pfx o Demo Beta)</option>
            </select>
          </div>
          <div><label>Usuario SOL (opcional en Beta)</label><input id="issSolUser" placeholder="MODDATOS o RUC+USER" /></div>
          <div><label>Clave SOL (opcional en Beta)</label><input id="issSolPass" type="password" placeholder="Clave SOL" /></div>
          <div><label>Certificado .pfx (solo si firma en Gateway)</label><input id="issPfxFile" type="file" accept=".pfx,.p12" /></div>
          <div><label>Contraseña .pfx</label><input id="issPfxPass" type="password" placeholder="Clave del certificado" /></div>
          <div><label>Correo para Alertas</label><input id="issAlertEmail" type="email" placeholder="facturacion@empresa.com" /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="saveIssuer()">Guardar Empresa</button>
          <span id="issMsg" style="margin-left:12px;font-size:12px;color:var(--ok)"></span>
        </div>
      </div>

      <div class="card">
        <h3>Empresas Registradas</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr><th>RUC</th><th>Razón Social</th><th>Entorno</th><th>Modo de Firma</th><th>Política</th><th>Certificado</th><th>SOL</th><th>Acciones</th></tr>
            </thead>
            <tbody id="issuersTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 6: CREDENCIALES Y API KEYS -->
    <div id="tab-clients" class="hidden">
      <div class="card">
        <h3>Crear Aplicación Cliente / API Key (Apps Externas y POS)</h3>
        <div class="form-grid">
          <div><label>Nombre de la Aplicación</label><input id="cliName" placeholder="POS Externo / Ecommerce" /></div>
          <div><label>Descripción</label><input id="cliDesc" placeholder="Integración de ventas" /></div>
          <div><label>RUCs Permitidos (separados por coma, vacío = todos)</label><input id="cliRucs" placeholder="20600994345" /></div>
          <div><label>Webhook URL (notificación de CDR)</label><input id="cliWebhook" placeholder="https://app.cliente.com/webhook/sunat" /></div>
          <div><label>Webhook Secret (HMAC-SHA256)</label><input id="cliSecret" placeholder="whsec_mi_secreto" /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="createClient()">Generar API Key</button>
        </div>
        <div id="newKeyBox" class="hidden" style="margin-top:14px;padding:12px;background:#EBF8F6;border:1px solid #017E84;border-radius:8px;font-size:13px;color:#0F766E"></div>
      </div>

      <div class="card">
        <h3>Aplicaciones Activas</h3>
        <table>
          <thead>
            <tr><th>Nombre</th><th>Prefijo API Key</th><th>RUCs Permitidos</th><th>Webhook</th><th>Último Uso</th><th>Acción</th></tr>
          </thead>
          <tbody id="clientsTable"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 7: PROBADOR RÁPIDO -->
    <div id="tab-tester" class="hidden">
      <div class="card">
        <h3>Emitir Comprobante de Prueba (Modo JSON → Firma en Gateway → SUNAT Beta)</h3>
        <div class="form-grid">
          <div><label>RUC Emisor (con .pfx o Demo en Gateway)</label><input id="tRuc" placeholder="20600994345" /></div>
          <div><label>Serie</label><input id="tSerie" value="FE01" maxlength="4" /></div>
          <div><label>Correlativo</label><input id="tCorr" value="1" /></div>
          <div><label>RUC Cliente</label><input id="tCustRuc" value="20100047218" /></div>
          <div><label>Razón Social Cliente</label><input id="tCustName" value="CLIENTE DE PRUEBA S.A.C." /></div>
          <div><label>Importe Base sin IGV (PEN)</label><input id="tAmount" type="number" value="100.00" step="0.01" /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="emitTestDoc()">Emitir y Enviar a SUNAT Beta</button>
        </div>
        <pre id="testerOut" class="hidden" style="margin-top:14px"></pre>
      </div>
    </div>

    <!-- TAB 8: CONECTORES IA (REMOTE MCP + OPENAPI AI) -->
    <div id="tab-connectors" class="hidden">
      <div class="card" style="background:linear-gradient(135deg, #66598F 0%, #714B67 55%, #017E84 100%);color:#FFFFFF;border:none;padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">
          <div>
            <span class="badge b-nav" style="margin-bottom:8px">ADR-010 · Remote MCP (Streamable HTTP) + OpenAPI 3.1</span>
            <h2 style="margin:4px 0 6px 0;font-size:20px;color:#FFFFFF">Conecta Claude, ChatGPT, Cursor o n8n a Sofia SUNAT Gateway</h2>
            <p style="margin:0;font-size:13px;color:rgba(255,255,255,.88);max-width:680px">
              Emite facturas y boletas, calcula IGV, consulta CDRs y explica errores SUNAT directamente desde tu asistente de IA usando API Keys aisladas por RUC.
            </p>
          </div>
          <div class="row-actions">
            <button class="btn btn-nav" onclick="copyText(window.location.origin + '/mcp', this)">Copiar URL MCP</button>
            <button class="btn btn-nav" onclick="copyText(window.location.origin + '/openapi-ai.json', this)">Copiar OpenAPI AI</button>
            <button class="btn" style="background:#FFFFFF;color:#714B67" onclick="openTab('clients')">Crear API Key para IA</button>
          </div>
        </div>
      </div>

      <div class="grid3">
        <div class="card">
          <h3>Claude Code / Claude Desktop</h3>
          <p style="font-size:12.5px;color:var(--muted);margin-top:0">Conecta mediante <strong>Remote MCP (Streamable HTTP)</strong> usando una API Key restringida al RUC deseado.</p>
          <pre id="snippetClaude">claude mcp add --transport http sofia-sunat https://gateway.sofiaerp.com/mcp \
  --header "Authorization: Bearer sk_live_TU_API_KEY"</pre>
          <button class="btn btn-sm btn-sec" onclick="copyText(document.getElementById('snippetClaude').textContent, this)">Copiar comando</button>
        </div>

        <div class="card">
          <h3>ChatGPT (Connectors / Custom GPT)</h3>
          <p style="font-size:12.5px;color:var(--muted);margin-top:0">Usa el endpoint MCP en <strong>ChatGPT Connectors</strong> o importa el esquema en <strong>Custom GPT Actions</strong> (Auth: Bearer).</p>
          <pre id="snippetChatGpt">MCP URL:     https://gateway.sofiaerp.com/mcp
OpenAPI AI:  https://gateway.sofiaerp.com/openapi-ai.json
Auth Header: Authorization: Bearer sk_live_TU_API_KEY</pre>
          <button class="btn btn-sm btn-sec" onclick="copyText(document.getElementById('snippetChatGpt').textContent, this)">Copiar configuración</button>
        </div>

        <div class="card">
          <h3>Cursor / VS Code / n8n</h3>
          <p style="font-size:12.5px;color:var(--muted);margin-top:0">Agrega este bloque a <code>.cursor/mcp.json</code> o usa los endpoints REST <code>/api/v1/ai/*</code> en n8n/Make.</p>
          <pre id="snippetCursor">{
  "mcpServers": {
    "sofia-sunat": {
      "url": "https://gateway.sofiaerp.com/mcp",
      "headers": {
        "Authorization": "Bearer sk_live_TU_API_KEY"
      }
    }
  }
}</pre>
          <button class="btn btn-sm btn-sec" onclick="copyText(document.getElementById('snippetCursor').textContent, this)">Copiar mcp.json</button>
        </div>
      </div>

      <div class="card">
        <h3>Herramientas MCP Activas &amp; Probador en Vivo</h3>
        <p style="font-size:12.5px;color:var(--muted);margin-top:0">
          Verifica en tiempo real la respuesta JSON-RPC 2.0 de <code>POST /mcp</code> (seguro, sin emitir documentos reales).
        </p>
        <div class="row-actions" style="margin-bottom:12px">
          <button class="btn btn-teal btn-sm" onclick="testMcp('tools/list', {})">Probar tools/list</button>
          <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'calculate_totals_igv', arguments:{currency:'PEN', items:[{description:'Suscripción SOFIA ERP', quantity:1, unit_price_without_tax:100}]}})">Probar calculate_totals_igv</button>
          <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'explain_sunat_error', arguments:{sunat_code:'1033'}})">Probar explain_sunat_error (1033)</button>
          <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'list_issuers', arguments:{}})">Probar list_issuers</button>
        </div>
        <pre id="mcpTestOut" class="hidden"></pre>
      </div>
    </div>
  </div>
</div>

<script>
let TOKEN = localStorage.getItem('sofia_gw_token') || '';
let ISSUERS_CACHE = [];

async function api(path, opts = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  if (TOKEN) headers['Authorization'] = 'Bearer ' + TOKEN;
  const r = await fetch('/api/v1' + path, Object.assign({}, opts, { headers }));
  if (r.status === 401) { logout(); throw new Error('Sesión expirada'); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
  return data;
}

async function doLogin() {
  document.getElementById('loginErr').textContent = '';
  try {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('loginEmail').value,
        password: document.getElementById('loginPass').value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error de autenticación');
    TOKEN = data.access_token;
    localStorage.setItem('sofia_gw_token', TOKEN);
    bootApp();
  } catch (e) {
    document.getElementById('loginErr').textContent = e.message;
  }
}

function logout() {
  TOKEN = '';
  localStorage.removeItem('sofia_gw_token');
  document.getElementById('appView').classList.add('hidden');
  document.getElementById('loginView').classList.remove('hidden');
}

function showTab(name, btn) {
  ['desk', 'documents', 'summaries', 'contingencies', 'observations', 'issuers', 'clients', 'connectors', 'tester'].forEach(t => {
    document.getElementById('tab-' + t).classList.toggle('hidden', t !== name);
  });
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function openTab(name) {
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  showTab(name, btn);
}

function statusBadge(st) {
  if (st === 'ACCEPTED') return '<span class="badge b-ok">ACEPTADO</span>';
  if (st === 'ACCEPTED_WITH_OBS') return '<span class="badge b-warn">OBSERVADO</span>';
  if (st === 'REJECTED' || st === 'VALIDATION_ERROR' || st === 'EXPIRED_ALERT') return `<span class="badge b-err">${st}</span>`;
  return `<span class="badge b-info">${st}</span>`;
}

function selectedRuc() {
  return document.getElementById('globalRucFilter').value || '';
}

function onRucFilterChange() {
  const ruc = selectedRuc();
  const badge = document.getElementById('activeEnvBadge');
  const iss = ISSUERS_CACHE.find(i => i.ruc === ruc);
  if (!iss) {
    badge.className = 'badge b-info';
    badge.textContent = 'Global';
  } else {
    badge.className = iss.is_beta ? 'badge b-warn' : 'badge b-ok';
    badge.textContent = `${iss.is_beta ? 'BETA' : 'PRODUCCIÓN'} · ${iss.signing_mode === 'tenant_local' ? 'Firma en Tenant' : 'Bóveda Gateway'}`;
  }
  refreshScopedData();
}

async function refreshSunatHealth() {
  try {
    const h = await fetch('/api/v1/health/sunat').then(r => r.json());
    const b = document.getElementById('sunatBetaStatus');
    const p = document.getElementById('sunatProdStatus');
    b.className = 'badge ' + (h.sunat_beta?.online ? 'b-ok' : 'b-err');
    b.textContent = `SUNAT Beta: ${h.sunat_beta?.online ? 'ONLINE' : 'CAÍDO'} (${h.sunat_beta?.latency_ms || 0}ms)`;
    p.className = 'badge ' + (h.sunat_prod?.online ? 'b-ok' : 'b-err');
    p.textContent = `SUNAT Prod: ${h.sunat_prod?.online ? 'ONLINE' : 'CAÍDO'} (${h.sunat_prod?.latency_ms || 0}ms)`;
  } catch (e) {}
}

async function refreshScopedData() {
  const ruc = selectedRuc();
  const q = ruc ? `?ruc=${encodeURIComponent(ruc)}` : '';
  const [stats, docs, summaries, conts, obs] = await Promise.all([
    api('/stats' + q),
    api('/documents' + (ruc ? `?ruc=${encodeURIComponent(ruc)}&limit=50` : '?limit=50')),
    api('/summaries' + q),
    api('/contingencies' + q),
    api('/observations' + q),
  ]);

  document.getElementById('kTotal').textContent = stats.total_documents;
  document.getElementById('kAccepted').textContent = stats.accepted;
  document.getElementById('kQueued').textContent = stats.queued_or_retrying;
  document.getElementById('kRejected').textContent = stats.rejected + stats.at_risk_deadline + (stats.accepted_with_obs || 0);

  document.getElementById('docsTable').innerHTML = docs.map(d => `
    <tr>
      <td><code>${d.issuer_ruc}</code></td>
      <td><strong>${d.doc_type}</strong> ${d.number}</td>
      <td>${d.issue_date}</td>
      <td>${d.currency} ${d.total_amount.toFixed(2)}</td>
      <td>${statusBadge(d.status)}</td>
      <td style="max-width:260px;font-size:12px;color:var(--muted)">${d.sunat_code ? `[${d.sunat_code}] ` : ''}${d.sunat_message || ''}</td>
      <td>${d.attempt_count}</td>
      <td class="row-actions">
        <button class="btn btn-sm btn-sec" onclick="retryDoc('${d.id}')">Reintentar</button>
        <button class="btn btn-sm btn-sec" onclick="recoverCdr('${d.id}')">CDR 1033</button>
        <button class="btn btn-sm btn-sec" onclick="downloadFile('${d.id}','xml')">XML</button>
        ${d.has_cdr ? `<button class="btn btn-sm" onclick="downloadFile('${d.id}','cdr')">CDR</button>` : ''}
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">Sin comprobantes registrados aún.</td></tr>';

  document.getElementById('summariesTable').innerHTML = summaries.map(s => `
    <tr>
      <td><code>${s.issuer_ruc}</code></td>
      <td><strong>${s.number}</strong></td>
      <td>${s.issue_date}</td>
      <td><code>${s.sunat_ticket || '-'}</code></td>
      <td>${statusBadge(s.status)}</td>
      <td style="max-width:260px;font-size:12px;color:var(--muted)">${s.sunat_code ? `[${s.sunat_code}] ` : ''}${s.sunat_message || ''}</td>
      <td>${s.attempt_count}</td>
      <td class="row-actions">
        <button class="btn btn-sm btn-sec" onclick="retryDoc('${s.id}')">Consultar / Reenviar</button>
        <button class="btn btn-sm btn-sec" onclick="downloadFile('${s.id}','xml')">XML</button>
        ${s.has_cdr ? `<button class="btn btn-sm" onclick="downloadFile('${s.id}','cdr')">CDR</button>` : ''}
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">Sin Resúmenes Diarios (RC) ni Comunicaciones de Baja (RA).</td></tr>';

  document.getElementById('contTable').innerHTML = conts.map(c => `
    <tr>
      <td><code>${c.issuer_ruc}</code></td>
      <td><strong>${c.doc_type}</strong> ${c.number}</td>
      <td>${c.issue_date}</td>
      <td>${statusBadge(c.status)}</td>
      <td>${c.attempt_count}</td>
      <td>${c.hours_left !== null ? `<span class="badge ${c.hours_left < 24 ? 'b-err' : 'b-warn'}">${c.hours_left}h</span>` : '-'}</td>
      <td style="max-width:260px;font-size:12px;color:var(--muted)">${c.sunat_message || ''}</td>
      <td class="row-actions">
        <button class="btn btn-sm btn-sec" onclick="retryDoc('${c.id}')">Reenviar</button>
        <button class="btn btn-sm btn-sec" onclick="recoverCdr('${c.id}')">Consultar CDR</button>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">Sin contingencias ni colas pendientes.</td></tr>';

  document.getElementById('obsTable').innerHTML = obs.map(o => `
    <tr>
      <td><code>${o.issuer_ruc}</code></td>
      <td><strong>${o.doc_type}</strong> ${o.number}</td>
      <td>${o.issue_date}</td>
      <td>${statusBadge(o.status)}</td>
      <td><code>${o.sunat_code || '-'}</code></td>
      <td style="font-size:12px;color:var(--muted)">${o.sunat_message || ''} ${(o.sunat_notes || []).join(' | ')}</td>
      <td><button class="btn btn-sm btn-sec" onclick="downloadFile('${o.id}','xml')">XML</button></td>
    </tr>
  `).join('') || '<tr><td colspan="7" style="color:var(--muted);text-align:center">Sin observaciones ni rechazos SUNAT.</td></tr>';
}

async function refreshAll() {
  refreshSunatHealth();
  const [issuers, clients] = await Promise.all([api('/issuers'), api('/clients')]);
  ISSUERS_CACHE = issuers;

  const sel = document.getElementById('globalRucFilter');
  const prev = sel.value;
  sel.innerHTML = '<option value="">Todas las Empresas (Vista Global)</option>' + issuers.map(i =>
    `<option value="${i.ruc}">${i.ruc} — ${i.business_name} [${i.is_beta ? 'BETA' : 'PROD'}]</option>`
  ).join('');
  if (issuers.some(i => i.ruc === prev)) sel.value = prev;

  document.getElementById('issuersTable').innerHTML = issuers.map(i => `
    <tr>
      <td><code>${i.ruc}</code></td>
      <td>${i.business_name} ${i.is_nrus ? '<span class="badge b-info" style="margin-left:4px">NRUS</span>' : ''}</td>
      <td>${i.is_beta ? '<span class="badge b-warn">BETA</span>' : '<span class="badge b-ok">PRODUCCIÓN</span>'}</td>
      <td>${i.signing_mode === 'tenant_local' ? '<span class="badge b-info">Tenant Odoo (.pfx local)</span>' : '<span class="badge b-ok">Bóveda Gateway</span>'}</td>
      <td><code>${i.dispatch_policy}</code></td>
      <td>${i.has_certificate ? (i.cert_is_demo ? '<span class="badge b-warn">DEMO</span>' : `<span class="badge b-ok">OK (${i.cert_days_left}d)</span>`) : '<span class="badge b-info">En Tenant</span>'}</td>
      <td>${i.has_sol ? '<span class="badge b-ok">OK</span>' : '<span class="badge b-err">Falta</span>'}</td>
      <td>${i.is_beta ? `<button class="btn btn-sm btn-err" onclick="purgeBeta('${i.ruc}')">Limpiar Beta</button>` : '<span style="font-size:11px;color:var(--muted)">Protegido</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">Registra o sincroniza tu primera empresa desde SOFIA ERP.</td></tr>';

  document.getElementById('clientsTable').innerHTML = clients.map(c => `
    <tr>
      <td><strong>${c.name}</strong><div style="font-size:11px;color:var(--muted)">${c.description || ''}</div></td>
      <td><code>${c.key_prefix}...</code></td>
      <td>${c.allowed_rucs ? c.allowed_rucs.join(', ') : 'Todos'}</td>
      <td style="font-size:12px">${c.webhook_url || '-'}</td>
      <td style="font-size:12px;color:var(--muted)">${c.last_used_at ? c.last_used_at.slice(0,19).replace('T',' ') : 'Nunca'}</td>
      <td>${c.is_active ? `<button class="btn btn-sm btn-err" onclick="revokeClient('${c.id}')">Revocar</button>` : '<span class="badge b-err">Revocada</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" style="color:var(--muted);text-align:center">Sin API Keys creadas.</td></tr>';

  if (issuers.length && !document.getElementById('tRuc').value) {
    document.getElementById('tRuc').value = issuers[0].ruc;
  }
  await refreshScopedData();
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function saveIssuer() {
  const msg = document.getElementById('issMsg');
  msg.textContent = 'Guardando...';
  try {
    const fileInput = document.getElementById('issPfxFile');
    let pfx_base64 = null;
    if (fileInput.files && fileInput.files[0]) pfx_base64 = await fileToBase64(fileInput.files[0]);
    const isBeta = document.getElementById('issBeta').value === 'true';
    const tenantLocal = document.getElementById('issSigningMode').value === 'tenant_local';
    await api('/issuers', {
      method: 'POST',
      body: JSON.stringify({
        ruc: document.getElementById('issRuc').value.trim(),
        business_name: document.getElementById('issName').value.trim(),
        address: document.getElementById('issAddr').value.trim() || null,
        ubigeo: document.getElementById('issUbigeo').value.trim() || '150101',
        is_beta: isBeta,
        is_nrus: document.getElementById('issNrus').value === 'true',
        dispatch_policy: document.getElementById('issPolicy').value,
        sol_username: document.getElementById('issSolUser').value.trim() || null,
        sol_password: document.getElementById('issSolPass').value || null,
        pfx_base64,
        pfx_password: document.getElementById('issPfxPass').value || null,
        tenant_local_signing: tenantLocal && !pfx_base64,
        generate_demo_cert: isBeta && !tenantLocal && !pfx_base64,
        alert_email: document.getElementById('issAlertEmail').value.trim() || null
      })
    });
    msg.textContent = 'Empresa guardada correctamente.';
    refreshAll();
  } catch (e) {
    msg.style.color = '#f87171';
    msg.textContent = e.message;
  }
}

async function createClient() {
  const rucsRaw = document.getElementById('cliRucs').value.trim();
  const allowed_rucs = rucsRaw ? rucsRaw.split(',').map(s => s.trim()).filter(Boolean) : null;
  const res = await api('/clients', {
    method: 'POST',
    body: JSON.stringify({
      name: document.getElementById('cliName').value.trim(),
      description: document.getElementById('cliDesc').value.trim() || null,
      allowed_rucs,
      webhook_url: document.getElementById('cliWebhook').value.trim() || null,
      webhook_secret: document.getElementById('cliSecret').value.trim() || null
    })
  });
  const box = document.getElementById('newKeyBox');
  box.classList.remove('hidden');
  box.innerHTML = `<strong>API Key creada (cópiala ahora, no se volverá a mostrar):</strong><br><code style="font-size:14px;color:#017E84;background:#FFFFFF">${res.api_key}</code>`;
  refreshAll();
}

async function purgeBeta(ruc) {
  if (!confirm(`¿Eliminar todos los comprobantes de prueba BETA del RUC ${ruc}? Haz esto antes de pasar la empresa a Producción.`)) return;
  try {
    const res = await api(`/issuers/${encodeURIComponent(ruc)}/beta-documents`, { method: 'DELETE' });
    alert(`Limpieza completada para ${ruc}: ${res.deleted_documents} documentos y ${res.removed_files} archivos eliminados.`);
    refreshAll();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function revokeClient(id) {
  if (!confirm('¿Revocar esta API Key?')) return;
  await api('/clients/' + id, { method: 'DELETE' });
  refreshAll();
}

async function retryDoc(id) { await api(`/documents/${id}/retry`, { method: 'POST' }); setTimeout(refreshScopedData, 1200); }
async function recoverCdr(id) { await api(`/documents/${id}/recover-cdr`, { method: 'POST' }); setTimeout(refreshScopedData, 1500); }

async function downloadFile(id, kind) {
  const r = await fetch(`/api/v1/documents/${id}/${kind}`, { headers: { 'Authorization': 'Bearer ' + TOKEN } });
  if (!r.ok) { alert('Archivo no disponible aún.'); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = kind === 'cdr' ? `CDR-${id}.zip` : `XML-${id}.xml`;
  a.click();
  URL.revokeObjectURL(url);
}

async function emitTestDoc() {
  const out = document.getElementById('testerOut');
  out.classList.remove('hidden');
  out.textContent = 'Firmando localmente y enviando a SUNAT Beta...';
  try {
    const today = new Date().toISOString().slice(0, 10);
    const res = await api('/documents/emit', {
      method: 'POST',
      body: JSON.stringify({
        issuer_ruc: document.getElementById('tRuc').value.trim(),
        doc_type: '01',
        serie: document.getElementById('tSerie').value.trim().toUpperCase(),
        correlativo: document.getElementById('tCorr').value.trim(),
        issue_date: today,
        currency: 'PEN',
        try_sync: true,
        customer: {
          doc_type: '6',
          doc_number: document.getElementById('tCustRuc').value.trim(),
          name: document.getElementById('tCustName').value.trim()
        },
        items: [{
          code: 'DEMO01',
          description: 'Servicio de Prueba Sofia Gateway',
          unit_code: 'NIU',
          quantity: 1,
          unit_price_without_tax: parseFloat(document.getElementById('tAmount').value || '100'),
          igv_affectation_code: '10',
          igv_rate: 0.18
        }]
      })
    });
    out.textContent = JSON.stringify(res, null, 2);
    document.getElementById('tCorr').value = String(parseInt(document.getElementById('tCorr').value || '1', 10) + 1);
    setTimeout(refreshScopedData, 1500);
  } catch (e) {
    out.textContent = 'ERROR: ' + e.message;
  }
}

function copyText(txt, btn) {
  navigator.clipboard.writeText(txt).then(() => {
    if (btn) {
      const prev = btn.textContent;
      btn.textContent = '¡Copiado!';
      setTimeout(() => { btn.textContent = prev; }, 1400);
    }
  });
}

async function testMcp(method, params) {
  const out = document.getElementById('mcpTestOut');
  out.classList.remove('hidden');
  out.textContent = 'Ejecutando POST /mcp (' + method + ')...';
  try {
    const r = await fetch('/mcp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + TOKEN
      },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
    });
    const data = await r.json();
    out.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = 'ERROR: ' + e.message;
  }
}

function bootApp() {
  document.getElementById('loginView').classList.add('hidden');
  document.getElementById('appView').classList.remove('hidden');
  refreshAll();
}

if (TOKEN) bootApp();
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def gateway_panel():
    return HTMLResponse(content=PANEL_HTML)
