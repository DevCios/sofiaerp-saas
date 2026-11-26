// POS Express — Cliente Ultraligero Unificado (Windows .exe Tauri + Android .apk Capacitor + PWA)
const STORAGE_AUTH = 'sofia_pos_auth_v1';
const STORAGE_DATA = 'sofia_pos_data_v1';
const STORAGE_QUEUE = 'sofia_pos_offline_queue_v1';

let AUTH = JSON.parse(localStorage.getItem(STORAGE_AUTH) || 'null');
let POS = JSON.parse(localStorage.getItem(STORAGE_DATA) || 'null');
let CART = [];
let ACTIVE_CAT = 0;
let DOC_TYPE = '03';
let PAY_JOURNAL_ID = null;
let CUSTOMER = null;

function getQueue() {
  return JSON.parse(localStorage.getItem(STORAGE_QUEUE) || '[]');
}
function saveQueue(q) {
  localStorage.setItem(STORAGE_QUEUE, JSON.stringify(q));
  renderQueueBadge();
}

function renderQueueBadge() {
  const q = getQueue();
  const el = document.getElementById('badgeQueue');
  if (!el) return;
  if (q.length > 0) {
    el.textContent = `Pendientes: ${q.length}`;
    el.classList.remove('hidden');
  } else {
    el.classList.add('hidden');
  }
}

function updateOnlineBadge() {
  const b = document.getElementById('badgeOnline');
  if (!b) return;
  if (navigator.onLine) {
    b.className = 'pill pill-ok';
    b.textContent = 'Online';
    syncOfflineQueue();
  } else {
    b.className = 'pill pill-warn';
    b.textContent = 'Offline (Cola Local)';
  }
}
window.addEventListener('online', updateOnlineBadge);
window.addEventListener('offline', updateOnlineBadge);

async function postApi(ep, payload) {
  if (!AUTH || !AUTH.serverUrl) throw new Error('No conectado a un servidor SOFIA ERP.');
  const r = await fetch(AUTH.serverUrl.replace(/\/+$/, '') + '/pos_express/api/' + ep, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-POS-Token': AUTH.token || ''
    },
    body: JSON.stringify(payload || {})
  });
  if (r.status === 401) {
    doLogout();
    throw new Error('Sesión expirada. Inicia sesión nuevamente.');
  }
  return await r.json();
}

async function doAppLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('loginErr');
  const btn = document.getElementById('btnLogin');
  errEl.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = 'Conectando...';
  try {
    const serverUrl = document.getElementById('fServer').value.trim().replace(/\/+$/, '');
    const login = document.getElementById('fLogin').value.trim();
    const password = document.getElementById('fPass').value;

    const r = await fetch(serverUrl + '/pos_express/api/app_login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password })
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || !data.success) {
      throw new Error(data.error || 'No se pudo conectar al servidor SOFIA ERP.');
    }

    AUTH = { serverUrl, token: data.token, sessionId: data.session_id, login };
    POS = data.pos_data;
    localStorage.setItem(STORAGE_AUTH, JSON.stringify(AUTH));
    localStorage.setItem(STORAGE_DATA, JSON.stringify(POS));
    bootTerminal();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Conectar y Abrir Caja';
  }
}

function doLogout() {
  if (getQueue().length > 0 && !confirm('Hay ventas offline sin sincronizar. ¿Salir de todas formas?')) return;
  AUTH = null;
  localStorage.removeItem(STORAGE_AUTH);
  document.getElementById('appView').classList.add('hidden');
  document.getElementById('loginView').classList.remove('hidden');
}

async function refreshFromServer() {
  if (!AUTH || !navigator.onLine) return;
  try {
    const fresh = await postApi('data', { session_id: AUTH.sessionId });
    if (fresh && !fresh.error) {
      POS = fresh;
      localStorage.setItem(STORAGE_DATA, JSON.stringify(POS));
      renderTerminalState();
    }
  } catch (e) {}
}

function bootTerminal() {
  document.getElementById('loginView').classList.add('hidden');
  document.getElementById('appView').classList.remove('hidden');
  renderTerminalState();
  updateOnlineBadge();
  renderQueueBadge();
  refreshFromServer();
}

