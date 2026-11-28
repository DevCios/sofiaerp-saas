# -*- coding: utf-8 -*-
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PANEL_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>API SUNAT — Pasarela Resiliente SUNAT</title>
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

    /* === LAYOUT DEVELOPER CONSOLE (ESTRUCTURA SIDEBAR + PALETA OFICIAL ODOO 20) === */
    .console-shell { display: flex; min-height: 100vh; background: var(--bg); }
    .sidebar {
      width: 244px; min-width: 244px; background: #FAFAFC; border-right: 1px solid var(--border);
      display: flex; flex-direction: column; justify-content: space-between;
      position: sticky; top: 0; height: 100vh; overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none;
      z-index: 35; transition: margin-left .2s ease;
    }
    .sidebar::-webkit-scrollbar { display: none; }
    .sidebar.collapsed { margin-left: -244px; }
    .sb-top { padding: 12px 12px 8px 12px; }
    .sb-brand { display: flex; align-items: center; gap: 9px; padding: 2px 6px 10px 6px; font-weight: 700; font-size: 15px; color: var(--text); letter-spacing: -0.01em; }
    .sb-brand-mark { width: 28px; height: 28px; border-radius: 7px; background: var(--o20-primary); color: #FFFFFF; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }
    .sb-ws-wrap { position: relative; margin-bottom: 8px; }
    .sb-ws-box {
      width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 8px;
      background: #FFFFFF; border: 1px solid var(--border); border-radius: 9px;
      padding: 6px 10px; font-size: 12.5px; font-weight: 600; color: var(--text); cursor: pointer;
    }
    .sb-ws-box:hover { border-color: var(--o20-primary); }
    .sb-ws-menu {
      position: absolute; left: 0; right: 0; top: calc(100% + 4px); background: #FFFFFF;
      border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 12px 28px rgba(15,23,42,.14);
      padding: 6px; z-index: 50;
    }
    .sb-ws-opt {
      width: 100%; border: none; background: transparent; border-radius: 7px; padding: 7px 8px;
      display: flex; align-items: center; justify-content: space-between; gap: 6px;
      font-size: 12.5px; color: var(--text); cursor: pointer; text-align: left;
    }
    .sb-ws-opt:hover { background: #F4F1FB; color: var(--o20-primary); }
    .sb-ws-divider { height: 1px; background: var(--border); margin: 5px 0; }
    .sb-ws-avatar { width: 22px; height: 22px; border-radius: 6px; background: var(--o20-primary-soft); color: var(--o20-primary); display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; flex-shrink: 0; }
    .sb-env-toggle {
      display: grid; grid-template-columns: 1fr 1fr; gap: 4px; background: #EFEFF4;
      padding: 3px; border-radius: 9px; margin-bottom: 10px;
    }
    .sb-env-btn {
      border: none; background: transparent; padding: 5px 8px; border-radius: 7px;
      font-size: 12px; font-weight: 600; color: #6B7280; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 5px;
    }
    .sb-env-btn.active { background: #FFFFFF; color: var(--text); box-shadow: 0 1px 2px rgba(16,24,40,.08); }
    .sb-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
    .sb-dot-prod { background: var(--o20-teal); }
    .sb-dot-beta { background: var(--warn); }

    .sb-group-lbl { font-size: 11px; font-weight: 600; color: #9CA3AF; padding: 8px 10px 3px 10px; }
    .sb-item {
      width: 100%; background: transparent; border: none; border-radius: 8px;
      padding: 6px 10px; margin-bottom: 1px; cursor: pointer;
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      color: #4B5563; font-size: 13px; font-weight: 500; text-align: left; text-decoration: none;
      transition: background .14s, color .14s;
    }
    .role-card {
      border: 1.5px solid var(--border); border-radius: 10px; padding: 14px; cursor: pointer;
      background: #FFFFFF; transition: border-color .15s, box-shadow .15s;
    }
    .role-card.active { border-color: var(--o20-primary); background: #FAF8FD; box-shadow: 0 0 0 3px rgba(113,75,103,.12); }
    .role-perm { font-size: 12px; margin: 5px 0; display: flex; align-items: center; gap: 6px; color: #374151; }
    .role-perm.denied { color: #9CA3AF; }

    /* Tarjetas de Planes Premium Estilo Acanalado Odoo 20 */
    .plan-card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 16px; padding: 10px; display: flex; flex-direction: column; box-shadow: 0 2px 10px rgba(15,23,42,.03); }
    .plan-card.plan-current { border: 2px solid var(--o20-primary); }
    .plan-head { border-radius: 12px; padding: 18px 16px 20px 16px; min-height: 126px; display: flex; flex-direction: column; justify-content: space-between; }
    .plan-head-light { background: #F9FAFB; border: 1px solid #EEF0F4; color: var(--text); }
    .plan-head-dark {
      background-color: #16111F;
      background-image:
        linear-gradient(90deg, #16111F 0%, rgba(102,89,143,.45) 58%, rgba(113,75,103,.75) 100%),
        repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0px, rgba(255,255,255,.06) 2px, rgba(1,126,132,.08) 2px, rgba(0,0,0,.28) 16px);
      color: #FFFFFF;
    }
    .plan-head-teal {
      background-color: #121C22;
      background-image:
        linear-gradient(90deg, #121C22 0%, rgba(1,126,132,.50) 60%, rgba(113,75,103,.72) 100%),
        repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0px, rgba(255,255,255,.06) 2px, rgba(1,126,132,.10) 2px, rgba(0,0,0,.28) 16px);
      color: #FFFFFF;
    }
    .plan-price { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
    .plan-price small { font-size: 12.5px; font-weight: 500; opacity: .78; }
    .plan-body { padding: 14px 8px 6px 8px; flex: 1; display: flex; flex-direction: column; }
    .plan-feat { font-size: 12.5px; color: #4B5563; padding: 8px 0; border-bottom: 1px solid #F3F4F6; }
    .plan-feat:last-child { border-bottom: none; }
    .cycle-toggle { display: inline-flex; background: #EFEFF4; padding: 3px; border-radius: 9px; gap: 3px; }
    .cycle-btn { border: none; background: transparent; padding: 5px 12px; border-radius: 7px; font-size: 12px; font-weight: 600; color: #6B7280; cursor: pointer; }
    .cycle-btn.active { background: #FFFFFF; color: var(--text); box-shadow: 0 1px 2px rgba(16,24,40,.08); }

    /* Formulario Datos de Facturación (2 columnas limpias) */
    .bf-row { display: grid; grid-template-columns: 260px 1fr; gap: 16px; align-items: center; padding: 14px 0; border-bottom: 1px solid #F1F3F6; }
    .bf-row:last-child { border-bottom: none; }
    @media (max-width: 780px) { .bf-row { grid-template-columns: 1fr; gap: 6px; } }
    .sb-item:hover { background: #EFEFF5; color: var(--text); }
    .sb-item.active { background: var(--o20-primary-soft); color: var(--o20-primary); font-weight: 600; }
    .sb-item-left { display: inline-flex; align-items: center; gap: 9px; min-width: 0; }
    .sb-item svg { width: 15px; height: 15px; flex-shrink: 0; opacity: .82; }
    .sb-item.active svg { opacity: 1; color: var(--o20-primary); }

    .sb-bottom { padding: 10px 12px; border-top: 1px solid var(--border); background: #FAFAFC; }
    .sb-upgrade-btn {
      width: 100%; border: none; border-radius: 9px; padding: 9px 12px; cursor: pointer;
      background: linear-gradient(135deg, #241930 0%, #66598F 58%, #714B67 100%);
      color: #FFFFFF; font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;
      margin-bottom: 6px; box-shadow: 0 3px 10px rgba(102,89,143,.22); transition: filter .15s;
    }
    .sb-upgrade-btn:hover { filter: brightness(1.08); }
    .sub-pills { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
    .sub-pill { background: #FFFFFF; border: 1px solid var(--border); color: #4B5563; padding: 6px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
    .sub-pill:hover { background: #F4F1FB; color: var(--o20-primary); }
    .sub-pill.active { background: var(--o20-primary); border-color: var(--o20-primary); color: #FFFFFF; }

    .console-right { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .topbar {
      min-height: 54px; background: #FFFFFF; border-bottom: 1px solid var(--border);
      padding: 0 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px;
      position: sticky; top: 0; z-index: 25; flex-wrap: nowrap;
    }
    .topbar-left { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .topbar-left strong { color: var(--text); font-weight: 600; white-space: nowrap; }
    .topbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; flex-shrink: 0; }
    .tb-status-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }
    .tb-icon-btn { background: transparent; border: 1px solid transparent; color: #4B5563; width: 30px; height: 30px; border-radius: 7px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
    .tb-icon-btn:hover { background: #F3F4F6; border-color: var(--border); }
    .tb-search {
      display: inline-flex; align-items: center; gap: 8px; background: #F9FAFB; border: 1px solid var(--border);
      border-radius: 8px; padding: 5px 10px; color: var(--muted); font-size: 12.5px; cursor: pointer;
    }
    .tb-search:hover { border-color: #CBD5E1; color: var(--text); }
    .tb-kbd { background: #FFFFFF; border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; font-size: 10.5px; font-weight: 600; color: #6B7280; }
    .tb-avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--o20-navbar); color: #FFFFFF; font-weight: 700; font-size: 12px; display: inline-flex; align-items: center; justify-content: center; }

    .console-main { max-width: 1120px; width: 100%; margin: 0 auto; padding: 28px 32px 44px 32px; }
    @media (max-width: 900px) {
      .sidebar { position: fixed; left: 0; top: 0; bottom: 0; box-shadow: 0 12px 32px rgba(0,0,0,.18); }
      .console-main { padding: 18px 16px 32px 16px; }
    }

    /* Banner Hero Oscuro Acanalado en Paleta Odoo 20 (Morado #66598F / #714B67 + Teal #017E84) */
    .ai-hero-ribbed {
      position: relative; overflow: hidden; border-radius: 16px; padding: 28px 30px; margin-bottom: 24px;
      background-color: #16111F;
      background-image:
        linear-gradient(90deg, #16111F 0%, #1C1528 38%, rgba(102,89,143,0.42) 72%, rgba(113,75,103,0.68) 100%),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.06) 0px, rgba(255,255,255,0.06) 2px, rgba(1,126,132,0.08) 2px, rgba(0,0,0,0.28) 18px);
      color: #FFFFFF; box-shadow: 0 10px 28px rgba(36,25,48,.16);
    }
    .ai-hero-badges { display: flex; gap: 8px; margin-bottom: 18px; }
    .ai-hero-badge { width: 34px; height: 34px; border-radius: 9px; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 15px; }
    .ai-hero-row { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; }
    .ai-hero-ribbed h2 { margin: 0 0 8px 0; font-size: 24px; font-weight: 700; letter-spacing: -0.02em; color: #FFFFFF; line-height: 1.2; }
    .ai-hero-ribbed p { margin: 0; font-size: 13.5px; color: rgba(255,255,255,.78); max-width: 520px; line-height: 1.5; }
    .ai-hero-cta { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
    .ai-hero-link { color: rgba(255,255,255,.92); font-size: 13px; font-weight: 600; text-decoration: none; }
    .ai-hero-link:hover { text-decoration: underline; }
    .ai-hero-btn { background: #FFFFFF; color: #1F2937; border: none; border-radius: 9px; padding: 9px 18px; font-weight: 700; font-size: 13px; cursor: pointer; }
    .ai-hero-btn:hover { background: #F3F4F6; }

    /* Command Palette Modal (Ctrl K) */
    .cmd-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,.45); z-index: 60; display: flex; align-items: flex-start; justify-content: center; padding-top: 12vh; }
    .cmd-box { width: 100%; max-width: 480px; background: #FFFFFF; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 20px 50px rgba(15,23,42,.22); overflow: hidden; }
    .cmd-input { border: none !important; border-bottom: 1px solid var(--border) !important; border-radius: 0 !important; padding: 14px 16px !important; font-size: 14px !important; box-shadow: none !important; }
    .cmd-list { max-height: 300px; overflow-y: auto; padding: 6px; }
    .cmd-row { width: 100%; border: none; background: transparent; padding: 9px 12px; border-radius: 7px; text-align: left; cursor: pointer; font-size: 13px; color: var(--text); display: flex; justify-content: space-between; }
    .cmd-row:hover { background: var(--o20-primary-soft); color: var(--o20-primary); }

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
    <div class="login-logo">A</div>
    <h2 style="margin:0 0 4px 0;text-align:center;color:var(--text)">API SUNAT</h2>
    <p style="color:var(--muted);font-size:12.5px;text-align:center;margin:0 0 18px 0">API &amp; Pasarela Resiliente SUNAT · Remote MCP</p>
    <div style="display:flex;gap:6px;background:#F3F4F6;padding:4px;border-radius:8px;margin-bottom:16px">
      <button id="btnModeLogin" class="btn btn-sm" style="flex:1" onclick="setAuthMode('login')">Iniciar Sesión</button>
      <button id="btnModeRegister" class="btn btn-sm btn-sec" style="flex:1;border:none;background:transparent" onclick="setAuthMode('register')">Crear Cuenta</button>
      <button id="btnModeSofia" class="btn btn-sm btn-sec" style="flex:1;border:none;background:transparent" onclick="setAuthMode('sofia')">SOFIA ERP</button>
    </div>

    <div id="formLogin">
      <div style="margin-bottom:12px">
        <label>Correo electrónico</label>
        <input id="loginEmail" type="email" placeholder="tu@empresa.com" />
      </div>
      <div style="margin-bottom:18px">
        <label>Contraseña</label>
        <input id="loginPass" type="password" placeholder="Contraseña" />
      </div>
      <button class="btn" style="width:100%;padding:10px" onclick="doLogin()">Ingresar a la Consola</button>
    </div>

    <div id="formSofia" class="hidden">
      <div style="background:#F4F1FB;border:1px solid #DED7F2;color:#5B4B8A;border-radius:8px;padding:9px 11px;font-size:12px;margin-bottom:12px">
        Ingresa con tu cuenta de <strong>sofiaerp.com</strong> (SSO verificado RS256 · cuota incluida).
      </div>
      <div style="margin-bottom:10px">
        <label>Correo de tu cuenta SOFIA ERP</label>
        <input id="sofiaEmail" type="email" placeholder="usuario@tuempresa.com" />
      </div>
      <div style="margin-bottom:10px">
        <label>Contraseña SOFIA ERP</label>
        <input id="sofiaPass" type="password" placeholder="••••••••" />
      </div>
      <div style="margin-bottom:16px">
        <label>Código MFA (solo si tienes 2FA activo)</label>
        <input id="sofiaMfa" type="text" placeholder="123456 (opcional)" maxlength="6" />
      </div>
      <button class="btn" style="width:100%;padding:10px;background:var(--o20-navbar)" onclick="doSofiaSso()">Ingresar con SOFIA ERP (SSO)</button>
    </div>

    <div id="formRegister" class="hidden">
      <div style="margin-bottom:10px">
        <label>Nombre completo</label>
        <input id="regName" type="text" placeholder="Ej. Luis Pérez" />
      </div>
      <div style="margin-bottom:10px">
        <label>Nombre de tu Workspace (opcional)</label>
        <input id="regWs" type="text" placeholder="Ej. Workspace de Luis" />
      </div>
      <div style="margin-bottom:10px">
        <label>Correo electrónico</label>
        <input id="regEmail" type="email" placeholder="luis@empresa.pe" />
      </div>
      <div style="margin-bottom:16px">
        <label>Contraseña (mín. 8 caracteres)</label>
        <input id="regPass" type="password" placeholder="••••••••" />
      </div>
      <button class="btn btn-teal" style="width:100%;padding:10px" onclick="doRegister()">Crear Workspace Gratis (50 ops/mes)</button>
    </div>

    <p id="loginErr" style="color:var(--err);font-size:12px;margin-top:10px;text-align:center"></p>
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);text-align:center;display:flex;justify-content:center;gap:14px;flex-wrap:wrap">
      <a href="/docs-portal" style="font-size:12.5px;font-weight:600;color:var(--o20-primary);text-decoration:none">Documentación API &amp; MCP</a>
      <a href="/consulta" style="font-size:12.5px;font-weight:600;color:var(--o20-teal);text-decoration:none">Consulta Pública →</a>
    </div>
  </div>
</div>

<div id="appView" class="hidden console-shell">
  <!-- SIDEBAR IZQUIERDO ESTILO DEVELOPER CONSOLE EN PALETA ODOO 20 -->
  <aside id="consoleSidebar" class="sidebar">
    <div class="sb-top">
      <div class="sb-brand">
        <span class="sb-brand-mark">A</span>
        <span>API SUNAT</span>
      </div>

      <div class="sb-ws-wrap">
        <button type="button" class="sb-ws-box" onclick="toggleWsMenu()">
          <div style="display:flex;align-items:center;gap:8px;min-width:0">
            <span id="sbWsAvatar" class="sb-ws-avatar">A</span>
            <span id="workspaceBadge" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">Cargando...</span>
          </div>
          <span style="color:#9CA3AF;font-size:11px">⇅</span>
        </button>
        <div id="wsMenu" class="sb-ws-menu hidden">
          <div id="wsMenuList"></div>
          <div class="sb-ws-divider"></div>
          <button type="button" class="sb-ws-opt" style="font-weight:600;color:var(--o20-primary)" onclick="openNewWsModal()"><span>+ Nuevo workspace</span></button>
          <button type="button" class="sb-ws-opt" style="color:var(--muted)" onclick="closeWsMenu();openTab('workspaces')"><span>Administrar workspaces</span></button>
        </div>
      </div>

      <div class="sb-env-toggle">
        <button id="envBtnBeta" class="sb-env-btn" onclick="setEnvHint('beta')"><span class="sb-dot sb-dot-beta"></span>Prueba</button>
        <button id="envBtnProd" class="sb-env-btn active" onclick="setEnvHint('prod')"><span class="sb-dot sb-dot-prod"></span>Producción</button>
      </div>

      <nav>
        <button class="sb-item tab active" data-tab="desk" onclick="showTab('desk', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>Inicio</span>
        </button>
        <button class="sb-item tab" data-tab="connectors" onclick="showTab('connectors', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>Conectores</span>
          <span class="badge b-info" style="font-size:10px;padding:1px 6px">IA</span>
        </button>
        <button class="sb-item tab" data-tab="issuers" onclick="showTab('issuers', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="13" y2="12"/></svg>Empresas</span>
        </button>
        <button class="sb-item tab" data-tab="documents" onclick="showTab('documents', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>Documentos</span>
        </button>

        <div class="sb-group-lbl">Desarrollador</div>
        <button class="sb-item tab" data-tab="lookup" onclick="showTab('lookup', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Consultas RUC/DNI/TC</span>
        </button>
        <button class="sb-item tab" data-tab="clients" onclick="showTab('clients', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>API Keys</span>
        </button>
        <button class="sb-item tab" data-tab="logs" onclick="showTab('logs', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>Logs</span>
        </button>

        <div class="sb-group-lbl">Workspace</div>
        <button class="sb-item tab" data-tab="billing" onclick="showTab('billing', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>Facturación</span>
        </button>
        <button class="sb-item tab" data-tab="team" onclick="showTab('team', this)">
          <span class="sb-item-left"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>Equipo</span>
        </button>
      </nav>
    </div>

    <div class="sb-bottom">
      <button class="sb-upgrade-btn" onclick="openTab('billing')">
        <span>↑</span><span>Mejorar plan</span>
      </button>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;padding:4px 4px 0 4px">
        <a href="/docs-portal" target="_blank" style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:#4B5563;text-decoration:none;font-weight:500">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>Documentación
        </a>
        <a href="/consulta" target="_blank" style="font-size:12px;color:var(--o20-teal);text-decoration:none;font-weight:600">Consulta CPE</a>
      </div>
    </div>
  </aside>

  <!-- CONTENIDO DERECHO: TOPBAR + AREA PRINCIPAL -->
  <div class="console-right">
    <div class="topbar">
      <div class="topbar-left">
        <button class="tb-icon-btn" onclick="toggleSidebar()" title="Mostrar / ocultar menú">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
        </button>
        <span>Consola API</span>
        <span>›</span>
        <strong id="topbarCrumb">Inicio</strong>
      </div>
      <div class="topbar-right">
        <span id="sunatBetaStatus" class="tb-status-pill b-info" title="Estado SUNAT Beta">Beta</span>
        <span id="sunatProdStatus" class="tb-status-pill b-ok" title="Estado SUNAT Producción">Prod</span>
        <select id="globalRucFilter" onchange="onRucFilterChange()" style="width:185px;padding:5px 8px;font-size:12px">
          <option value="">Todas las Empresas</option>
        </select>
        <span id="activeEnvBadge" class="hidden"></span>
        <button class="tb-search" onclick="openCmdModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <span>Buscar</span>
          <span class="tb-kbd">Ctrl K</span>
        </button>
        <button class="tb-icon-btn" onclick="refreshAll()" title="Actualizar">↻</button>
        <span id="userAvatar" class="tb-avatar" title="Usuario">A</span>
        <button class="tb-icon-btn" onclick="logout()" title="Cerrar sesión" style="width:auto;padding:0 8px;font-size:12px;font-weight:600">Salir</button>
      </div>
    </div>

    <main class="console-main">
      <!-- TAB 1: INICIO (ESTILO DEVELOPER CONSOLE + PALETA ODOO 20) -->
      <div id="tab-desk">
        <div style="margin-bottom:20px">
          <h1 id="heroGreeting" style="margin:0;font-size:24px;font-weight:700;letter-spacing:-0.02em;color:var(--text)">Buenas tardes</h1>
          <p id="heroSub" style="margin:4px 0 0 0;font-size:13.5px;color:var(--muted)">Facturación electrónica de SUNAT, dentro de tu asistente de IA y SOFIA ERP.</p>
        </div>

        <!-- Banner Hero Acanalado en Colores Odoo 20 -->
        <div class="ai-hero-ribbed">
          <div class="ai-hero-badges">
            <span class="ai-hero-badge" style="background:#714B67;color:#FFFFFF" title="Claude MCP">✦</span>
            <span class="ai-hero-badge" style="background:#FFFFFF;color:#017E84" title="ChatGPT / OpenAPI">◎</span>
          </div>
          <div class="ai-hero-row">
            <div>
              <h2>Conecta Claude o ChatGPT<br/>a API SUNAT</h2>
              <p>Emite facturas, boletas y guías, calcula IGV y consulta su estado en SUNAT directamente desde tu asistente de IA favorito.</p>
            </div>
            <div class="ai-hero-cta">
              <a href="/docs-portal" target="_blank" class="ai-hero-link">Ver documentación ↗</a>
              <button class="ai-hero-btn" onclick="openTab('connectors')">Conectar</button>
            </div>
          </div>
        </div>

        <!-- Medidor Visual de Cuota Mensual -->
        <div style="margin-bottom:26px">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px">
            <div>
              <span id="quotaHeadline" style="font-weight:700;font-size:15.5px;color:var(--text)">500 operaciones restantes</span>
              <span id="quotaPlanBadge" class="badge b-info" style="margin-left:8px">STARTER</span>
            </div>
            <button class="btn btn-sm btn-sec" onclick="openTab('billing')">↑ Mejorar plan</button>
          </div>
          <div id="quotaTicks" style="display:flex;gap:3px;height:18px;align-items:center;overflow:hidden"></div>
          <div id="quotaSub" style="font-size:12.5px;color:var(--muted);margin-top:8px">0 de 500 operaciones usadas este mes</div>
        </div>

        <!-- KPIs Pastel Oficiales Odoo 20 -->
        <div class="grid4">
          <div class="kpi kpi-purple" style="cursor:pointer" onclick="openTab('documents')">
            <div class="lbl">Comprobantes Totales</div>
            <div class="val" id="kTotal">0</div>
            <div class="sub">Procesados en pasarela</div>
          </div>
          <div class="kpi kpi-teal" style="cursor:pointer" onclick="openTab('documents')">
            <div class="lbl">Aceptados SUNAT</div>
            <div class="val" style="color:var(--ok)" id="kAccepted">0</div>
            <div class="sub" style="color:var(--ok)">Con CDR oficial</div>
          </div>
          <div class="kpi kpi-peach" style="cursor:pointer" onclick="openTab('contingencies')">
            <div class="lbl">En Cola / Contingencia</div>
            <div class="val" style="color:var(--warn)" id="kQueued">0</div>
            <div class="sub" style="color:var(--warn)">Reintento automático</div>
          </div>
          <div class="kpi kpi-rose" style="cursor:pointer" onclick="openTab('observations')">
            <div class="lbl">Observados / Rechazados</div>
            <div class="val" style="color:var(--err)" id="kRejected">0</div>
            <div class="sub" style="color:var(--err)">Requieren revisión</div>
          </div>
        </div>
      </div>

    <!-- SUB-BARRA DE DOCUMENTOS (Agrupa Comprobantes, Resúmenes, Contingencias, Observaciones y Probador) -->
    <div id="docsSubBar" class="sub-pills hidden">
      <button class="sub-pill" data-sub="documents" onclick="openTab('documents')">Comprobantes</button>
      <button class="sub-pill" data-sub="summaries" onclick="openTab('summaries')">Resúmenes (RC/RA)</button>
      <button class="sub-pill" data-sub="contingencies" onclick="openTab('contingencies')">Contingencias</button>
      <button class="sub-pill" data-sub="observations" onclick="openTab('observations')">Observaciones</button>
      <button class="sub-pill" data-sub="tester" onclick="openTab('tester')">Probador Beta</button>
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
              <option value="gateway_vault">Bóveda API SUNAT (subir .pfx o Demo Beta)</option>
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

    <!-- TAB 8: CONECTORES IA (DISEÑO HÍBRIDO LIMPIO + DESARROLLADORES) -->
    <div id="tab-connectors" class="hidden">
      <div style="margin-bottom:20px">
        <h2 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-0.02em">Conecta <span style="color:var(--muted);font-weight:500">tus agentes</span></h2>
        <p style="margin:4px 0 0 0;font-size:13.5px;color:var(--muted)">Conéctalo una vez y emite o consulta comprobantes SUNAT, RUC, DNI y Tipo de Cambio desde cualquier conversación.</p>
      </div>

      <!-- 2 Tarjetas Principales (Claude y ChatGPT) -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-bottom:16px">
        <div class="card" style="margin-bottom:0;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 20px">
          <div style="display:flex;align-items:center;gap:14px">
            <div style="width:42px;height:42px;border-radius:10px;background:#714B67;color:#FFFFFF;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;flex-shrink:0">✦</div>
            <div>
              <div style="font-weight:700;font-size:15px;color:var(--text)">Claude</div>
              <div style="font-size:12.5px;color:var(--muted)">Funciona con Claude.ai, Desktop y Claude Code (OAuth 2.1 / MCP).</div>
            </div>
          </div>
          <button class="btn btn-sec btn-sm" style="padding:7px 14px;white-space:nowrap" onclick="openConnectGuide('claude')">Conectar</button>
        </div>

        <div class="card" style="margin-bottom:0;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 20px">
          <div style="display:flex;align-items:center;gap:14px">
            <div style="width:42px;height:42px;border-radius:10px;background:#017E84;color:#FFFFFF;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;flex-shrink:0">◎</div>
            <div>
              <div style="font-weight:700;font-size:15px;color:var(--text)">ChatGPT</div>
              <div style="font-size:12.5px;color:var(--muted)">Conecta vía ChatGPT Connectors (MCP) o Custom GPT Actions.</div>
            </div>
          </div>
          <button class="btn btn-sec btn-sm" style="padding:7px 14px;white-space:nowrap" onclick="openConnectGuide('chatgpt')">Conectar</button>
        </div>
      </div>

      <!-- Acordeón para Desarrolladores (Cursor, Claude Code, n8n, OpenAPI, Probador) -->
      <div style="margin-bottom:24px">
        <button type="button" class="btn btn-sec btn-sm" style="background:transparent;border:none;padding:6px 4px;color:var(--text);font-weight:600;display:inline-flex;align-items:center;gap:6px" onclick="toggleDevMcpBox()">
          <span>Otro cliente MCP / Desarrolladores (Cursor, n8n, Probador)</span>
          <span id="devMcpChevron">⌄</span>
        </button>

        <div id="devMcpBox" class="hidden" style="margin-top:12px">
          <div class="card" style="background:#F4F1FB;border-color:#DED7F2">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
              <div>
                <h3 style="margin:0 0 4px 0;color:var(--o20-primary)">Endpoints Remote MCP &amp; OAuth 2.1 PKCE</h3>
                <div style="font-size:12.5px;color:#4B5563">
                  MCP URL: <code>https://apisunat.pro/mcp</code> · OpenAPI AI: <code>https://apisunat.pro/openapi-ai.json</code>
                </div>
              </div>
              <div class="row-actions">
                <button class="btn btn-sm" onclick="copyText('https://apisunat.pro/mcp', this)">Copiar URL MCP</button>
                <button class="btn btn-sm btn-sec" onclick="copyText('https://apisunat.pro/openapi-ai.json', this)">Copiar OpenAPI</button>
                <a href="/.well-known/oauth-authorization-server" target="_blank" class="btn btn-sm btn-sec" style="text-decoration:none">Discovery OAuth</a>
              </div>
            </div>
          </div>

          <div class="grid3">
            <div class="card">
              <h3>Claude Code (Terminal)</h3>
              <pre id="snippetClaude">claude mcp add --transport http api-sunat https://apisunat.pro/mcp \
  --header "Authorization: Bearer sk_live_TU_API_KEY"</pre>
              <button class="btn btn-sm btn-sec" onclick="copyText(document.getElementById('snippetClaude').textContent, this)">Copiar comando</button>
            </div>
            <div class="card">
              <h3>ChatGPT / n8n / Make</h3>
              <pre id="snippetChatGpt">MCP URL:     https://apisunat.pro/mcp
OpenAPI AI:  https://apisunat.pro/openapi-ai.json
Auth Header: Authorization: Bearer sk_live_TU_API_KEY</pre>
              <button class="btn btn-sm btn-sec" onclick="copyText(document.getElementById('snippetChatGpt').textContent, this)">Copiar configuración</button>
            </div>
            <div class="card">
              <h3>Cursor / VS Code (.cursor/mcp.json)</h3>
              <pre id="snippetCursor">{
  "mcpServers": {
    "api-sunat": {
      "url": "https://apisunat.pro/mcp",
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
            <h3>Probador en Vivo de <code>POST /mcp</code> (9 herramientas activas)</h3>
            <div class="row-actions" style="margin-bottom:12px">
              <button class="btn btn-teal btn-sm" onclick="testMcp('tools/list', {})">Probar tools/list</button>
              <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'calculate_totals_igv', arguments:{currency:'PEN', items:[{description:'Servicio Demo', quantity:1, unit_price_without_tax:100}]}})">Probar calculate_totals_igv</button>
              <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'get_exchange_rate', arguments:{}})">Probar get_exchange_rate</button>
              <button class="btn btn-sec btn-sm" onclick="testMcp('tools/call', {name:'explain_sunat_error', arguments:{sunat_code:'1033'}})">Probar explain_sunat_error</button>
            </div>
            <pre id="mcpTestOut" class="hidden"></pre>
          </div>
        </div>
      </div>

      <!-- Tabla: Conexiones de IA -->
      <div style="margin-bottom:10px">
        <h3 style="margin:0;font-size:16px;font-weight:700">Conexiones de IA</h3>
        <p style="margin:3px 0 0 0;font-size:12.5px;color:var(--muted)">Asistentes OAuth 2.1 y llaves API conectadas a este workspace. Puedes revocar cualquier acceso al instante.</p>
      </div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Aplicación</th>
              <th>Método</th>
              <th>Identificador</th>
              <th>Conectada</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody id="aiConnectionsTable"></tbody>
        </table>
      </div>
    </div>

    <!-- Modal Guiado Conectar Claude / ChatGPT -->
    <div id="connectGuideModal" class="cmd-backdrop hidden" onclick="if(event.target===this) closeConnectGuide()">
      <div class="cmd-box" style="max-width:480px;padding:22px 24px;border-radius:14px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <h3 id="cgTitle" style="margin:0;font-size:17px">Conectar Claude</h3>
          <button class="tb-icon-btn" onclick="closeConnectGuide()">✕</button>
        </div>
        <div id="cgBody" style="font-size:13px;color:#374151;line-height:1.6"></div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
          <button class="btn btn-sec btn-sm" onclick="closeConnectGuide()">Cerrar</button>
          <a id="cgExternalLink" href="https://claude.ai" target="_blank" class="btn btn-sm" style="text-decoration:none">Abrir asistente ↗</a>
        </div>
      </div>
    </div>

    <!-- TAB 9: LOGS API / MCP -->
    <div id="tab-logs" class="hidden">
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px">
          <h3 style="margin:0">Logs de Peticiones API &amp; Herramientas MCP</h3>
          <div style="display:flex;gap:8px;align-items:center">
            <select id="logSourceFilter" onchange="refreshScopedData()" style="width:auto;min-width:150px;padding:6px 10px">
              <option value="">Todos (REST + MCP)</option>
              <option value="MCP">Solo MCP (IA)</option>
              <option value="REST">Solo API REST</option>
            </select>
            <button class="btn btn-sm btn-sec" onclick="refreshScopedData()">Actualizar Logs</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Fecha (UTC)</th>
              <th>Origen</th>
              <th>Acción / Tool</th>
              <th>RUC</th>
              <th>Cliente</th>
              <th>Estado</th>
              <th>Latencia</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody id="logsTable"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 10: FACTURACIÓN Y PLANES (MERCADO PAGO + DATOS DE FACTURACIÓN) -->
    <div id="tab-billing" class="hidden">
      <div id="billingBanner" class="card hidden" style="background:#EBF8F6;border-color:#C4E8E2;color:#0F766E;font-weight:600"></div>

      <div class="sub-pills">
        <button id="billSubPlans" class="sub-pill active" onclick="switchBillingSub('plans')">Planes y Pagos</button>
        <button id="billSubProfile" class="sub-pill" onclick="switchBillingSub('profile')">Datos de facturación</button>
      </div>

      <!-- SUB-VISTA 1: PLANES Y PAGOS -->
      <div id="billingPlansPanel">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-bottom:16px;flex-wrap:wrap">
          <div>
            <h2 style="margin:0;font-size:20px;font-weight:700">Planes</h2>
            <p style="margin:4px 0 0 0;font-size:13px;color:var(--muted)">
              Todos los planes emiten directo en SUNAT. Pagos procesados con <strong>Mercado Pago (Yape, Plin, Tarjetas)</strong>.
            </p>
          </div>
          <div class="cycle-toggle">
            <button id="cycleBtnMonthly" class="cycle-btn active" onclick="setBillingCycle('monthly')">Mensual</button>
            <button id="cycleBtnYearly" class="cycle-btn" onclick="setBillingCycle('yearly')">Anual · 2 meses gratis</button>
          </div>
        </div>

        <div id="plansGrid" class="grid4" style="margin-bottom:22px"></div>

        <div class="card">
          <h3>Historial de Pagos y Upgrades (Mercado Pago)</h3>
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Plan</th>
                <th>Cuota Otorgada</th>
                <th>Monto (PEN)</th>
                <th>Estado</th>
                <th>ID Pago MP</th>
              </tr>
            </thead>
            <tbody id="ordersTable"></tbody>
          </table>
        </div>
      </div>

      <!-- SUB-VISTA 2: DATOS DE FACTURACIÓN (SUNAT AUTOCOMPLETE) -->
      <div id="billingProfilePanel" class="hidden">
        <div style="background:#EBF8F6;border:1px solid #C4E8E2;color:#0F766E;border-radius:10px;padding:11px 16px;font-size:12.5px;font-weight:500;margin-bottom:16px;display:flex;align-items:center;gap:8px">
          <span>🛡</span>
          <span>Guardaremos estos datos en <strong>API SUNAT</strong> para emitir automáticamente tu Boleta o Factura electrónica por tus pagos con <strong>Mercado Pago</strong>.</span>
        </div>

        <div class="card" style="padding:22px 26px">
          <h3 style="margin:0 0 2px 0;font-size:16px">Datos de facturación</h3>
          <p style="margin:0 0 12px 0;font-size:12.5px;color:var(--muted)">Aparecen en los comprobantes de tu suscripción.</p>

          <div class="bf-row">
            <div><strong style="font-size:13px">Tipo de comprobante <span style="color:var(--err)">*</span></strong></div>
            <div>
              <select id="bfDocType" onchange="onBillingDocTypeChange()">
                <option value="01">Factura</option>
                <option value="03">Boleta de Venta</option>
              </select>
            </div>
          </div>

          <div class="bf-row">
            <div>
              <strong style="font-size:13px">Documento de identidad <span style="color:var(--err)">*</span></strong>
              <div style="font-size:11.5px;color:var(--muted);margin-top:2px">Con RUC o DNI puedes completar los datos automáticamente desde SUNAT / RENIEC.</div>
            </div>
            <div style="display:flex;gap:8px">
              <select id="bfIdType" style="width:110px;flex-shrink:0">
                <option value="6">RUC</option>
                <option value="1">DNI</option>
              </select>
              <input id="bfIdNum" placeholder="20600994345" maxlength="11" />
              <button type="button" class="btn btn-sec btn-sm" style="white-space:nowrap;padding:0 14px" onclick="lookupBillingFiscalData()">SUNAT 🔍</button>
            </div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Razón social / Nombre <span style="color:var(--err)">*</span></strong></div>
            <div><input id="bfName" placeholder="Ej. Mi Empresa S.A.C." /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Dirección</strong></div>
            <div><input id="bfAddr" placeholder="Línea 1 (Av. / Calle / Número)" /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Dirección 2</strong></div>
            <div><input id="bfAddr2" placeholder="Departamento, oficina o interior" /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Ciudad</strong></div>
            <div><input id="bfCity" placeholder="Ej. Lima / Huancayo" /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Departamento / Estado</strong></div>
            <div><input id="bfDept" placeholder="Ej. Lima / Junín" /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Código postal</strong></div>
            <div><input id="bfZip" placeholder="Ej. 15001" /></div>
          </div>

          <div class="bf-row">
            <div><strong style="font-size:13px">Correo para comprobantes</strong></div>
            <div><input id="bfEmail" type="email" placeholder="contabilidad@empresa.pe" /></div>
          </div>

          <div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-top:18px">
            <span id="bfMsg" style="font-size:12.5px;color:var(--ok)"></span>
            <button class="btn" onclick="saveBillingProfile()">Guardar datos de facturación</button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 11: HUB DE CONSULTAS PERÚ (RUC / DNI / TIPO DE CAMBIO SUNAT) -->
    <div id="tab-lookup" class="hidden">
      <div class="grid3">
        <div class="card">
          <h3>Consulta RUC (SUNAT)</h3>
          <p style="font-size:12px;color:var(--muted);margin-top:0"><code>GET /api/v1/lookup/ruc/{ruc}</code> · Caché compartido 7 días.</p>
          <div style="display:flex;gap:8px">
            <input id="lkRuc" placeholder="20100047218" maxlength="11" />
            <button class="btn btn-sm" onclick="runLookup('ruc')">Consultar</button>
          </div>
          <pre id="lkRucOut" class="hidden" style="margin-top:10px"></pre>
        </div>
        <div class="card">
          <h3>Consulta DNI (RENIEC)</h3>
          <p style="font-size:12px;color:var(--muted);margin-top:0"><code>GET /api/v1/lookup/dni/{dni}</code> · Caché compartido 30 días.</p>
          <div style="display:flex;gap:8px">
            <input id="lkDni" placeholder="8 dígitos" maxlength="8" />
            <button class="btn btn-sm" onclick="runLookup('dni')">Consultar</button>
          </div>
          <pre id="lkDniOut" class="hidden" style="margin-top:10px"></pre>
        </div>
        <div class="card">
          <h3>Tipo de Cambio SUNAT (USD → PEN)</h3>
          <p style="font-size:12px;color:var(--muted);margin-top:0"><code>GET /api/v1/lookup/exchange-rate</code> · Cron diario 07:30 Lima.</p>
          <div style="display:flex;gap:8px">
            <input id="lkTcDate" type="date" />
            <button class="btn btn-sm btn-teal" onclick="runLookup('tc')">Consultar</button>
          </div>
          <pre id="lkTcOut" class="hidden" style="margin-top:10px"></pre>
        </div>
      </div>
    </div>

    <!-- TAB 12: WORKSPACES (MULTI-WORKSPACE) -->
    <div id="tab-workspaces" class="hidden">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap">
        <div>
          <h2 style="margin:0;font-size:21px;font-weight:700">Workspaces</h2>
          <p style="margin:4px 0 0 0;font-size:13px;color:var(--muted)">Cada workspace agrupa sus propios RUCs, API Keys, logs y plan de facturación.</p>
        </div>
        <button class="btn" onclick="openNewWsModal()">+ Nuevo workspace</button>
      </div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Nombre / Slug</th>
              <th>Origen</th>
              <th>Plan</th>
              <th>Cuota Mensual</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody id="workspacesTable"></tbody>
        </table>
      </div>
    </div>

    <!-- TAB 13: EQUIPO E INVITACIONES -->
    <div id="tab-team" class="hidden">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap">
        <div>
          <h2 style="margin:0;font-size:21px;font-weight:700">Equipo</h2>
          <p style="margin:4px 0 0 0;font-size:13px;color:var(--muted)">Invita y administra a las personas de tu workspace.</p>
        </div>
        <button id="btnOpenInvite" class="btn" onclick="openInviteModal()">+ Invitar miembro</button>
      </div>

      <div class="sub-pills">
        <button id="teamSubMembers" class="sub-pill active" onclick="switchTeamSub('members')">Miembros <span id="teamMemCount" class="badge b-info" style="margin-left:4px">1</span></button>
        <button id="teamSubInvites" class="sub-pill" onclick="switchTeamSub('invites')">Invitaciones <span id="teamInvCount" class="badge b-warn" style="margin-left:4px">0</span></button>
      </div>

      <div id="teamMembersPanel" class="card">
        <table>
          <thead>
            <tr>
              <th>Miembro</th>
              <th>Rol</th>
              <th>Se unió</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody id="teamMembersTable"></tbody>
        </table>
      </div>

      <div id="teamInvitesPanel" class="card hidden">
        <table>
          <thead>
            <tr>
              <th>Correo Invitado</th>
              <th>Rol</th>
              <th>Enlace de Invitación</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody id="teamInvitesTable"></tbody>
        </table>
      </div>
    </div>
    </main>
  </div>
</div>

<!-- Modal Invita a un miembro del equipo (Estilo Odoo 20) -->
<div id="inviteModal" class="cmd-backdrop hidden" onclick="if(event.target===this) closeInviteModal()">
  <div class="cmd-box" style="max-width:520px;border-radius:16px">
    <div style="height:86px;background-color:#16111F;background-image:linear-gradient(90deg,#16111F 0%,rgba(102,89,143,.5) 55%,rgba(113,75,103,.78) 100%),repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0px,rgba(255,255,255,.06) 2px,rgba(1,126,132,.08) 2px,rgba(0,0,0,.28) 16px);display:flex;align-items:center;justify-content:center">
      <div style="width:44px;height:44px;border-radius:11px;background:#714B67;color:#FFFFFF;font-weight:800;font-size:20px;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.35)">A</div>
    </div>
    <div style="padding:22px 24px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
        <h3 style="margin:0;font-size:18px;font-weight:700">Invita a un miembro del equipo</h3>
        <button class="tb-icon-btn" onclick="closeInviteModal()">✕</button>
      </div>
      <p style="margin:0 0 14px 0;font-size:12.5px;color:var(--muted)">Suma a alguien a tu workspace para trabajar con la API en conjunto.</p>
      <input id="invEmail" type="email" placeholder="Correo electrónico (ej. dev@empresa.pe)" style="margin-bottom:14px" />

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px">
        <div id="roleCardMember" class="role-card active" onclick="selectInviteRole('member')">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">
            <strong style="font-size:13.5px">Miembro</strong>
            <input type="radio" name="invRole" value="member" checked style="width:auto;accent-color:#714B67" />
          </div>
          <div style="font-size:11.5px;color:var(--muted);margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid var(--border)">Construye con la API</div>
          <div class="role-perm">✓ API keys y conectores</div>
          <div class="role-perm">✓ Documentos, logs y uso</div>
          <div class="role-perm denied">✕ Facturación</div>
          <div class="role-perm denied">✕ Gestión del equipo</div>
        </div>
        <div id="roleCardAdmin" class="role-card" onclick="selectInviteRole('admin')">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">
            <strong style="font-size:13.5px">Administrador</strong>
            <input type="radio" name="invRole" value="admin" style="width:auto;accent-color:#714B67" />
          </div>
          <div style="font-size:11.5px;color:var(--muted);margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid var(--border)">Administra el workspace</div>
          <div class="role-perm">✓ API keys y conectores</div>
          <div class="role-perm">✓ Documentos, logs y uso</div>
          <div class="role-perm">✓ Facturación</div>
          <div class="role-perm">✓ Gestión del equipo</div>
        </div>
      </div>

      <div id="invResultBox" class="hidden" style="background:#EBF8F6;border:1px solid #C4E8E2;color:#0F766E;padding:10px 12px;border-radius:8px;font-size:12px;margin-bottom:12px"></div>
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <button class="btn btn-sec btn-sm" onclick="closeInviteModal()">Cancelar</button>
        <button class="btn btn-sm" onclick="submitInviteMember()">Invitar</button>
      </div>
    </div>
  </div>
</div>

<!-- Modal Crear Nuevo Workspace -->
<div id="newWsModal" class="cmd-backdrop hidden" onclick="if(event.target===this) closeNewWsModal()">
  <div class="cmd-box" style="padding:22px;max-width:420px">
    <h3 style="margin:0 0 6px 0;font-size:17px">Nuevo workspace</h3>
    <p style="margin:0 0 14px 0;font-size:12.5px;color:var(--muted)">Agrupa tus RUCs, claves API, webhooks y plan de forma aislada. Incluye 50 operaciones/mes gratis.</p>
    <label>Nombre del workspace</label>
    <input id="newWsName" placeholder="Ej. Cliente Comercial Lima S.A.C." style="margin-bottom:14px" />
    <div style="display:flex;justify-content:flex-end;gap:8px">
      <button class="btn btn-sec btn-sm" onclick="closeNewWsModal()">Cancelar</button>
      <button class="btn btn-sm" onclick="submitNewWorkspace()">Crear workspace</button>
    </div>
  </div>
</div>

<!-- Command Palette Modal (Ctrl K) -->
<div id="cmdModal" class="cmd-backdrop hidden" onclick="if(event.target===this) closeCmdModal()">
  <div class="cmd-box">
    <input id="cmdInput" class="cmd-input" placeholder="Ir a sección (Inicio, Conectores, Empresas, Documentos, Logs, Facturación)..." oninput="renderCmdList(this.value)" />
    <div id="cmdList" class="cmd-list"></div>
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

function setAuthMode(mode) {
  document.getElementById('formLogin').classList.toggle('hidden', mode !== 'login');
  document.getElementById('formRegister').classList.toggle('hidden', mode !== 'register');
  document.getElementById('formSofia').classList.toggle('hidden', mode !== 'sofia');
  document.getElementById('loginErr').textContent = '';
  const map = { login: 'btnModeLogin', register: 'btnModeRegister', sofia: 'btnModeSofia' };
  Object.entries(map).forEach(([k, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (k === mode) {
      el.className = 'btn btn-sm'; el.style.cssText = 'flex:1';
    } else {
      el.className = 'btn btn-sm btn-sec'; el.style.cssText = 'flex:1;border:none;background:transparent';
    }
  });
}

async function doSofiaSso(directToken) {
  document.getElementById('loginErr').textContent = '';
  try {
    const payload = directToken
      ? { sofia_token: directToken }
      : {
          email: document.getElementById('sofiaEmail').value.trim(),
          password: document.getElementById('sofiaPass').value,
          mfa_code: document.getElementById('sofiaMfa').value.trim() || null
        };
    const res = await fetch('/api/v1/auth/sofia-sso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error de autenticación SOFIA ERP');
    TOKEN = data.access_token;
    localStorage.setItem('sofia_gw_token', TOKEN);
    if (directToken) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    bootApp();
  } catch (e) {
    document.getElementById('loginErr').textContent = e.message;
  }
}

async function doRegister() {
  document.getElementById('loginErr').textContent = '';
  const invToken = new URLSearchParams(window.location.search).get('invite') || null;
  try {
    const res = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: document.getElementById('regName').value.trim(),
        workspace_name: document.getElementById('regWs').value.trim() || null,
        email: document.getElementById('regEmail').value.trim(),
        password: document.getElementById('regPass').value,
        invite_token: invToken
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'No se pudo crear la cuenta');
    TOKEN = data.access_token;
    localStorage.setItem('sofia_gw_token', TOKEN);
    bootApp();
  } catch (e) {
    document.getElementById('loginErr').textContent = e.message;
  }
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

const TAB_LABELS = {
  desk: 'Inicio',
  connectors: 'Conectores IA',
  issuers: 'Empresas',
  documents: 'Documentos',
  summaries: 'Resúmenes (RC/RA)',
  contingencies: 'Contingencias',
  observations: 'Observaciones',
  clients: 'API Keys',
  lookup: 'Consultas RUC / DNI / TC',
  logs: 'Logs API / MCP',
  billing: 'Facturación y Planes',
  team: 'Equipo',
  workspaces: 'Workspaces',
  tester: 'Probador Rápido'
};

let INVITE_ROLE = 'member';
function switchTeamSub(sub) {
  document.getElementById('teamMembersPanel').classList.toggle('hidden', sub !== 'members');
  document.getElementById('teamInvitesPanel').classList.toggle('hidden', sub !== 'invites');
  document.getElementById('teamSubMembers').classList.toggle('active', sub === 'members');
  document.getElementById('teamSubInvites').classList.toggle('active', sub === 'invites');
}
function openInviteModal() {
  document.getElementById('invEmail').value = '';
  document.getElementById('invResultBox').classList.add('hidden');
  selectInviteRole('member');
  document.getElementById('inviteModal').classList.remove('hidden');
  setTimeout(() => document.getElementById('invEmail').focus(), 20);
}
function closeInviteModal() { document.getElementById('inviteModal').classList.add('hidden'); }
function selectInviteRole(role) {
  INVITE_ROLE = role;
  document.getElementById('roleCardMember').classList.toggle('active', role === 'member');
  document.getElementById('roleCardAdmin').classList.toggle('active', role === 'admin');
  const r = document.querySelector(`input[name="invRole"][value="${role}"]`);
  if (r) r.checked = true;
}
async function submitInviteMember() {
  const email = document.getElementById('invEmail').value.trim();
  if (!email || !email.includes('@')) { alert('Ingresa un correo válido.'); return; }
  try {
    const res = await api('/workspaces/team/invite', {
      method: 'POST',
      body: JSON.stringify({ email, role: INVITE_ROLE })
    });
    const box = document.getElementById('invResultBox');
    box.classList.remove('hidden');
    box.innerHTML = `<strong>Invitación creada para ${res.email}.</strong> Comparte este enlace:<br><code style="word-break:break-all">${res.invite_url}</code> <button class="btn btn-sm btn-teal" style="margin-left:6px" onclick="copyText('${res.invite_url}', this)">Copiar</button>`;
    refreshAll();
  } catch (e) {
    alert(e.message);
  }
}
async function removeMember(id) {
  if (!confirm('¿Quitar a este miembro del workspace?')) return;
  await api('/workspaces/team/members/' + id, { method: 'DELETE' });
  refreshAll();
}
async function revokeInvite(id) {
  if (!confirm('¿Revocar esta invitación?')) return;
  await api('/workspaces/team/invitations/' + id, { method: 'DELETE' });
  refreshAll();
}

function toggleWsMenu() { document.getElementById('wsMenu').classList.toggle('hidden'); }
function closeWsMenu() { document.getElementById('wsMenu').classList.add('hidden'); }
function openNewWsModal() {
  closeWsMenu();
  document.getElementById('newWsName').value = '';
  document.getElementById('newWsModal').classList.remove('hidden');
  setTimeout(() => document.getElementById('newWsName').focus(), 20);
}
function closeNewWsModal() { document.getElementById('newWsModal').classList.add('hidden'); }

async function submitNewWorkspace() {
  const name = document.getElementById('newWsName').value.trim();
  if (name.length < 2) { alert('Ingresa un nombre válido para el workspace.'); return; }
  try {
    const res = await api('/workspaces', { method: 'POST', body: JSON.stringify({ name }) });
    if (res.access_token) {
      TOKEN = res.access_token;
      localStorage.setItem('sofia_gw_token', TOKEN);
    }
    closeNewWsModal();
    await refreshAll();
    openTab('desk');
  } catch (e) {
    alert(e.message);
  }
}

async function switchWorkspace(wsId) {
  closeWsMenu();
  try {
    const res = await api('/workspaces/' + wsId + '/switch', { method: 'POST' });
    if (res.access_token) {
      TOKEN = res.access_token;
      localStorage.setItem('sofia_gw_token', TOKEN);
      await refreshAll();
      openTab('desk');
    }
  } catch (e) {
    alert(e.message);
  }
}

function toggleSidebar() {
  document.getElementById('consoleSidebar').classList.toggle('collapsed');
}

function setEnvHint(mode) {
  document.getElementById('envBtnBeta').classList.toggle('active', mode === 'beta');
  document.getElementById('envBtnProd').classList.toggle('active', mode === 'prod');
  const iss = ISSUERS_CACHE.find(i => (mode === 'beta' ? i.is_beta : !i.is_beta));
  if (iss) {
    document.getElementById('globalRucFilter').value = iss.ruc;
    onRucFilterChange();
  }
}

function openCmdModal() {
  document.getElementById('cmdModal').classList.remove('hidden');
  const inp = document.getElementById('cmdInput');
  inp.value = '';
  renderCmdList('');
  setTimeout(() => inp.focus(), 20);
}
function closeCmdModal() { document.getElementById('cmdModal').classList.add('hidden'); }
function renderCmdList(q) {
  const ql = (q || '').toLowerCase();
  const rows = Object.entries(TAB_LABELS)
    .filter(([, label]) => label.toLowerCase().includes(ql))
    .map(([k, label]) => `<button class="cmd-row" onclick="openTab('${k}');closeCmdModal()"><span>${label}</span><span style="color:#9CA3AF;font-size:11px">Ir →</span></button>`)
    .join('');
  document.getElementById('cmdList').innerHTML = rows || '<div style="padding:12px;font-size:12.5px;color:#9CA3AF">Sin coincidencias</div>';
}
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openCmdModal(); }
  if (e.key === 'Escape') closeCmdModal();
});

const DOCS_GROUP = new Set(['documents', 'summaries', 'contingencies', 'observations', 'tester']);

function showTab(name, btn) {
  ['desk', 'documents', 'summaries', 'contingencies', 'observations', 'issuers', 'clients', 'lookup', 'connectors', 'logs', 'billing', 'team', 'workspaces', 'tester'].forEach(t => {
    document.getElementById('tab-' + t).classList.toggle('hidden', t !== name);
  });
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  const targetNav = btn || document.querySelector(`.tab[data-tab="${DOCS_GROUP.has(name) ? 'documents' : name}"]`);
  if (targetNav) targetNav.classList.add('active');

  const subBar = document.getElementById('docsSubBar');
  if (subBar) {
    subBar.classList.toggle('hidden', !DOCS_GROUP.has(name));
    subBar.querySelectorAll('.sub-pill').forEach(p => p.classList.toggle('active', p.dataset.sub === name));
  }

  const crumb = document.getElementById('topbarCrumb');
  if (crumb) crumb.textContent = TAB_LABELS[name] || name;

  if (window.innerWidth <= 900) {
    document.getElementById('consoleSidebar').classList.add('collapsed');
  }
}

if (window.innerWidth <= 900) {
  const _sb = document.getElementById('consoleSidebar');
  if (_sb) _sb.classList.add('collapsed');
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
  const iss = ISSUERS_CACHE.find(i => i.ruc === ruc);
  if (iss) {
    document.getElementById('envBtnBeta').classList.toggle('active', iss.is_beta);
    document.getElementById('envBtnProd').classList.toggle('active', !iss.is_beta);
  }
  refreshScopedData();
}

async function refreshSunatHealth() {
  try {
    const h = await fetch('/api/v1/health/sunat').then(r => r.json());
    const b = document.getElementById('sunatBetaStatus');
    const p = document.getElementById('sunatProdStatus');
    b.className = 'tb-status-pill ' + (h.sunat_beta?.online ? 'b-ok' : 'b-err');
    b.textContent = `● Beta`;
    b.title = `SUNAT Beta: ${h.sunat_beta?.online ? 'ONLINE' : 'CAÍDO'} (${h.sunat_beta?.latency_ms || 0}ms)`;
    p.className = 'tb-status-pill ' + (h.sunat_prod?.online ? 'b-ok' : 'b-err');
    p.textContent = `● Prod`;
    p.title = `SUNAT Prod: ${h.sunat_prod?.online ? 'ONLINE' : 'CAÍDO'} (${h.sunat_prod?.latency_ms || 0}ms)`;
  } catch (e) {}
}

async function refreshScopedData() {
  const ruc = selectedRuc();
  const q = ruc ? `?ruc=${encodeURIComponent(ruc)}` : '';
  const srcFilter = document.getElementById('logSourceFilter') ? document.getElementById('logSourceFilter').value : '';
  const logQs = new URLSearchParams();
  if (ruc) logQs.set('ruc', ruc);
  if (srcFilter) logQs.set('source', srcFilter);
  const [stats, docs, summaries, conts, obs, quota, logs] = await Promise.all([
    api('/stats' + q),
    api('/documents' + (ruc ? `?ruc=${encodeURIComponent(ruc)}&limit=50` : '?limit=50')),
    api('/summaries' + q),
    api('/contingencies' + q),
    api('/observations' + q),
    api('/quota' + q),
    api('/logs' + (logQs.toString() ? '?' + logQs.toString() : '')),
  ]);

  if (quota) {
    document.getElementById('quotaHeadline').textContent = `${quota.remaining} operaciones restantes este mes`;
    document.getElementById('quotaPlanBadge').textContent = `${quota.plan_name} · ${quota.month}`;
    document.getElementById('quotaSub').textContent = `${quota.used_this_month} de ${quota.monthly_quota} comprobantes usados (${quota.usage_pct}%)`;
    const totalTicks = 60;
    const filled = Math.min(totalTicks, Math.round((quota.usage_pct / 100) * totalTicks));
    let ticksHtml = '';
    for (let i = 0; i < totalTicks; i++) {
      const color = i < filled ? '#714B67' : '#D5DAE5';
      ticksHtml += `<span style="flex:1;height:14px;border-radius:2px;background:${color}"></span>`;
    }
    document.getElementById('quotaTicks').innerHTML = ticksHtml;
  }

  document.getElementById('logsTable').innerHTML = (logs || []).map(l => `
    <tr>
      <td style="font-size:12px;color:var(--muted)">${(l.created_at || '').slice(0,19).replace('T',' ')}</td>
      <td><span class="badge ${l.source === 'MCP' ? 'b-info' : 'b-ok'}">${l.source}</span></td>
      <td><code>${l.action}</code></td>
      <td><code>${l.issuer_ruc || '-'}</code></td>
      <td style="font-size:12px">${l.client_label || '-'}</td>
      <td><span class="badge ${l.status_code < 400 ? 'b-ok' : 'b-err'}">${l.status_code}</span></td>
      <td style="font-size:12px">${l.latency_ms} ms</td>
      <td style="font-size:12px;color:var(--muted);max-width:240px">${l.error_summary || 'OK'}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">Sin registros de API o MCP aún. Prueba un tool desde Conectores IA.</td></tr>';

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
  const [me, issuers, clients, billing, orders, workspaces, team, billProfile, aiConns] = await Promise.all([
    api('/auth/me'),
    api('/issuers'),
    api('/clients'),
    api('/billing/plans'),
    api('/billing/orders'),
    api('/workspaces'),
    api('/workspaces/team'),
    api('/billing/profile'),
    api('/connectors/connections'),
  ]);
  ISSUERS_CACHE = issuers;
  BILLING_CACHE = billing;

  if (Array.isArray(aiConns)) {
    document.getElementById('aiConnectionsTable').innerHTML = aiConns.map(c => `
      <tr>
        <td><strong>${c.app_name}</strong></td>
        <td><span class="badge ${c.kind === 'oauth' ? 'b-info' : 'b-ok'}">${c.auth_type}</span></td>
        <td><code>${c.detail}</code></td>
        <td style="font-size:12px;color:var(--muted)">${(c.connected_at || '').slice(0, 10)}</td>
        <td><button class="btn btn-sm btn-err" onclick="disconnectAiConnection('${c.kind}', '${c.id}')">Desconectar</button></td>
      </tr>
    `).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:24px">Aún no hay asistentes de IA conectados. Haz clic en <strong>Conectar</strong> arriba en Claude o ChatGPT.</td></tr>';
  }

  if (billProfile) {
    document.getElementById('bfDocType').value = billProfile.doc_type_receipt || '01';
    document.getElementById('bfIdType').value = billProfile.identity_type || '6';
    document.getElementById('bfIdNum').value = billProfile.identity_number || '';
    document.getElementById('bfName').value = billProfile.business_name || '';
    document.getElementById('bfAddr').value = billProfile.address || '';
    document.getElementById('bfAddr2').value = billProfile.address2 || '';
    document.getElementById('bfCity').value = billProfile.city || '';
    document.getElementById('bfDept').value = billProfile.department || '';
    document.getElementById('bfZip').value = billProfile.postal_code || '';
    document.getElementById('bfEmail').value = billProfile.billing_email || '';
  }

  if (team) {
    const roleLabel = r => r === 'owner' ? 'Propietario' : (r === 'admin' ? 'Administrador' : 'Miembro');
    document.getElementById('teamMemCount').textContent = (team.members || []).length;
    document.getElementById('teamInvCount').textContent = (team.invitations || []).length;
    document.getElementById('btnOpenInvite').classList.toggle('hidden', !team.can_manage);

    document.getElementById('teamMembersTable').innerHTML = (team.members || []).map(m => {
      const initials = (m.full_name || m.email || 'U').split(' ').map(s => s[0]).join('').slice(0, 2).toUpperCase();
      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <span class="tb-avatar" style="background:var(--o20-primary-soft);color:var(--o20-primary)">${initials}</span>
              <div>
                <strong>${m.full_name}</strong> ${m.is_me ? '<span class="badge b-info" style="margin-left:4px">Tú</span>' : ''}
                <div style="font-size:11.5px;color:var(--muted)">${m.email}</div>
              </div>
            </div>
          </td>
          <td><strong>${roleLabel(m.role)}</strong></td>
          <td style="font-size:12px;color:var(--muted)">${(m.joined_at || '').slice(0, 10)}</td>
          <td>${(team.can_manage && m.role !== 'owner' && !m.is_me) ? `<button class="btn btn-sm btn-err" onclick="removeMember('${m.id}')">Quitar</button>` : '<span style="font-size:12px;color:var(--muted)">—</span>'}</td>
        </tr>
      `;
    }).join('');

    document.getElementById('teamInvitesTable').innerHTML = (team.invitations || []).map(inv => `
      <tr>
        <td><strong>${inv.email}</strong></td>
        <td><span class="badge b-info">${roleLabel(inv.role)}</span></td>
        <td><code style="font-size:11.5px">${inv.invite_url}</code></td>
        <td class="row-actions">
          <button class="btn btn-sm btn-sec" onclick="copyText('${inv.invite_url}', this)">Copiar enlace</button>
          ${team.can_manage ? `<button class="btn btn-sm btn-err" onclick="revokeInvite('${inv.id}')">Revocar</button>` : ''}
        </td>
      </tr>
    `).join('') || '<tr><td colspan="4" style="color:var(--muted);text-align:center">Sin invitaciones pendientes.</td></tr>';
  }

  if (Array.isArray(workspaces)) {
    document.getElementById('wsMenuList').innerHTML = workspaces.map(w => `
      <button type="button" class="sb-ws-opt" onclick="switchWorkspace('${w.id}')">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${w.name}</span>
        ${w.is_current ? '<span style="color:var(--o20-teal);font-weight:700">✓</span>' : `<span style="font-size:10.5px;color:#9CA3AF">${w.plan_name}</span>`}
      </button>
    `).join('') || '<div style="padding:6px 8px;font-size:12px;color:#9CA3AF">Sin workspaces creados</div>';

    document.getElementById('workspacesTable').innerHTML = workspaces.map(w => `
      <tr>
        <td>
          <strong>${w.name}</strong> ${w.is_current ? '<span class="badge b-info" style="margin-left:6px">Actual</span>' : ''}
          <div style="font-size:11.5px;color:var(--muted)"><code>${w.slug}</code></div>
        </td>
        <td><span class="badge ${w.source === 'sofia_erp' ? 'b-info' : 'b-ok'}">${w.source === 'sofia_erp' ? 'SOFIA ERP' : 'Externo'}</span></td>
        <td><strong>${w.plan_name}</strong></td>
        <td>${(w.monthly_quota || 0).toLocaleString()} / mes</td>
        <td>${w.is_current ? '<span style="font-size:12px;color:var(--muted)">En uso</span>' : `<button class="btn btn-sm btn-sec" onclick="switchWorkspace('${w.id}')">Cambiar →</button>`}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center">Aún no hay workspaces. Crea uno con "+ Nuevo workspace".</td></tr>';
  }

  if (me) {
    const h = new Date().getHours();
    const salute = h < 12 ? 'Buenos días' : (h < 19 ? 'Buenas tardes' : 'Buenas noches');
    const wsBadge = document.getElementById('workspaceBadge');
    const sbAvatar = document.getElementById('sbWsAvatar');
    const userAvatar = document.getElementById('userAvatar');
    if (me.is_superadmin) {
      wsBadge.textContent = 'Superadmin Global';
      if (sbAvatar) sbAvatar.textContent = 'S';
      if (userAvatar) userAvatar.textContent = 'A';
      document.getElementById('heroGreeting').innerHTML = `${salute}, <span style="color:var(--muted);font-weight:500">Admin</span>`;
    } else if (me.workspace) {
      const firstName = (me.full_name || me.email || 'Usuario').split(' ')[0];
      wsBadge.textContent = me.workspace.name;
      if (sbAvatar) sbAvatar.textContent = (me.workspace.name[0] || 'W').toUpperCase();
      if (userAvatar) userAvatar.textContent = (firstName[0] || 'U').toUpperCase();
      document.getElementById('heroGreeting').innerHTML = `${salute}, <span style="color:var(--muted);font-weight:500">${firstName}</span>`;
      document.getElementById('heroSub').textContent = `Facturación electrónica SUNAT & Remote MCP · Plan ${me.workspace.plan_name} (${me.workspace.monthly_quota} ops/mes).`;
    }
  }

  renderPlansGrid();

  document.getElementById('ordersTable').innerHTML = (orders || []).map(o => `
    <tr>
      <td style="font-size:12px;color:var(--muted)">${(o.created_at || '').slice(0,19).replace('T',' ')}</td>
      <td><strong>${o.plan_code}</strong></td>
      <td>${o.quota_granted.toLocaleString()} / mes</td>
      <td>S/ ${o.amount_pen.toFixed(2)}</td>
      <td><span class="badge ${o.status === 'PAID' ? 'b-ok' : (o.status === 'PENDING' ? 'b-warn' : 'b-err')}">${o.status}</span></td>
      <td><code>${o.mp_payment_id || '-'}</code></td>
    </tr>
  `).join('') || '<tr><td colspan="6" style="color:var(--muted);text-align:center">Sin pagos registrados aún.</td></tr>';

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
          description: 'Servicio de Prueba API SUNAT',
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

function toggleDevMcpBox() {
  const box = document.getElementById('devMcpBox');
  const ch = document.getElementById('devMcpChevron');
  const hidden = box.classList.toggle('hidden');
  if (ch) ch.textContent = hidden ? '⌄' : '⌃';
}

function openConnectGuide(provider) {
  const title = document.getElementById('cgTitle');
  const body = document.getElementById('cgBody');
  const link = document.getElementById('cgExternalLink');
  if (provider === 'claude') {
    title.textContent = 'Conectar Claude a API SUNAT';
    link.href = 'https://claude.ai/settings/connectors';
    link.textContent = 'Abrir Claude Connectors ↗';
    body.innerHTML = `
      <ol style="padding-left:18px;margin:0">
        <li>Abre <strong>Claude → Configuración → Conectores → Agregar conector personalizado</strong>.</li>
        <li>Pega esta URL Remote MCP:<br>
          <div style="display:flex;gap:8px;align-items:center;margin:8px 0">
            <code style="flex:1;padding:6px 8px">https://apisunat.pro/mcp</code>
            <button class="btn btn-sm" onclick="copyText('https://apisunat.pro/mcp', this)">Copiar</button>
          </div>
        </li>
        <li>Claude abrirá la pantalla <strong>OAuth 2.1</strong> de API SUNAT: inicia sesión, elige tu RUC y haz clic en <strong>Autorizar</strong>.</li>
      </ol>
    `;
  } else {
    title.textContent = 'Conectar ChatGPT a API SUNAT';
    link.href = 'https://chatgpt.com/gpts/editor';
    link.textContent = 'Abrir ChatGPT ↗';
    body.innerHTML = `
      <p style="margin:0 0 8px 0"><strong>Opción 1 — ChatGPT Connectors (MCP OAuth 2.1):</strong></p>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
        <code style="flex:1;padding:6px 8px">https://apisunat.pro/mcp</code>
        <button class="btn btn-sm" onclick="copyText('https://apisunat.pro/mcp', this)">Copiar MCP</button>
      </div>
      <p style="margin:0 0 8px 0"><strong>Opción 2 — Custom GPT Actions (OpenAPI 3.1 + Bearer API Key):</strong></p>
      <div style="display:flex;gap:8px;align-items:center">
        <code style="flex:1;padding:6px 8px">https://apisunat.pro/openapi-ai.json</code>
        <button class="btn btn-sm btn-teal" onclick="copyText('https://apisunat.pro/openapi-ai.json', this)">Copiar OpenAPI</button>
      </div>
    `;
  }
  document.getElementById('connectGuideModal').classList.remove('hidden');
}

function closeConnectGuide() {
  document.getElementById('connectGuideModal').classList.add('hidden');
}

async function disconnectAiConnection(kind, id) {
  if (!confirm('¿Desconectar y revocar el acceso de este asistente IA?')) return;
  if (kind === 'oauth') {
    await api('/connectors/oauth/' + id, { method: 'DELETE' });
  } else {
    await api('/clients/' + id, { method: 'DELETE' });
  }
  refreshAll();
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

async function runLookup(kind) {
  const outId = kind === 'ruc' ? 'lkRucOut' : (kind === 'dni' ? 'lkDniOut' : 'lkTcOut');
  const out = document.getElementById(outId);
  out.classList.remove('hidden');
  out.textContent = 'Consultando API SUNAT...';
  try {
    let path = '/lookup/exchange-rate';
    if (kind === 'ruc') path = '/lookup/ruc/' + encodeURIComponent(document.getElementById('lkRuc').value.trim());
    else if (kind === 'dni') path = '/lookup/dni/' + encodeURIComponent(document.getElementById('lkDni').value.trim());
    else {
      const dt = document.getElementById('lkTcDate').value.trim();
      if (dt) path += '?date=' + encodeURIComponent(dt);
    }
    const res = await api(path);
    out.textContent = JSON.stringify(res, null, 2);
  } catch (e) {
    out.textContent = 'ERROR: ' + e.message;
  }
}

let BILLING_CACHE = null;
let BILLING_CYCLE = 'monthly';

function switchBillingSub(sub) {
  document.getElementById('billingPlansPanel').classList.toggle('hidden', sub !== 'plans');
  document.getElementById('billingProfilePanel').classList.toggle('hidden', sub !== 'profile');
  document.getElementById('billSubPlans').classList.toggle('active', sub === 'plans');
  document.getElementById('billSubProfile').classList.toggle('active', sub === 'profile');
}

function setBillingCycle(cycle) {
  BILLING_CYCLE = cycle;
  document.getElementById('cycleBtnMonthly').classList.toggle('active', cycle === 'monthly');
  document.getElementById('cycleBtnYearly').classList.toggle('active', cycle === 'yearly');
  renderPlansGrid();
}

function renderPlansGrid() {
  if (!BILLING_CACHE || !BILLING_CACHE.plans) return;
  const isYearly = BILLING_CYCLE === 'yearly';
  document.getElementById('plansGrid').innerHTML = BILLING_CACHE.plans.map(p => {
    const isCurrent = BILLING_CACHE.current_plan === p.code;
    const isFree = p.code === 'FREE';
    const isCustom = !!p.custom_contact;
    const headCls = isFree ? 'plan-head-light' : (p.code === 'PRO' ? 'plan-head-teal' : 'plan-head-dark');
    const priceVal = Number(isYearly ? (p.annual_price_pen || p.price_pen * 10) : p.price_pen);
    const priceFmt = priceVal === 0 ? '0' : (Number.isInteger(priceVal) ? priceVal.toFixed(0) : priceVal.toFixed(2));
    const periodTxt = isFree ? (p.period_label || '/ 30 días') : (isYearly ? '/año' : '/mes');
    const priceHtml = isCustom
      ? `<div class="plan-price" style="font-size:21px">Según<br/>volumen</div>`
      : `<div class="plan-price">S/ ${priceFmt} <small>${periodTxt}</small></div>`;

    let btnHtml = '';
    if (isFree) {
      btnHtml = `<button class="btn btn-sm btn-sec" disabled style="width:100%;margin:12px 0 8px 0">${isCurrent ? '✓ Plan actual' : 'Plan base'}</button>`;
    } else if (isCustom) {
      btnHtml = `<a href="mailto:ventas@sofiaerp.com?subject=Plan%20A%20Medida%20API%20SUNAT" class="btn btn-sm btn-sec" style="width:100%;margin:12px 0 8px 0;text-align:center;text-decoration:none;display:block">Contactar ventas</a>`;
    } else {
      btnHtml = `<button class="btn btn-sm ${p.code === 'PRO' ? 'btn-teal' : ''}" style="width:100%;margin:12px 0 8px 0" onclick="startPlanCheckout('${p.code}')">${isCurrent ? 'Renovar con Mercado Pago' : 'Mejorar'}</button>`;
    }

    const feats = (p.features || []).map(f => `<div class="plan-feat">${f}</div>`).join('');
    return `
      <div class="plan-card ${isCurrent ? 'plan-current' : ''}">
        <div class="plan-head ${headCls}">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:14px;font-weight:700">${p.name}</span>
            ${isCurrent ? '<span class="badge b-ok">Actual</span>' : (p.code === 'PRO' ? '<span class="badge b-nav">Recomendado</span>' : '')}
          </div>
          ${priceHtml}
        </div>
        <div class="plan-body">
          ${btnHtml}
          <div style="font-size:12.5px;font-weight:700;color:var(--text);padding:6px 0 8px 0;border-bottom:1px solid #F3F4F6">${p.headline || ''}</div>
          ${feats}
        </div>
      </div>
    `;
  }).join('');
}

function onBillingDocTypeChange() {
  const dt = document.getElementById('bfDocType').value;
  document.getElementById('bfIdType').value = dt === '01' ? '6' : '1';
  document.getElementById('bfIdNum').maxLength = dt === '01' ? 11 : 8;
}

async function lookupBillingFiscalData() {
  const idType = document.getElementById('bfIdType').value;
  const num = document.getElementById('bfIdNum').value.trim();
  const msg = document.getElementById('bfMsg');
  msg.style.color = 'var(--muted)';
  msg.textContent = 'Consultando en SUNAT / RENIEC...';
  try {
    if (idType === '6') {
      const d = await api('/lookup/ruc/' + encodeURIComponent(num));
      if (d.business_name) document.getElementById('bfName').value = d.business_name;
      if (d.address) document.getElementById('bfAddr').value = d.address;
      if (d.province || d.district) document.getElementById('bfCity').value = d.province || d.district;
      if (d.department) document.getElementById('bfDept').value = d.department;
      msg.style.color = 'var(--ok)';
      msg.textContent = `RUC encontrado (${d.source || 'SUNAT'}).`;
    } else {
      const d = await api('/lookup/dni/' + encodeURIComponent(num));
      if (d.full_name) document.getElementById('bfName').value = d.full_name;
      msg.style.color = 'var(--ok)';
      msg.textContent = `DNI encontrado (${d.source || 'RENIEC'}).`;
    }
  } catch (e) {
    msg.style.color = 'var(--err)';
    msg.textContent = e.message;
  }
}

async function saveBillingProfile() {
  const msg = document.getElementById('bfMsg');
  msg.style.color = 'var(--muted)';
  msg.textContent = 'Guardando...';
  try {
    await api('/billing/profile', {
      method: 'PUT',
      body: JSON.stringify({
        doc_type_receipt: document.getElementById('bfDocType').value,
        identity_type: document.getElementById('bfIdType').value,
        identity_number: document.getElementById('bfIdNum').value.trim(),
        business_name: document.getElementById('bfName').value.trim(),
        address: document.getElementById('bfAddr').value.trim(),
        address2: document.getElementById('bfAddr2').value.trim(),
        city: document.getElementById('bfCity').value.trim(),
        department: document.getElementById('bfDept').value.trim(),
        postal_code: document.getElementById('bfZip').value.trim(),
        billing_email: document.getElementById('bfEmail').value.trim()
      })
    });
    msg.style.color = 'var(--ok)';
    msg.textContent = '✓ Datos de facturación guardados correctamente.';
  } catch (e) {
    msg.style.color = 'var(--err)';
    msg.textContent = e.message;
  }
}

async function startPlanCheckout(planCode) {
  try {
    const res = await api('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_code: planCode, billing_cycle: BILLING_CYCLE })
    });
    if (res.checkout_url) {
      window.location.href = res.checkout_url;
    } else {
      alert('No se recibió URL de Mercado Pago.');
    }
  } catch (e) {
    alert(e.message);
  }
}

function bootApp() {
  document.getElementById('loginView').classList.add('hidden');
  document.getElementById('appView').classList.remove('hidden');
  const qs = new URLSearchParams(window.location.search);
  const bStatus = qs.get('billing');
  if (bStatus) {
    const banner = document.getElementById('billingBanner');
    banner.classList.remove('hidden');
    banner.textContent = bStatus === 'success'
      ? '¡Pago confirmado en Mercado Pago! Tu plan y cuota mensual han sido actualizados.'
      : (bStatus === 'pending' ? 'Tu pago está pendiente de confirmación en Mercado Pago.' : 'El pago fue cancelado o rechazado.');
    openTab('billing');
  }
  refreshAll();
}

const _urlParams = new URLSearchParams(window.location.search);
const _urlSofiaToken = _urlParams.get('sofia_token');
const _urlInviteToken = _urlParams.get('invite');
if (_urlSofiaToken) {
  doSofiaSso(_urlSofiaToken);
} else if (TOKEN) {
  if (_urlInviteToken) {
    api('/workspaces/invitations/' + encodeURIComponent(_urlInviteToken) + '/accept', { method: 'POST' })
      .then(res => {
        if (res && res.access_token) { TOKEN = res.access_token; localStorage.setItem('sofia_gw_token', TOKEN); }
        window.history.replaceState({}, document.title, window.location.pathname);
        bootApp();
      }).catch(() => bootApp());
  } else {
    bootApp();
  }
} else if (_urlInviteToken) {
  setAuthMode('register');
}
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def gateway_panel():
    return HTMLResponse(content=PANEL_HTML)
