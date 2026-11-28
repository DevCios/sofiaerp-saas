# -*- coding: utf-8 -*-
"""
Portal de Documentación Interactiva estilo heyo-docs para API SUNAT (/docs-portal).
Sigue el Design System oficial SOFIA / Odoo 20 y carga dinámicamente /openapi-ai.json.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

DOCS_PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Documentación — API SUNAT API &amp; MCP</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <style>
    :root {
      --o20-navbar: #66598F;
      --o20-primary: #714B67;
      --o20-teal: #017E84;
      --bg: #F6F7F9;
      --card: #FFFFFF;
      --border: #E2E5EC;
      --text: #1F2937;
      --muted: #6B7280;
    }
    * { box-sizing: border-box; }
    body { margin:0; font-family:'Inter', system-ui, sans-serif; background:var(--bg); color:var(--text); -webkit-font-smoothing:antialiased; }
    header { background:var(--o20-navbar); color:#FFFFFF; position:sticky; top:0; z-index:40; box-shadow:0 1px 3px rgba(17,24,39,.14); }
    .nav { max-width:1320px; margin:0 auto; padding:0 24px; min-height:56px; display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
    .brand { display:flex; align-items:center; gap:10px; font-weight:700; font-size:15px; color:#FFFFFF; text-decoration:none; }
    .brand-mark { width:30px; height:30px; border-radius:8px; background:rgba(255,255,255,.20); display:inline-flex; align-items:center; justify-content:center; font-weight:800; }
    .nav-tabs { display:flex; gap:6px; }
    .nav-tab { background:transparent; border:none; color:rgba(255,255,255,.82); padding:7px 14px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; }
    .nav-tab.active, .nav-tab:hover { background:rgba(255,255,255,.18); color:#FFFFFF; }
    .btn-link { background:#FFFFFF; color:var(--o20-primary); padding:6px 12px; border-radius:6px; font-size:12.5px; font-weight:700; text-decoration:none; }

    .layout { max-width:1320px; margin:0 auto; display:grid; grid-template-columns:240px 1fr; gap:24px; padding:24px; }
    @media (max-width: 900px) { .layout { grid-template-columns:1fr; } .sidebar { display:none; } }
    .sidebar { position:sticky; top:76px; align-self:start; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; }
    .side-group { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:14px 0 6px 8px; }
    .side-group:first-child { margin-top:0; }
    .side-link { display:block; padding:7px 10px; border-radius:7px; color:#374151; text-decoration:none; font-size:13px; font-weight:500; }
    .side-link:hover { background:#F4F1FB; color:var(--o20-primary); }

    .content { min-width:0; }
    .doc-card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:26px 28px; margin-bottom:20px; box-shadow:0 1px 2px rgba(16,24,40,.03); }
    h1 { margin:0 0 8px 0; font-size:24px; letter-spacing:-0.02em; }
    h2 { margin:22px 0 8px 0; font-size:17px; color:var(--o20-primary); }
    p, li { font-size:14px; line-height:1.65; color:#374151; }
    code { background:#F3F4F6; color:#374151; padding:2px 6px; border-radius:5px; font-size:12.5px; }
    pre { background:#1F2937; color:#E5E7EB; padding:15px 16px; border-radius:10px; overflow-x:auto; font-size:12.5px; line-height:1.55; position:relative; }
    .badge { display:inline-block; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700; }
    .b-get { background:#D9F2EE; color:#0F766E; }
    .b-post { background:#EAE6F8; color:#5B4B8A; }
    .ep-box { border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-bottom:12px; background:#FAFBFC; }
    .hidden { display:none !important; }
  </style>
</head>
<body>
  <header>
    <div class="nav">
      <a class="brand" href="/docs-portal">
        <span class="brand-mark">A</span>
        <span>API SUNAT <span style="opacity:.75;font-weight:400">· Docs</span></span>
      </a>
      <div class="nav-tabs">
        <button class="nav-tab active" onclick="switchDocTab('guide', this)">Guía</button>
        <button class="nav-tab" onclick="switchDocTab('examples', this)">Ejemplos &amp; MCP</button>
        <button class="nav-tab" onclick="switchDocTab('openapi', this)">Referencia API</button>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <a class="btn-link" href="/openapi-ai.json" target="_blank" style="background:rgba(255,255,255,.15);color:#FFFFFF">OpenAPI JSON</a>
        <a class="btn-link" href="/">Consola Gateway →</a>
      </div>
    </div>
  </header>

  <div class="layout">
    <aside class="sidebar">
      <div class="side-group">Primeros pasos</div>
      <a class="side-link" href="#intro" onclick="switchDocTab('guide')">Qué es API SUNAT</a>
      <a class="side-link" href="#auth" onclick="switchDocTab('guide')">Autenticación (API Key &amp; OAuth 2.1)</a>
      <a class="side-link" href="#conventions" onclick="switchDocTab('guide')">Convenciones SUNAT</a>
      <div class="side-group">Asistentes de IA</div>
      <a class="side-link" href="#mcp-claude" onclick="switchDocTab('examples')">Claude &amp; Cursor (MCP)</a>
      <a class="side-link" href="#chatgpt" onclick="switchDocTab('examples')">ChatGPT Actions / OAuth</a>
      <a class="side-link" href="#curl" onclick="switchDocTab('examples')">Ejemplo cURL &amp; Python</a>
      <div class="side-group">Referencia</div>
      <a class="side-link" href="#ref-api" onclick="switchDocTab('openapi')">Endpoints OpenAPI 3.1</a>
    </aside>

    <main class="content">
      <!-- TAB GUIA -->
      <section id="sec-guide">
        <div class="doc-card" id="intro">
          <span class="badge b-post" style="margin-bottom:10px">UBL 2.1 · XMLDSig · Anti-1033 · Remote MCP</span>
          <h1>Documentación de API SUNAT</h1>
          <p>
            <strong>API SUNAT</strong> es una pasarela resiliente de facturación electrónica para Perú (SUNAT).
            Recibe JSON limpio, valida reglas fiscales antes del envío, genera XML UBL 2.1, firma digitalmente con certificado <code>.pfx</code> en Bóveda Fernet
            y gestiona colas de reintentos automáticos y recuperación de CDR ante errores <code>1033</code>.
          </p>
          <h2 id="auth">Autenticación</h2>
          <ul>
            <li><strong>API Key aislada por RUC:</strong> envía <code>Authorization: Bearer sk_live_...</code> o <code>X-API-Key: sk_live_...</code>.</li>
            <li><strong>OAuth 2.1 + PKCE (S256):</strong> soportado nativamente en <code>/.well-known/oauth-authorization-server</code> y <code>/oauth/register</code> para conexión 1-clic en <strong>Claude.ai</strong> y <strong>ChatGPT Connectors</strong>.</li>
          </ul>
          <h2 id="conventions">Convenciones SUNAT</h2>
          <ul>
            <li>Las fechas usan formato <code>YYYY-MM-DD</code> en zona horaria <code>America/Lima</code>.</li>
            <li>Los códigos SUNAT se envían como texto: <code>"01"</code> (Factura), <code>"03"</code> (Boleta), <code>"10"</code> (Gravado IGV), <code>"NIU"</code> (Unidad).</li>
            <li><strong>Idempotencia estricta:</strong> reenviar el mismo <code>(issuer_ruc, doc_type, serie, correlativo)</code> nunca duplica el comprobante; retorna <code>idempotent_replay: true</code>.</li>
            <li><strong>Plazo legal SUNAT:</strong> 3 días calendario para Facturas/Notas y 7 días para Boletas.</li>
          </ul>
        </div>
      </section>

      <!-- TAB EJEMPLOS & MCP -->
      <section id="sec-examples" class="hidden">
        <div class="doc-card" id="mcp-claude">
          <h1>Conectar Claude, ChatGPT y Cursor (MCP)</h1>
          <p>API SUNAT expone un servidor <strong>Remote MCP (Streamable HTTP)</strong> en <code>https://apisunat.pro/mcp</code> con 6 herramientas fiscales.</p>
          <h2>1. Claude Code (1 comando)</h2>
          <pre>claude mcp add --transport http sofia-sunat https://apisunat.pro/mcp \
  --header "Authorization: Bearer sk_live_TU_API_KEY"</pre>
          <h2 id="chatgpt">2. ChatGPT (Connectors OAuth 2.1 o Custom GPT Actions)</h2>
          <pre>Remote MCP URL:   https://apisunat.pro/mcp
OAuth Discovery:  https://apisunat.pro/.well-known/oauth-authorization-server
OpenAPI AI URL:   https://apisunat.pro/openapi-ai.json</pre>
          <h2 id="curl">3. Emitir Factura vía cURL</h2>
          <pre>curl -X POST https://apisunat.pro/api/v1/documents/emit \
  -H "Authorization: Bearer sk_live_TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "issuer_ruc": "20600994345",
    "doc_type": "01",
    "serie": "FE01",
    "correlativo": "1",
    "issue_date": "2026-11-27",
    "currency": "PEN",
    "customer": {"doc_type": "6", "doc_number": "20100047218", "name": "CLIENTE DEMO S.A.C."},
    "items": [{"description": "Suscripción SOFIA ERP", "quantity": 1, "unit_price_without_tax": 100.00}]
  }'</pre>
        </div>
      </section>

      <!-- TAB REFERENCIA OPENAPI -->
      <section id="sec-openapi" class="hidden">
        <div class="doc-card" id="ref-api">
          <h1>Referencia OpenAPI 3.1</h1>
          <p>Cargada en tiempo real desde <code>/openapi-ai.json</code>.</p>
          <div id="openapiList">Cargando especificación...</div>
        </div>
      </section>
    </main>
  </div>

<script>
function switchDocTab(name, btn) {
  ['guide', 'examples', 'openapi'].forEach(t => {
    document.getElementById('sec-' + t).classList.toggle('hidden', t !== name);
  });
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  if (name === 'openapi') loadOpenApi();
}

let OPENAPI_LOADED = false;
async function loadOpenApi() {
  if (OPENAPI_LOADED) return;
  try {
    const spec = await fetch('/openapi-ai.json').then(r => r.json());
    const box = document.getElementById('openapiList');
    const html = [];
    for (const [path, methods] of Object.entries(spec.paths || {})) {
      for (const [verb, meta] of Object.entries(methods)) {
        const cls = verb.toLowerCase() === 'get' ? 'b-get' : 'b-post';
        html.push(`
          <div class="ep-box">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <span class="badge ${cls}">${verb.toUpperCase()}</span>
              <code style="font-weight:700">${path}</code>
              <span style="font-size:12px;color:#6B7280">${meta.operationId || ''}</span>
            </div>
            <p style="margin:8px 0 0 0;font-size:13px">${meta.summary || ''}</p>
          </div>
        `);
      }
    }
    box.innerHTML = html.join('');
    OPENAPI_LOADED = true;
  } catch (e) {
    document.getElementById('openapiList').textContent = 'Error cargando /openapi-ai.json: ' + e.message;
  }
}
</script>
</body>
</html>
"""


@router.get("/docs-portal", response_class=HTMLResponse, include_in_schema=False)
async def docs_portal():
    return HTMLResponse(content=DOCS_PORTAL_HTML)