function renderTerminalState() {
  if (!POS) return;
  const sym = POS.company_info.currency_symbol || 'S/';
  document.getElementById('hdrTitle').textContent = POS.header_title || 'POS Express';
  document.getElementById('hdrSub').textContent = `${POS.session_name} · ${POS.user_name} · ${POS.company_info.provider.toUpperCase()}${POS.company_info.test_env ? ' (BETA)' : ''}`;
  document.getElementById('badgeSales').textContent = `Ventas: ${sym} ${Number(POS.sales_total || 0).toFixed(2)}`;

  if (POS.company_info.is_nrus) {
    document.getElementById('badgeRegime').classList.remove('hidden');
    document.getElementById('btnDoc01').classList.add('hidden');
    DOC_TYPE = '03';
  } else {
    document.getElementById('badgeRegime').classList.add('hidden');
    document.getElementById('btnDoc01').classList.remove('hidden');
  }

  if (!CUSTOMER) CUSTOMER = POS.default_partner;
  renderCustomer();
  renderCategories();
  renderProducts();
  renderPayMethods();
  renderCart();
}

function renderCustomer() {
  document.getElementById('custName').textContent = CUSTOMER ? `${CUSTOMER.name} (${CUSTOMER.vat || 'S/D'})` : 'Consumidor Final';
}
function resetCustomer() {
  CUSTOMER = POS ? POS.default_partner : null;
  document.getElementById('custDocInput').value = '';
  renderCustomer();
}
function selectDocType(t) {
  if (POS && POS.company_info.is_nrus && t === '01') return;
  DOC_TYPE = t;
  document.getElementById('btnDoc03').classList.toggle('active', t === '03');
  document.getElementById('btnDoc01').classList.toggle('active', t === '01');
}

function renderCategories() {
  const bar = document.getElementById('catBar');
  let html = `<button class="cat-btn ${ACTIVE_CAT === 0 ? 'active' : ''}" onclick="setCat(0)">Todos (${POS.catalog.length})</button>`;
  (POS.product_categories || []).forEach(c => {
    html += `<button class="cat-btn ${ACTIVE_CAT === c.id ? 'active' : ''}" onclick="setCat(${c.id})">${c.name}</button>`;
  });
  bar.innerHTML = html;
}
function setCat(id) { ACTIVE_CAT = id; renderCategories(); renderProducts(); }

function renderProducts() {
  if (!POS) return;
  const q = (document.getElementById('searchInput').value || '').trim().toLowerCase();
  const sym = POS.company_info.currency_symbol || 'S/';
  const list = (POS.catalog || []).filter(p => {
    if (ACTIVE_CAT && (!p.categ_id || p.categ_id[0] !== ACTIVE_CAT)) return false;
    if (!q) return true;
    return (p.name || '').toLowerCase().includes(q)
      || (p.default_code || '').toLowerCase().includes(q)
      || (p.barcode || '').toLowerCase().includes(q);
  }).slice(0, 120);

  document.getElementById('prodGrid').innerHTML = list.map(p => `
    <div class="prod-card" onclick="addToCart(${p.id})">
      <div class="prod-name">${p.name}</div>
      <div class="prod-meta">
        <span class="prod-price">${sym} ${Number(p.list_price || 0).toFixed(2)}</span>
        <span class="prod-stock">Stock: ${Number(p.qty_available || 0)}</span>
      </div>
    </div>
  `).join('') || '<div style="color:var(--muted);padding:20px">Sin productos encontrados.</div>';
}

document.getElementById('searchInput').addEventListener('input', renderProducts);
document.getElementById('searchInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && POS) {
    const q = e.target.value.trim().toLowerCase();
    const exact = POS.catalog.find(p => (p.barcode || '').toLowerCase() === q || (p.default_code || '').toLowerCase() === q);
    if (exact) { addToCart(exact.id); e.target.value = ''; renderProducts(); }
  }
});

function addToCart(prodId) {
  const prod = POS.catalog.find(p => p.id === prodId);
  if (!prod) return;
  const ex = CART.find(i => i.product_id === prodId);
  if (ex) ex.qty += 1;
  else CART.push({ product_id: prod.id, name: prod.name, price: Number(prod.list_price || 0), qty: 1, discount: 0 });
  renderCart();
}
function chQty(idx, delta) {
  CART[idx].qty += delta;
  if (CART[idx].qty <= 0) CART.splice(idx, 1);
  renderCart();
}
function cartTotalAmount() {
  return CART.reduce((s, i) => s + (i.qty * i.price * (1 - (i.discount || 0) / 100)), 0);
}

