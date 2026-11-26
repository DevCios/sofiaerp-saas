# -*- coding: utf-8 -*-
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PANEL_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SOFIA SUNAT Gateway — Caja Negra Multi-App</title>
  <style>
    :root {
      --bg: #0b1120; --card: #111827; --card2: #1e293b; --border: #273449;
      --text: #f1f5f9; --muted: #94a3b8; --primary: #3b82f6; --primary-h: #2563eb;
      --ok: #10b981; --warn: #f59e0b; --err: #ef4444; --info: #06b6d4;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); }
    .hidden { display: none !important; }
    header { background: var(--card); border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; }
    .brand { font-weight: 700; font-size: 18px; display: flex; align-items: center; gap: 10px; }
    .badge { padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; display: inline-block; }
    .b-ok { background: rgba(16,185,129,.18); color: #34d399; }
    .b-warn { background: rgba(245,158,11,.18); color: #fbbf24; }
    .b-err { background: rgba(239,68,68,.18); color: #f87171; }
    .b-info { background: rgba(6,182,212,.18); color: #22d3ee; }
    .container { max-width: 1280px; margin: 24px auto; padding: 0 20px; }
    .tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    .tab { background: var(--card); border: 1px solid var(--border); color: var(--muted); padding: 9px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
    .tab.active { background: var(--primary); color: #fff; border-color: var(--primary); }
    .grid4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 20px; }
    .kpi { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
    .kpi .lbl { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    .kpi .val { font-size: 28px; font-weight: 700; margin-top: 6px; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 18px; }
    .card h3 { margin: 0 0 14px 0; font-size: 15px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: left; }
    th { color: var(--muted); font-weight: 600; font-size: 12px; }
    input, select, textarea { background: var(--card2); border: 1px solid var(--border); color: var(--text); padding: 8px 10px; border-radius: 6px; width: 100%; font-size: 13px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
    .btn:hover { background: var(--primary-h); }
    .btn-sm { padding: 4px 9px; font-size: 12px; }
    .btn-sec { background: var(--card2); border: 1px solid var(--border); color: var(--text); }
    .btn-err { background: #dc2626; }
    .login-box { max-width: 380px; margin: 90px auto; background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 28px; }
    .row-actions { display: flex; gap: 6px; flex-wrap: wrap; }
    .sunat-pill { display: flex; gap: 10px; align-items: center; font-size: 12px; }
    pre { background: #020617; border: 1px solid var(--border); padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 12px; color: #a5f3fc; }
  </style>
</head>
<body>

<div id="loginView" class="login-box">
  <h2 style="margin-top:0">SOFIA SUNAT Gateway</h2>
  <p style="color:var(--muted);font-size:13px">Caja Negra Multi-App · <code>gateway.sofiaerp.com</code></p>
  <div style="margin-bottom:12px">
    <label>Correo Administrador</label>
    <input id="loginEmail" type="email" value="admin@sofiaerp.com" />
  </div>
  <div style="margin-bottom:16px">
    <label>Contraseña</label>
    <input id="loginPass" type="password" placeholder="Contraseña" />
  </div>
  <button class="btn" style="width:100%" onclick="doLogin()">Ingresar al Panel</button>
  <p id="loginErr" style="color:#f87171;font-size:12px;margin-top:10px"></p>
</div>

<div id="appView" class="hidden">
  <header>
    <div class="brand">
      <span>SOFIA SUNAT Gateway</span>
      <span class="badge b-info">gateway.sofiaerp.com</span>
    </div>
    <div class="sunat-pill">
      <span id="sunatBetaStatus" class="badge b-warn">SUNAT Beta: ...</span>
      <span id="sunatProdStatus" class="badge b-warn">SUNAT Prod: ...</span>
      <button class="btn btn-sm btn-sec" onclick="refreshAll()">Actualizar</button>
      <button class="btn btn-sm btn-sec" onclick="logout()">Salir</button>
    </div>
  </header>

  <div class="container">
    <div class="tabs">
      <button class="tab active" onclick="showTab('dashboard', this)">Dashboard y Bandeja</button>
      <button class="tab" onclick="showTab('issuers', this)">Empresas Emisoras (RUCs)</button>
      <button class="tab" onclick="showTab('clients', this)">Apps y API Keys</button>
      <button class="tab" onclick="showTab('tester', this)">Probador Rápido (Beta)</button>
    </div>

    <!-- TAB 1: DASHBOARD Y BANDEJA -->
    <div id="tab-dashboard">
      <div class="grid4">
        <div class="kpi"><div class="lbl">Comprobantes Totales</div><div class="val" id="kTotal">0</div></div>
        <div class="kpi"><div class="lbl">Aceptados SUNAT</div><div class="val" style="color:var(--ok)" id="kAccepted">0</div></div>
        <div class="kpi"><div class="lbl">En Cola / Reintento</div><div class="val" style="color:var(--warn)" id="kQueued">0</div></div>
        <div class="kpi"><div class="lbl">Rechazados / Alerta</div><div class="val" style="color:var(--err)" id="kRejected">0</div></div>
      </div>

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

    <!-- TAB 2: EMPRESAS EMISORAS -->
    <div id="tab-issuers" class="hidden">
      <div class="card">
        <h3>Registrar / Actualizar Empresa Emisora (RUC)</h3>
        <div class="form-grid">
          <div><label>RUC (11 dígitos)</label><input id="issRuc" maxlength="11" placeholder="20600994345" /></div>
          <div><label>Razón Social</label><input id="issName" placeholder="MI EMPRESA S.A.C." /></div>
          <div><label>Dirección Fiscal</label><input id="issAddr" placeholder="Av. Javier Prado 123" /></div>
          <div><label>Ubigeo (6 dígitos)</label><input id="issUbigeo" value="150101" maxlength="6" /></div>
          <div>
            <label>Entorno SUNAT</label>
            <select id="issBeta">
              <option value="true">Modo Pruebas (SUNAT Beta + Demo PFX)</option>
              <option value="false">Producción Real SUNAT</option>
            </select>
          </div>
          <div>
            <label>Política de Envío</label>
            <select id="issPolicy">
              <option value="INSTANT_WITH_RETRY">Inmediato + Reintentos Automáticos</option>
              <option value="SCHEDULED_NIGHT">Ventana Nocturna (01:00 - 05:00 AM)</option>
              <option value="HYBRID_BOLETA_SUMMARY">Híbrido (Facturas inmediato / Boletas resumen)</option>
            </select>
          </div>
          <div><label>Usuario SOL (vacío = MODDATOS en Beta)</label><input id="issSolUser" placeholder="MODDATOS o UsuarioSOL" /></div>
          <div><label>Clave SOL</label><input id="issSolPass" type="password" placeholder="Clave SOL" /></div>
          <div><label>Certificado .pfx (opcional en Beta)</label><input id="issPfxFile" type="file" accept=".pfx,.p12" /></div>
          <div><label>Contraseña .pfx</label><input id="issPfxPass" type="password" placeholder="Contraseña .pfx" /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="saveIssuer()">Guardar Empresa Emisora</button>
          <span id="issMsg" style="margin-left:12px;font-size:12px"></span>
        </div>
      </div>

      <div class="card">
        <h3>Empresas Registradas</h3>
        <div style="overflow-x:auto">
          <table>
            <thead>
              <tr><th>RUC</th><th>Razón Social</th><th>Entorno</th><th>Política</th><th>Certificado</th><th>Vence en</th></tr>
            </thead>
            <tbody id="issuersTable"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: APPS Y API KEYS -->
    <div id="tab-clients" class="hidden">
      <div class="card">
        <h3>Crear Aplicación Cliente (SOFIA ERP, POS, Ecommerce)</h3>
        <div class="form-grid">
          <div><label>Nombre de la App</label><input id="cliName" placeholder="SOFIA ERP Producción" /></div>
          <div><label>Descripción</label><input id="cliDesc" placeholder="Conexión principal Odoo 20" /></div>
          <div><label>Webhook URL (opcional)</label><input id="cliWebhook" placeholder="https://tu-app.com/webhooks/sunat" /></div>
          <div><label>Webhook Secret HMAC (opcional)</label><input id="cliSecret" placeholder="whsec_..." /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="createClient()">Generar API Key</button>
        </div>
        <div id="newKeyBox" class="hidden" style="margin-top:14px">
          <pre id="newKeyText"></pre>
        </div>
      </div>

      <div class="card">
        <h3>Aplicaciones Conectadas</h3>
        <table>
          <thead><tr><th>Nombre</th><th>Prefijo Key</th><th>Webhook</th><th>Último Uso</th><th>Estado</th><th>Acción</th></tr></thead>
          <tbody id="clientsTable"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: PROBADOR RÁPIDO -->
    <div id="tab-tester" class="hidden">
      <div class="card">
        <h3>Emitir Comprobante de Prueba (Firma Instantánea + Cola SUNAT)</h3>
        <div class="form-grid">
          <div><label>RUC Emisor registrado</label><input id="tRuc" placeholder="20600994345" /></div>
          <div><label>Tipo</label><select id="tType"><option value="01">01 - Factura</option><option value="03">03 - Boleta</option></select></div>
          <div><label>Serie</label><input id="tSerie" value="FE01" /></div>
          <div><label>Correlativo</label><input id="tNum" value="1" /></div>
          <div><label>RUC/DNI Cliente</label><input id="tCustNum" value="20100047218" /></div>
          <div><label>Nombre Cliente</label><input id="tCustName" value="CLIENTE DE PRUEBA SAC" /></div>
        </div>
        <div style="margin-top:14px">
          <button class="btn" onclick="emitTestDoc()">Emitir Comprobante Ahora</button>
        </div>
        <pre id="testOutput" style="margin-top:14px">Aquí verás la respuesta instantánea (&lt;300ms) con Hash y QR...</pre>
      </div>
    </div>
  </div>
</div>

<script>
const API = "/api/v1";
let TOKEN = localStorage.getItem("gw_token") || "";

function authHeaders() {
  return { "Content-Type": "application/json", "Authorization": "Bearer " + TOKEN };
}

async function doLogin() {
  document.getElementById("loginErr").textContent = "";
  const r = await fetch(API + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.getElementById("loginEmail").value,
      password: document.getElementById("loginPass").value
    })
  });
  const data = await r.json();
  if (!r.ok) {
    document.getElementById("loginErr").textContent = data.detail || "Error de acceso";
    return;
  }
  TOKEN = data.access_token;
  localStorage.setItem("gw_token", TOKEN);
  initApp();
}

function logout() {
  localStorage.removeItem("gw_token");
  TOKEN = "";
  document.getElementById("appView").classList.add("hidden");
  document.getElementById("loginView").classList.remove("hidden");
}

function showTab(name, btn) {
  ["dashboard", "issuers", "clients", "tester"].forEach(t => {
    document.getElementById("tab-" + t).classList.toggle("hidden", t !== name);
  });
  document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

function badgeFor(st) {
  if (st === "ACCEPTED" || st === "ACCEPTED_WITH_OBS") return `<span class="badge b-ok">${st}</span>`;
  if (st === "REJECTED" || st === "EXPIRED_ALERT" || st === "VALIDATION_ERROR") return `<span class="badge b-err">${st}</span>`;
  return `<span class="badge b-warn">${st}</span>`;
}

async function loadSunatHealth() {
  try {
    const r = await fetch(API + "/health/sunat");
    const d = await r.json();
    const b = document.getElementById("sunatBetaStatus");
    const p = document.getElementById("sunatProdStatus");
    b.className = "badge " + (d.sunat_beta.online ? "b-ok" : "b-err");
    b.textContent = `SUNAT Beta: ${d.sunat_beta.online ? "OK" : "CAÍDO"} (${d.sunat_beta.latency_ms}ms)`;
    p.className = "badge " + (d.sunat_prod.online ? "b-ok" : "b-err");
    p.textContent = `SUNAT Prod: ${d.sunat_prod.online ? "OK" : "CAÍDO"} (${d.sunat_prod.latency_ms}ms)`;
  } catch (e) {}
}

async function loadStatsAndDocs() {
  const rs = await fetch(API + "/stats", { headers: authHeaders() });
  if (rs.status === 401) { logout(); return; }
  const s = await rs.json();
  document.getElementById("kTotal").textContent = s.total_documents;
  document.getElementById("kAccepted").textContent = `${s.accepted} (${s.acceptance_rate_pct}%)`;
  document.getElementById("kQueued").textContent = s.queued_or_retrying;
  document.getElementById("kRejected").textContent = s.rejected + s.at_risk_deadline;

  const rd = await fetch(API + "/documents?limit=50", { headers: authHeaders() });
  const docs = await rd.json();
  document.getElementById("docsTable").innerHTML = docs.map(d => `
    <tr>
      <td><code>${d.issuer_ruc}</code></td>
      <td><strong>${d.doc_type}</strong> · ${d.number}</td>
      <td>${d.issue_date}</td>
      <td>${d.currency} ${d.total_amount.toFixed(2)}</td>
      <td>${badgeFor(d.status)}</td>
      <td style="max-width:260px">${d.sunat_code || "-"} ${d.sunat_message ? "— " + d.sunat_message : ""}</td>
      <td>${d.attempt_count}</td>
      <td class="row-actions">
        <button class="btn btn-sm btn-sec" onclick="retryDoc('${d.id}')">Reintentar</button>
        <button class="btn btn-sm btn-sec" onclick="recoverCdr('${d.id}')">CDR 1033</button>
        <button class="btn btn-sm btn-sec" onclick="dlFile('${d.id}','xml')">XML</button>
        ${d.has_cdr ? `<button class="btn btn-sm" onclick="dlFile('${d.id}','cdr')">CDR</button>` : ""}
      </td>
    </tr>
  `).join("") || `<tr><td colspan="8" style="color:var(--muted)">Sin comprobantes aún.</td></tr>`;
}

async function dlFile(id, kind) {
  const r = await fetch(`${API}/documents/${id}/${kind}`, { headers: { "Authorization": "Bearer " + TOKEN } });
  if (!r.ok) { alert("Archivo no disponible"); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = kind === "cdr" ? `CDR-${id}.zip` : `XML-${id}.xml`;
  a.click();
}

async function retryDoc(id) {
  await fetch(`${API}/documents/${id}/retry`, { method: "POST", headers: authHeaders() });
  setTimeout(loadStatsAndDocs, 1500);
}

async function recoverCdr(id) {
  await fetch(`${API}/documents/${id}/recover-cdr`, { method: "POST", headers: authHeaders() });
  setTimeout(loadStatsAndDocs, 1500);
}

async function loadIssuers() {
  const r = await fetch(API + "/issuers", { headers: authHeaders() });
  const list = await r.json();
  document.getElementById("issuersTable").innerHTML = list.map(i => `
    <tr>
      <td><code>${i.ruc}</code></td>
      <td>${i.business_name}</td>
      <td>${i.is_beta ? '<span class="badge b-warn">BETA</span>' : '<span class="badge b-ok">PRODUCCIÓN</span>'}</td>
      <td><code>${i.dispatch_policy}</code></td>
      <td>${i.has_certificate ? (i.cert_is_demo ? '<span class="badge b-warn">Demo Beta</span>' : '<span class="badge b-ok">Oficial .pfx</span>') : '<span class="badge b-err">Falta</span>'}</td>
      <td>${i.cert_days_left !== null ? i.cert_days_left + " días" : "-"}</td>
    </tr>
  `).join("") || `<tr><td colspan="6" style="color:var(--muted)">No hay empresas registradas.</td></tr>`;
}

async function saveIssuer() {
  const msg = document.getElementById("issMsg");
  msg.textContent = "Guardando...";
  let pfxB64 = null;
  const f = document.getElementById("issPfxFile").files[0];
  if (f) {
    const buf = await f.arrayBuffer();
    pfxB64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
  }
  const isBeta = document.getElementById("issBeta").value === "true";
  const r = await fetch(API + "/issuers", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      ruc: document.getElementById("issRuc").value.trim(),
      business_name: document.getElementById("issName").value.trim(),
      address: document.getElementById("issAddr").value.trim(),
      ubigeo: document.getElementById("issUbigeo").value.trim() || "150101",
      is_beta: isBeta,
      dispatch_policy: document.getElementById("issPolicy").value,
      sol_username: document.getElementById("issSolUser").value.trim() || null,
      sol_password: document.getElementById("issSolPass").value.trim() || null,
      pfx_base64: pfxB64,
      pfx_password: document.getElementById("issPfxPass").value || null,
      generate_demo_cert: isBeta && !pfxB64
    })
  });
  const d = await r.json();
  if (!r.ok) { msg.style.color = "#f87171"; msg.textContent = d.detail || "Error"; return; }
  msg.style.color = "#34d399";
  msg.textContent = `Empresa ${d.ruc} guardada correctamente.`;
  loadIssuers();
}

async function loadClients() {
  const r = await fetch(API + "/clients", { headers: authHeaders() });
  const list = await r.json();
  document.getElementById("clientsTable").innerHTML = list.map(c => `
    <tr>
      <td><strong>${c.name}</strong></td>
      <td><code>${c.key_prefix}...</code></td>
      <td>${c.webhook_url || "-"}</td>
      <td>${c.last_used_at ? c.last_used_at.slice(0,19).replace("T"," ") : "Nunca"}</td>
      <td>${c.is_active ? '<span class="badge b-ok">Activa</span>' : '<span class="badge b-err">Revocada</span>'}</td>
      <td>${c.is_active ? `<button class="btn btn-sm btn-err" onclick="revokeClient('${c.id}')">Revocar</button>` : ""}</td>
    </tr>
  `).join("") || `<tr><td colspan="6" style="color:var(--muted)">Sin aplicaciones conectadas.</td></tr>`;
}

async function createClient() {
  const r = await fetch(API + "/clients", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      name: document.getElementById("cliName").value.trim(),
      description: document.getElementById("cliDesc").value.trim() || null,
      webhook_url: document.getElementById("cliWebhook").value.trim() || null,
      webhook_secret: document.getElementById("cliSecret").value.trim() || null
    })
  });
  const d = await r.json();
  if (!r.ok) { alert(d.detail || "Error"); return; }
  document.getElementById("newKeyBox").classList.remove("hidden");
  document.getElementById("newKeyText").textContent = `API KEY (copia ahora, no se volverá a mostrar):\n${d.api_key}`;
  loadClients();
}

async function revokeClient(id) {
  if (!confirm("¿Revocar esta API Key?")) return;
  await fetch(`${API}/clients/${id}`, { method: "DELETE", headers: authHeaders() });
  loadClients();
}

async function emitTestDoc() {
  const out = document.getElementById("testOutput");
  out.textContent = "Firmando localmente y encolando...";
  const today = new Date().toISOString().slice(0, 10);
  const dtype = document.getElementById("tType").value;
  const r = await fetch(API + "/documents/emit", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      issuer_ruc: document.getElementById("tRuc").value.trim(),
      doc_type: dtype,
      serie: document.getElementById("tSerie").value.trim(),
      correlativo: document.getElementById("tNum").value.trim(),
      issue_date: today,
      currency: "PEN",
      customer: {
        doc_type: dtype === "01" ? "6" : "1",
        doc_number: document.getElementById("tCustNum").value.trim(),
        name: document.getElementById("tCustName").value.trim()
      },
      items: [{
        code: "SRV-001",
        description: "Servicio de prueba SOFIA SUNAT Gateway",
        unit_code: "ZZ",
        quantity: 1,
        unit_price_without_tax: 100.00,
        igv_affectation_code: "10",
        igv_rate: 0.18
      }]
    })
  });
  const d = await r.json();
  out.textContent = JSON.stringify(d, null, 2);
  setTimeout(loadStatsAndDocs, 2000);
}

function refreshAll() {
  loadSunatHealth();
  loadStatsAndDocs();
  loadIssuers();
  loadClients();
}

function initApp() {
  document.getElementById("loginView").classList.add("hidden");
  document.getElementById("appView").classList.remove("hidden");
  refreshAll();
}

if (TOKEN) initApp();
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def gateway_panel():
    return HTMLResponse(content=PANEL_HTML)
