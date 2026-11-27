(function() {
    'use strict';

    // ════════════════════════════════════════════════════════════════
    // WANGO DELIVERY CHECKOUT — v4 (Bootstrap-independent modal)
    // ════════════════════════════════════════════════════════════════

    // Abre el modal SIN depender de Bootstrap en absoluto
    function wangoOpenModal(modalEl) {
        if (!modalEl) { console.error('[WanGO] Modal element is null'); return; }

        // Limpiar cualquier backdrop anterior
        document.querySelectorAll('.wango-backdrop, #wango-modal-backdrop').forEach(function(b){ b.remove(); });

        // Mostrar modal con CSS directo (override de todo)
        modalEl.removeAttribute('style');
        modalEl.style.display = 'block';
        modalEl.style.zIndex  = '1055';
        modalEl.classList.add('show');

        // Backdrop oscuro
        var backdrop = document.createElement('div');
        backdrop.id = 'wango-modal-backdrop';
        backdrop.style.cssText = [
            'position:fixed', 'top:0', 'left:0',
            'width:100%', 'height:100%',
            'background:rgba(0,0,0,0.5)',
            'z-index:1050',
            'cursor:pointer'
        ].join(';');
        document.body.appendChild(backdrop);

        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';

        // Cerrar al hacer clic en backdrop
        backdrop.addEventListener('click', function() { wangoCloseModal(modalEl); });

        try {
            if (window._wangoInitAndResizeMap) {
                window._wangoInitAndResizeMap();
            }
        } catch(e) {}

        console.log('[WanGO] Modal abierto OK');
    }

    function wangoCloseModal(modalEl) {
        if (!modalEl) return;
        modalEl.style.display = 'none';
        modalEl.classList.remove('show');
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.querySelectorAll('#wango-modal-backdrop, .wango-backdrop').forEach(function(b){ b.remove(); });
    }

    // ── Punto de entrada ──────────────────────────────────────────────
    function init() {
        console.log('[WanGO] delivery_checkout.js v4 loaded. readyState=' + document.readyState);

        var card = document.getElementById('wango_delivery_checkout_card');
        if (!card) {
            console.log('[WanGO] No en página de checkout, saliendo.');
            return;
        }
        console.log('[WanGO] Card encontrada, inicializando...');

        var modal    = document.getElementById('wangoDeliveryModal');
        var selDept  = document.getElementById('sel_department');
        var selProv  = document.getElementById('sel_province');
        var selDist  = document.getElementById('sel_district');
        var branchList   = document.getElementById('wango_branch_list');
        var homeResult   = document.getElementById('wango_home_delivery_result');
        var agencyResult = document.getElementById('wango_agency_result');
        var payButton    = document.getElementById('o_payment_form_pay');

        console.log('[WanGO] modal=' + (modal ? 'OK' : 'NULL'));
        console.log('[WanGO] sel_department=' + (selDept ? 'OK' : 'NULL'));
        console.log('[WanGO] sel_province=' + (selProv ? 'OK' : 'NULL'));
        console.log('[WanGO] sel_district=' + (selDist ? 'OK' : 'NULL'));

        if (!modal) {
            console.error('[WanGO] #wangoDeliveryModal no encontrado en el DOM. El template puede no haberse renderizado.');
            return;
        }

        // ── Botones de cierre dentro del modal ────────────────────────────
        modal.querySelectorAll('[data-bs-dismiss="modal"],[data-dismiss="modal"]').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                wangoCloseModal(modal);
            });
        });
        document.addEventListener('click', function(e) {
            var closeBtn = e.target.closest('[data-dismiss="modal"], [data-bs-dismiss="modal"]');
            if (closeBtn) {
                var m = closeBtn.closest('.modal');
                if (m) {
                    e.preventDefault();
                    wangoCloseModal(m);
                }
            }
        });

        // ── Botones que abren el modal ─────────────────────────────────────
        // Buscamos en todo el card los botones con data-target o data-bs-target
        function wireOpenButtons() {
            var triggers = document.querySelectorAll(
                '[data-target="#wangoDeliveryModal"],[data-bs-target="#wangoDeliveryModal"]'
            );
            console.log('[WanGO] Botones de apertura encontrados: ' + triggers.length);
            triggers.forEach(function(btn) {
                // Clonar para remover listeners anteriores
                var newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                newBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[WanGO] Botón modal click detectado');
                    if (selDept && selDept.options.length <= 1) loadDepartments();
                    wangoOpenModal(modal);
                });
            });
        }
        wireOpenButtons();

        // ── Tabs Switching (Retiro / Despacho / Agencia) ───────────────────
        var tabLinks = modal.querySelectorAll('#deliveryTabs a');
        tabLinks.forEach(function(tabLink) {
            tabLink.addEventListener('click', function(e) {
                e.preventDefault();
                tabLinks.forEach(function(t) {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tabLink.classList.add('active');
                tabLink.setAttribute('aria-selected', 'true');

                var targetSel = tabLink.getAttribute('href');
                modal.querySelectorAll('#deliveryTabContent .tab-pane').forEach(function(pane) {
                    pane.classList.remove('show', 'active');
                });
                var activePane = modal.querySelector(targetSel);
                if (activePane) {
                    activePane.classList.add('show', 'active');
                }
                if (targetSel === '#content-pickup') {
                    if (window._wangoInitAndResizeMap) window._wangoInitAndResizeMap();
                }
            });
        });

        // ── Si el pedido ya tiene un método de entrega seleccionado ────────
        function unblockPayButtons() {
            var buttons = document.querySelectorAll(
                '#o_payment_form_pay, .o_payment_form_pay, button[name="o_payment_submit_button"], button.o_payment_submit_button, #o_payment_form_pay button, .btn-primary[type="submit"], button[type="submit"], a.btn-primary'
            );
            buttons.forEach(function(b) {
                if (b.innerText && (b.innerText.includes('Pagar') || b.innerText.includes('Pay') || b.id === 'o_payment_form_pay')) {
                    b.removeAttribute('disabled');
                    b.disabled = false;
                    b.classList.remove('disabled');
                    b.style.pointerEvents = 'auto';
                    b.style.cursor = 'pointer';
                    b.style.opacity = '1';
                }
            });
        }

        var summaryEl = document.getElementById('wango_delivery_summary');
        if (summaryEl && !summaryEl.classList.contains('d-none')) {
            unblockPayButtons();
            setInterval(unblockPayButtons, 500);
        }

        // ── Mapa Leaflet ──────────────────────────────────────────────────
        var map = null;
        var markersGroup = null;
        function initMap() {
            var mapContainer = document.getElementById('wango_leaflet_map');
            if (map || typeof L === 'undefined' || !mapContainer) return;
            try {
                // Si Leaflet ya tenía una instancia previa
                if (mapContainer._leaflet_id) {
                    return;
                }
                map = L.map('wango_leaflet_map').setView([-12.046374, -77.042793], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19, attribution: '© OpenStreetMap'
                }).addTo(map);
                markersGroup = L.layerGroup().addTo(map);
                console.log('[WanGO] Mapa Leaflet inicializado');
            } catch(e) { console.warn('[WanGO] Error mapa:', e); }
        }

        window._wangoInitAndResizeMap = function() {
            if (!map) initMap();
            setTimeout(function() {
                if (map) map.invalidateSize();
            }, 200);
            setTimeout(function() {
                if (map) map.invalidateSize();
            }, 600);
        };

        // Inicializar mapa cuando el modal esté visible
        modal.addEventListener('shown.bs.modal', function() {
            window._wangoInitAndResizeMap();
        });
        // Fallback: vigilar si el modal se hace visible manualmente
        document.addEventListener('click', function() {
            setTimeout(function() {
                if (modal.classList.contains('show')) {
                    window._wangoInitAndResizeMap();
                }
            }, 300);
        });

        // ── Auto-aplicar envío guardado ────────────────────────────────────
        (function autoApply() {
            var savedType = localStorage.getItem('wango_selected_delivery_type');
            var savedDist = localStorage.getItem('wango_del_dist_id');
            if (!savedType || !savedDist) return;
            if (sessionStorage.getItem('wango_delivery_applied') === 'true') return;

            var payload = {
                delivery_type: savedType,
                department_id: parseInt(localStorage.getItem('wango_del_dept_id')) || 0,
                province_id:   parseInt(localStorage.getItem('wango_del_prov_id'))  || 0,
                district_id:   parseInt(savedDist)
            };
            if (savedType === 'store_pickup') {
                var bi = localStorage.getItem('wango_selected_branch_id');
                if (!bi) return;
                payload.store_branch_id = parseInt(bi);
            } else if (savedType === 'agency_shipping') {
                var ai = localStorage.getItem('wango_selected_agency_id');
                if (!ai) return;
                payload.agency_id = parseInt(ai);
            }
            sessionStorage.setItem('wango_delivery_applied', 'true');
            fetch('/shop/delivery/select', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc:'2.0', method:'call', params: payload})
            }).then(function(r){ return r.json(); })
              .then(function(d){ if (d && d.result && !d.result.error) window.location.reload(); })
              .catch(function(){});
        })();

        // ── Cargar departamentos ───────────────────────────────────────────
        function loadDepartments(callback) {
            if (!selDept) return;
            selDept.innerHTML = '<option value="">Cargando departamentos...</option>';
            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{}})
            })
            .then(function(r){ return r.json(); })
            .then(function(data) {
                console.log('[WanGO] Respuesta departamentos:', JSON.stringify(data).substring(0, 200));
                selDept.innerHTML = '<option value="">Selecciona Departamento...</option>';
                if (data && data.result && data.result.length > 0) {
                    data.result.forEach(function(s) {
                        var o = document.createElement('option');
                        o.value = s.id; o.textContent = s.name;
                        selDept.appendChild(o);
                    });
                    console.log('[WanGO] ' + data.result.length + ' departamentos cargados');
                    // Restaurar selección previa
                    var sd    = localStorage.getItem('wango_del_dept_id');
                    var sp    = localStorage.getItem('wango_del_prov_id');
                    var sdist = localStorage.getItem('wango_del_dist_id');
                    if (sd) {
                        selDept.value = sd;
                        loadProvinces(sd, function() {
                            if (sp && selProv) {
                                selProv.value = sp;
                                loadDistricts(sp, function() {
                                    if (sdist && selDist) {
                                        selDist.value = sdist;
                                        selDist.dispatchEvent(new Event('change'));
                                    }
                                });
                            }
                        });
                    }
                } else {
                    console.warn('[WanGO] Sin departamentos. Respuesta:', JSON.stringify(data));
                    selDept.innerHTML = '<option value="">⚠ Sin datos — actualiza el módulo</option>';
                }
                if (callback) callback();
            })
            .catch(function(err) {
                console.error('[WanGO] Error fetch departamentos:', err);
                if (selDept) selDept.innerHTML = '<option value="">Error de conexión</option>';
            });
        }

        function loadProvinces(deptId, callback) {
            if (!selProv || !selDist || !deptId) return;
            selProv.innerHTML = '<option value="">Selecciona Provincia...</option>';
            selDist.innerHTML = '<option value="">Selecciona Distrito...</option>';
            selProv.disabled = true; selDist.disabled = true;
            clearResults();
            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{department_id: parseInt(deptId)}})
            })
            .then(function(r){ return r.json(); })
            .then(function(data) {
                if (data && data.result && data.result.length > 0) {
                    data.result.forEach(function(p) {
                        var o = document.createElement('option');
                        o.value = p.id; o.textContent = p.name;
                        selProv.appendChild(o);
                    });
                    selProv.disabled = false;
                }
                if (callback) callback();
            });
        }

        function loadDistricts(provId, callback) {
            if (!selDist || !provId) return;
            selDist.innerHTML = '<option value="">Selecciona Distrito...</option>';
            selDist.disabled = true;
            clearResults();
            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{province_id: parseInt(provId)}})
            })
            .then(function(r){ return r.json(); })
            .then(function(data) {
                if (data && data.result && data.result.length > 0) {
                    data.result.forEach(function(d) {
                        var o = document.createElement('option');
                        o.value = d.id; o.textContent = d.name;
                        selDist.appendChild(o);
                    });
                    selDist.disabled = false;
                }
                if (callback) callback();
            });
        }

        loadDepartments();

        if (selDept) selDept.addEventListener('change', function() { loadProvinces(this.value); });
        if (selProv) selProv.addEventListener('change', function() { loadDistricts(this.value); });

        if (selDist) {
            selDist.addEventListener('change', function() {
                var val = this.value;
                clearResults();
                if (!val) return;
                if (selDept && selDept.value) localStorage.setItem('wango_del_dept_id', selDept.value);
                if (selProv && selProv.value) localStorage.setItem('wango_del_prov_id', selProv.value);
                localStorage.setItem('wango_del_dist_id', val);
                var dstOpt = selDist.options[selDist.selectedIndex];
                var pOpt   = selProv ? selProv.options[selProv.selectedIndex] : null;
                if (dstOpt) localStorage.setItem('wango_del_dist_name', dstOpt.text);
                if (pOpt)   localStorage.setItem('wango_del_prov_name', pOpt.text);

                showSkeletons();

                fetch('/shop/delivery/branches', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({jsonrpc:'2.0',method:'call',params:{district_id:parseInt(val)}})
                }).then(function(r){return r.json();}).then(function(d){renderBranches(d.result||[]);});

                fetch('/shop/delivery/calculate', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({jsonrpc:'2.0',method:'call',params:{
                        department_id: parseInt(selDept ? selDept.value : 0),
                        province_id:   parseInt(selProv  ? selProv.value  : 0),
                        district_id:   parseInt(val)
                    }})
                }).then(function(r){return r.json();}).then(function(d){
                    if (d && d.result) { renderHomeDelivery(d.result.home_delivery); renderAgencies(d.result.agencies||[]); }
                });
            });
        }

        // ── UI helpers ────────────────────────────────────────────────────
        function clearResults() {
            var msg = '<div class="text-center py-4 text-muted"><i class="fa fa-info-circle mb-2 d-block" style="font-size:1.5rem"></i>Selecciona tu ubicación para ver opciones.</div>';
            if (branchList)   branchList.innerHTML   = msg;
            if (homeResult)   homeResult.innerHTML   = msg;
            if (agencyResult) agencyResult.innerHTML = msg;
            if (markersGroup) markersGroup.clearLayers();
        }

        function showSkeletons() {
            var sk = '<div class="wango-skeleton-line"></div><div class="wango-skeleton-line" style="width:80%"></div><div class="wango-skeleton-line" style="width:60%"></div>';
            if (branchList)   branchList.innerHTML   = sk;
            if (homeResult)   homeResult.innerHTML   = sk;
            if (agencyResult) agencyResult.innerHTML = sk;
        }

        function renderBranches(branches) {
            if (!branchList) return;
            branchList.innerHTML = '';
            if (markersGroup) markersGroup.clearLayers();
            if (!branches.length) {
                branchList.innerHTML = '<div class="text-center py-4 text-muted"><i class="fa fa-info-circle mb-2 d-block" style="font-size:1.5rem"></i>Sin tiendas en esta zona.</div>';
                return;
            }
            var bounds = [];
            branches.forEach(function(b) {
                var div = document.createElement('div');
                div.className = 'wango-branch-card' + (b.stock_available ? '' : ' disabled');
                div.setAttribute('data-id', b.id);
                var h = '<div class="d-flex justify-content-between align-items-start mb-2">';
                h += '<h6 class="fw-bold mb-0">' + b.name + '</h6><span class="fw-bold text-success">' + b.cost_display + '</span></div>';
                h += '<p class="text-muted small mb-2"><i class="fa fa-map-marker me-1"></i>' + b.address + '</p>';
                h += '<p class="text-muted small mb-2"><i class="fa fa-clock-o me-1"></i>' + (b.schedule||'') + '</p>';
                h += '<div class="d-flex align-items-center justify-content-between pt-2 border-top">';
                h += '<span class="small fw-bold ' + (b.stock_available?'text-success':'text-danger') + '">' + b.stock_message + '</span>';
                if (b.stock_available) h += '<button type="button" class="btn btn-sm btn-success rounded-pill px-3 btn-select-branch" style="background:#00a650;border:none;font-size:.8rem;font-weight:bold">Retirar aquí</button>';
                h += '</div>';
                div.innerHTML = h;
                branchList.appendChild(div);
                if (map && b.latitude && b.longitude) {
                    var mk = L.marker([b.latitude,b.longitude]).bindPopup('<b>'+b.name+'</b><br>'+b.address);
                    markersGroup.addLayer(mk); bounds.push([b.latitude,b.longitude]);
                    div.addEventListener('click', function(e) {
                        if (e.target.classList.contains('btn-select-branch')) return;
                        if (!b.stock_available) return;
                        map.setView([b.latitude,b.longitude],16); mk.openPopup();
                        document.querySelectorAll('.wango-branch-card').forEach(function(c){c.classList.remove('active');});
                        div.classList.add('active');
                    });
                }
            });
            if (!map) initMap();
            if (map) {
                setTimeout(function() { if (map) map.invalidateSize(); }, 200);
                if (bounds.length) {
                    map.fitBounds(bounds, {padding: [30, 30]});
                } else {
                    map.setView([-12.065, -75.205], 13);
                }
            }
        }

        function renderHomeDelivery(d) {
            if (!homeResult) return;
            if (!d || !d.available) {
                homeResult.innerHTML = '<div class="alert alert-warning py-3 text-center" style="border-radius:10px"><i class="fa fa-info-circle me-2"></i>' + ((d&&d.message)||'Sin cobertura en esta zona.') + '</div>';
                return;
            }
            var h = '<div class="card border p-4 text-center" style="border-radius:12px;max-width:450px;margin:0 auto">';
            h += '<h5 class="fw-bold mb-3">Servicio de Delivery</h5>';
            h += '<div class="d-flex justify-content-between mb-3 border-bottom pb-3"><span class="text-muted">Costo:</span><span class="h4 fw-bold mb-0" style="color:#00a650">'+d.cost_display+'</span></div>';
            h += '<div class="d-flex justify-content-between mb-4"><span class="text-muted">Plazo:</span><span class="fw-bold">'+d.time_display+'</span></div>';
            if (d.cost>0&&d.free_shipping_min>0) h += '<div class="alert alert-info py-2 px-3 mb-4 small" style="border-radius:8px"><i class="fa fa-info-circle me-1"></i>Envío Gratis en compras mayores a S/ '+d.free_shipping_min.toFixed(2)+'</div>';
            else if (d.cost===0&&d.free_shipping_min>0) h += '<div class="alert alert-success py-2 px-3 mb-4 small" style="border-radius:8px"><i class="fa fa-check-circle me-1"></i>¡Envío Gratis aplicado!</div>';
            h += '<button type="button" class="btn btn-success w-100 rounded-pill fw-bold btn-select-home" style="background:#00a650;border:none">Confirmar entrega a domicilio</button></div>';
            homeResult.innerHTML = h;
        }

        function renderAgencies(agencies) {
            if (!agencyResult) return;
            if (!agencies.length) { agencyResult.innerHTML = '<div class="alert alert-warning py-3 text-center" style="border-radius:10px"><i class="fa fa-info-circle me-2"></i>Sin agencias para esta zona.</div>'; return; }
            var h = '<h5 class="fw-bold mb-3" style="font-size:1rem"><i class="fa fa-plane text-success me-2"></i>Agencias disponibles:</h5><div class="row" style="gap:1rem 0">';
            agencies.forEach(function(ag) {
                h += '<div class="col-md-6"><div class="wango-agency-card border p-3 d-flex align-items-center justify-content-between">';
                h += '<div class="d-flex align-items-center gap-3"><img src="'+ag.logo+'" alt="'+ag.name+'" style="width:54px;height:54px;object-fit:contain;border:1px solid #eee;border-radius:6px">';
                h += '<div><h6 class="fw-bold mb-1">'+ag.name+'</h6><p class="text-muted small mb-0"><i class="fa fa-clock-o me-1"></i>'+ag.time_display+'</p></div></div>';
                h += '<div class="text-end d-flex flex-column align-items-end" style="gap:.5rem"><span class="fw-bold fs-5">'+ag.cost_display+'</span>';
                h += '<button type="button" class="btn btn-sm btn-success rounded-pill px-3 btn-select-agency" data-agency-id="'+ag.id+'" style="background:#00a650;border:none;font-size:.8rem;font-weight:bold">Elegir</button></div></div></div>';
            });
            agencyResult.innerHTML = h + '</div>';
        }

        // ── Seleccionar método de envío ───────────────────────────────────
        function postDeliverySelection(payload, onFail) {
            sessionStorage.setItem('wango_delivery_applied','true');
            localStorage.setItem('wango_selected_delivery_type', payload.delivery_type);
            if (payload.store_branch_id) localStorage.setItem('wango_selected_branch_id', payload.store_branch_id);
            if (payload.agency_id)       localStorage.setItem('wango_selected_agency_id', payload.agency_id);
            if (payload.department_id)   localStorage.setItem('wango_del_dept_id', payload.department_id);
            if (payload.province_id)     localStorage.setItem('wango_del_prov_id', payload.province_id);
            if (payload.district_id)     localStorage.setItem('wango_del_dist_id', payload.district_id);

            fetch('/shop/delivery/select', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({jsonrpc:'2.0',method:'call',params:payload})
            }).then(function(r){ return r.json(); }).then(function(data) {
                if (!data) {
                    if (onFail) onFail();
                    return;
                }
                var res = data.result || {};
                if (res.error) {
                    alert(res.error);
                    if (onFail) onFail();
                    return;
                }
                var emptyEl   = document.getElementById('wango_delivery_empty_state');
                var summaryEl = document.getElementById('wango_delivery_summary');
                if (emptyEl)   emptyEl.classList.add('d-none');
                if (summaryEl) summaryEl.classList.remove('d-none');
                var labels = {store_pickup:'Retiro en tienda',home_delivery:'Despacho a domicilio',agency_shipping:'Recibir en agencia'};
                var badge  = document.getElementById('wango_delivery_badge_type');
                var title  = document.getElementById('wango_delivery_title_desc');
                var addr   = document.getElementById('wango_delivery_sub_addr');
                var dateEl = document.getElementById('wango_delivery_sub_date');
                var costEl = document.getElementById('wango_delivery_summary_cost');
                if (badge)  badge.textContent  = labels[payload.delivery_type]||'';
                if (title)  title.textContent  = res.summary_html;
                if (costEl) costEl.textContent = res.shipping_cost_display;
                if (addr) {
                    if (payload.delivery_type==='store_pickup') {
                        var sc = document.querySelector('[data-id="'+payload.store_branch_id+'"]');
                        addr.innerHTML = '<i class="fa fa-map-marker me-1"></i> '+(sc&&sc.querySelector('p')?sc.querySelector('p').textContent:'');
                    } else if (payload.delivery_type==='home_delivery') {
                        addr.innerHTML = '<i class="fa fa-map-marker me-1"></i> Dirección de Envío';
                    } else {
                        addr.innerHTML = '<i class="fa fa-building-o me-1"></i> Encomienda / Agencia';
                    }
                }
                if (dateEl) {
                    if (res.estimated_date_display) { dateEl.innerHTML='<i class="fa fa-calendar me-1"></i> Entrega: '+res.estimated_date_display; dateEl.classList.remove('d-none'); }
                    else dateEl.classList.add('d-none');
                }
                if (payButton) payButton.removeAttribute('disabled');
                wangoCloseModal(modal);
                window.location.reload();
            }).catch(function(err){
                console.error('[WanGO] Error postDelivery:', err);
                alert('No se pudo guardar la opción de entrega. Intenta nuevamente.');
                if (onFail) onFail();
            });
        }

        // ── Delegación de clicks (buttons de selección) ───────────────────
        document.addEventListener('click', function(ev) {
            var btnB = ev.target.closest('.btn-select-branch');
            if (btnB) {
                ev.preventDefault();
                var cd = btnB.closest('.wango-branch-card');
                if (cd) {
                    var oldHtml = btnB.innerHTML;
                    btnB.disabled = true;
                    btnB.innerHTML = '<i class="fa fa-spinner fa-spin mr-1 me-1"></i> Guardando...';
                    postDeliverySelection({
                        delivery_type: 'store_pickup',
                        store_branch_id: parseInt(cd.getAttribute('data-id')),
                        department_id: parseInt(selDept ? selDept.value : 0),
                        province_id:   parseInt(selProv  ? selProv.value  : 0),
                        district_id:   parseInt(selDist  ? selDist.value  : 0)
                    }, function() {
                        btnB.disabled = false;
                        btnB.innerHTML = oldHtml;
                    });
                }
                return;
            }
            var btnH = ev.target.closest('.btn-select-home');
            if (btnH) {
                ev.preventDefault();
                var oldHtmlH = btnH.innerHTML;
                btnH.disabled = true;
                btnH.innerHTML = '<i class="fa fa-spinner fa-spin mr-1 me-1"></i> Guardando...';
                postDeliverySelection({
                    delivery_type: 'home_delivery',
                    department_id: parseInt(selDept ? selDept.value : 0),
                    province_id:   parseInt(selProv  ? selProv.value  : 0),
                    district_id:   parseInt(selDist  ? selDist.value  : 0)
                }, function() {
                    btnH.disabled = false;
                    btnH.innerHTML = oldHtmlH;
                });
                return;
            }
            var btnA = ev.target.closest('.btn-select-agency');
            if (btnA) {
                ev.preventDefault();
                var oldHtmlA = btnA.innerHTML;
                btnA.disabled = true;
                btnA.innerHTML = '<i class="fa fa-spinner fa-spin mr-1 me-1"></i> Guardando...';
                postDeliverySelection({
                    delivery_type: 'agency_shipping',
                    agency_id:     parseInt(btnA.getAttribute('data-agency-id')),
                    department_id: parseInt(selDept ? selDept.value : 0),
                    province_id:   parseInt(selProv  ? selProv.value  : 0),
                    district_id:   parseInt(selDist  ? selDist.value  : 0)
                }, function() {
                    btnA.disabled = false;
                    btnA.innerHTML = oldHtmlA;
                });
                return;
            }
        });
    }

    // ── Iniciar cuando el DOM esté listo ──────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