function renderCart() {
  if (!POS) return;
  const sym = POS.company_info.currency_symbol || 'S/';
  document.getElementById('cartLines').innerHTML = CART.map((item, idx) => `
    <div class="cart-item">
      <div style="flex:1">
        <div style="font-size:13px;font-weight:600">${item.name}</div>
        <div style="font-size:11.5px;color:var(--muted)">${sym} ${item.price.toFixed(2)} c/u</div>
      </div>
      <div class="qty-ctrl">
        <button class="qty-btn" onclick="chQty(${idx}, -1)">-</button>
        <span style="min-width:22px;text-align:center;font-weight:700">${item.qty}</span>
        <button class="qty-btn" onclick="chQty(${idx}, 1)">+</button>
      </div>
      <div style="min-width:66px;text-align:right;font-weight:700;font-size:13px">${sym} ${(item.qty * item.price).toFixed(2)}</div>
    </div>
  `).join('') || '<div style="text-align:center;color:var(--muted);padding:36px 10px;font-size:13px">Agrega productos desde el catálogo</div>';

  const tot = cartTotalAmount();
  document.getElementById('cartTotal').textContent = `${sym} ${tot.toFixed(2)}`;
  document.getElementById('mobCartBtn').textContent = `Carrito (${CART.reduce((s, i) => s + i.qty, 0)}) · ${sym} ${tot.toFixed(2)}`;
  updateChange();
}

function renderPayMethods() {
  if (!POS) return;
  if (POS.payment_methods.length && !PAY_JOURNAL_ID) PAY_JOURNAL_ID = POS.payment_methods[0].id;
  document.getElementById('payMethods').innerHTML = POS.payment_methods.map(m => `
    <button class="pay-btn pay-${m.code} ${PAY_JOURNAL_ID === m.id ? 'active' : ''}" onclick="setPayMethod(${m.id})">${m.name}</button>
  `).join('');
  const activeMethod = POS.payment_methods.find(m => m.id === PAY_JOURNAL_ID);
  const refEl = document.getElementById('payRefInput');
  if (refEl) refEl.classList.toggle('hidden', !activeMethod || activeMethod.code === 'cash');
}
function setPayMethod(id) { PAY_JOURNAL_ID = id; renderPayMethods(); }
function setQuickPaid(v) {
  const tot = cartTotalAmount();
  document.getElementById('paidInput').value = (v === 'exact' ? tot : v).toFixed(2);
  updateChange();
}
function updateChange() {
  if (!POS) return;
  const sym = POS.company_info.currency_symbol || 'S/';
  const tot = cartTotalAmount();
  const paid = parseFloat(document.getElementById('paidInput').value || '0') || 0;
  document.getElementById('changeLbl').textContent = `Vuelto: ${sym} ${Math.max(0, paid - tot).toFixed(2)}`;
}

async function consultCustomer() {
  const doc = (document.getElementById('custDocInput').value || '').trim();
  if (!doc) return;
  try {
    const res = await postApi('consult_doc', { doc_number: doc });
    if (res.error) { alert(res.error); return; }
    CUSTOMER = res;
    if (doc.length === 11 && !POS.company_info.is_nrus) selectDocType('01');
    renderCustomer();
  } catch (e) {
    alert('Sin conexión para consultar SUNAT. Puedes emitir a Consumidor Final en modo offline.');
  }
}

async function submitCheckout() {
  if (!CART.length) { alert('Agrega al menos un producto.'); return; }
  const btn = document.getElementById('btnPay');
  btn.disabled = true;
  btn.textContent = 'Procesando...';
  const sj = POS.sales_journals.find(j => j.code_type === DOC_TYPE) || POS.sales_journals[0];
  const tot = cartTotalAmount();
  const paid = parseFloat(document.getElementById('paidInput').value || '0') || tot;
  const payload = {
    session_id: AUTH.sessionId,
    partner_id: CUSTOMER ? CUSTOMER.id : null,
    lines: JSON.parse(JSON.stringify(CART)),
    amount_paid: paid,
    doc_type_code: DOC_TYPE,
    payment_journal_id: PAY_JOURNAL_ID,
    sales_journal_id: sj ? sj.id : null,
    note: (document.getElementById('payRefInput').value || '').trim()
  };

  try {
    if (!navigator.onLine) throw new Error('OFFLINE_MODE');
    const res = await postApi('checkout', payload);
    if (res.error) { alert(res.error); return; }
    CART = [];
    document.getElementById('paidInput').value = '';
    document.getElementById('payRefInput').value = '';
    resetCustomer();
    renderCart();
    showTicket(res.ticket);
    refreshFromServer();
  } catch (err) {
    // Modo Offline: guardar en cola local e imprimir ticket provisional sin detener la caja
    const q = getQueue();
    q.push({ id: Date.now(), created_at: new Date().toISOString(), payload });
    saveQueue(q);

    const offlineTicket = {
      company_name: POS.company_info.name,
      company_vat: POS.company_info.vat,
      company_address: POS.company_info.street,
      currency_symbol: POS.company_info.currency_symbol,
      is_nrus: POS.company_info.is_nrus,
      doc_badge: DOC_TYPE === '01' ? 'FACTURA (PENDIENTE SYNC)' : 'BOLETA (PENDIENTE SYNC)',
      name: `OFFLINE-${String(q.length).padStart(4, '0')}`,
      sunat_status: 'COLA OFFLINE LOCAL',
      date: new Date().toLocaleDateString('es-PE'),
      time: new Date().toLocaleTimeString('es-PE'),
      partner: CUSTOMER ? CUSTOMER.name : 'Consumidor Final',
      vat: CUSTOMER ? CUSTOMER.vat : '00000000',
      lines: payload.lines.map(l => ({ name: l.name, qty: l.qty, subtotal: l.qty * l.price })),
      amount_untaxed: POS.company_info.is_nrus ? tot : (tot / 1.18),
      amount_tax: POS.company_info.is_nrus ? 0 : (tot - tot / 1.18),
      amount_total: tot,
      amount_paid: paid,
      change: Math.max(0, paid - tot),
      ticket_footer: 'Venta registrada en modo offline. Se enviará a SUNAT automáticamente al restablecer Internet.',
      cpe_url: 'https://gateway.sofiaerp.com/consulta'
    };
    CART = [];
    document.getElementById('paidInput').value = '';
    document.getElementById('payRefInput').value = '';
    resetCustomer();
    renderCart();
    showTicket(offlineTicket);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Cobrar y Emitir SUNAT';
  }
}

async function syncOfflineQueue() {
  if (!AUTH || !navigator.onLine) return;
  const q = getQueue();
  if (!q.length) return;
  const remaining = [];
  for (const item of q) {
    try {
      const res = await postApi('checkout', item.payload);
      if (res.error) remaining.push(item);
    } catch (e) {
      remaining.push(item);
    }
  }
  saveQueue(remaining);
  if (remaining.length < q.length) refreshFromServer();
}
setInterval(syncOfflineQueue, 30000);

function showTicket(t) {
  const sym = t.currency_symbol || 'S/';
  const rows = (t.lines || []).map(l => `<div>${l.qty}x ${l.name} — <strong>${sym} ${Number(l.subtotal).toFixed(2)}</strong></div>`).join('');
  const taxHtml = t.is_nrus
    ? `<div>Op. Inafecta (NRUS): ${sym} ${Number(t.amount_total).toFixed(2)}</div>`
    : `<div>Op. Gravada: ${sym} ${Number(t.amount_untaxed).toFixed(2)}</div><div>IGV 18%: ${sym} ${Number(t.amount_tax).toFixed(2)}</div>`;
  document.getElementById('ticketContent').innerHTML = `
    <div class="center">
      <strong>${t.company_name}</strong><br/>
      RUC: ${t.company_vat}<br/>
      ${t.company_address || ''}<br/>
      <hr/>
      <strong>${t.doc_badge}</strong><br/>
      <strong>${t.name}</strong><br/>
      <span style="font-size:11px">SUNAT: ${t.sunat_status}</span>
    </div>
    <hr/>
    <div>Fecha: ${t.date} ${t.time}</div>
    <div>Cliente: ${t.partner} (${t.vat || 'S/D'})</div>
    <hr/>
    ${rows}
    <hr/>
    ${taxHtml}
    <div style="font-size:14px;margin-top:4px"><strong>TOTAL: ${sym} ${Number(t.amount_total).toFixed(2)}</strong></div>
    <div>Pagado: ${sym} ${Number(t.amount_paid).toFixed(2)} | Vuelto: ${sym} ${Number(t.change).toFixed(2)}</div>
    <hr/>
    <div class="center" style="font-size:11px">${t.ticket_footer || ''}<br/>Consulta: ${t.cpe_url}</div>
  `;
  const waText = encodeURIComponent(`Hola ${t.partner}, aquí tienes tu ${t.doc_badge} ${t.name} por ${sym} ${Number(t.amount_total).toFixed(2)} de ${t.company_name}: ${t.cpe_url}`);
  document.getElementById('btnWaShare').href = `https://wa.me/${(t.partner_phone || '').replace(/\D/g, '')}?text=${waText}`;
  document.getElementById('ticketModal').classList.remove('hidden');
}

function openCashModal() { document.getElementById('cashModal').classList.remove('hidden'); }
async function saveCashMove() {
  const res = await postApi('cash_move', {
    session_id: AUTH.sessionId,
    move_type: document.getElementById('cmType').value,
    amount: parseFloat(document.getElementById('cmAmt').value || '0'),
    note: document.getElementById('cmNote').value
  });
  if (res.error) { alert(res.error); return; }
  closeModal('cashModal');
  refreshFromServer();
}

async function openHistoryModal() {
  const res = await postApi('tickets', { session_id: AUTH.sessionId });
  const sym = POS.company_info.currency_symbol || 'S/';
  document.getElementById('historyList').innerHTML = (res.tickets || []).map(tk => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #EEF0F4">
      <div><strong>${tk.name}</strong> · ${tk.partner}<br/><span style="font-size:11.5px;color:var(--muted)">${tk.date} · ${sym} ${tk.amount.toFixed(2)}</span></div>
      <div style="display:flex;gap:6px">
        <button class="btn btn-sec btn-sm" onclick="reprint(${tk.id})">Ver</button>
        ${tk.payment_state !== 'reversed' ? `<button class="btn btn-err btn-sm" onclick="voidDoc(${tk.id}, '${tk.name}')">NC</button>` : '<span style="font-size:11px;color:var(--err)">Anulado</span>'}
      </div>
    </div>
  `).join('') || '<div style="color:var(--muted);padding:16px">Sin comprobantes en este turno.</div>';
  document.getElementById('historyModal').classList.remove('hidden');
}
async function reprint(id) {
  const res = await postApi('ticket_detail', { move_id: id });
  if (res.ticket) { closeModal('historyModal'); showTicket(res.ticket); }
}
async function voidDoc(id, name) {
  if (!confirm(`¿Emitir Nota de Crédito para anular ${name}?`)) return;
  const res = await postApi('credit_note', { move_id: id, session_id: AUTH.sessionId, reason: 'Anulación desde POS Express App' });
  if (res.error) { alert(res.error); return; }
  alert(`Nota de Crédito emitida: ${res.credit_note_name}`);
  openHistoryModal();
  refreshFromServer();
}

function openCloseModal() {
  const sym = POS.company_info.currency_symbol || 'S/';
  document.getElementById('closeSummary').innerHTML = `
    <div><strong>Turno:</strong> ${POS.session_name}</div>
    <div><strong>Fondo Inicial:</strong> ${sym} ${Number(POS.opening_balance || 0).toFixed(2)}</div>
    <div><strong>Ventas Efectivo:</strong> ${sym} ${Number(POS.cash_total || 0).toFixed(2)}</div>
    <div><strong>Ventas Bancos / Yape / Plin:</strong> ${sym} ${Number(POS.bank_total || 0).toFixed(2)}</div>
    <div style="margin-top:6px;font-size:14px"><strong>Efectivo Esperado: ${sym} ${Number(POS.cash_expected || 0).toFixed(2)}</strong></div>
  `;
  document.getElementById('clCounted').value = Number(POS.cash_expected || 0).toFixed(2);
  document.getElementById('closeModal').classList.remove('hidden');
}
async function confirmCloseSession() {
  const res = await postApi('close_session', {
    session_id: AUTH.sessionId,
    counted_cash: parseFloat(document.getElementById('clCounted').value || '0'),
    note: document.getElementById('clNote').value
  });
  if (res.error) { alert(res.error); return; }
  alert(`Turno ${res.session_name} cerrado. Diferencia: S/ ${res.difference.toFixed(2)}`);
  doLogout();
}

function toggleMobileView(showCart) { document.getElementById('workspace').classList.toggle('show-cart', showCart); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

if (AUTH && POS) {
  document.getElementById('fServer').value = AUTH.serverUrl;
  bootTerminal();
}
