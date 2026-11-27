(function() {
    'use strict';

    // ── Helper de Apertura y Cierre de Modales (CSS + Bootstrap friendly) ──
    function wangoOpenModal(modalEl) {
        if (!modalEl) return;
        if (window.bootstrap && window.bootstrap.Modal) {
            try {
                var inst = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                inst.show();
                return;
            } catch(e) {}
        }
        if (window.$ && $.fn && $.fn.modal) {
            try { $(modalEl).modal('show'); return; } catch(e) {}
        }
        document.querySelectorAll('#wango-loc-backdrop').forEach(function(b){b.remove();});
        var bk = document.createElement('div');
        bk.id = 'wango-loc-backdrop';
        bk.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1050;cursor:pointer;';
        document.body.appendChild(bk);
        bk.addEventListener('click', function(){ wangoCloseModal(modalEl); });
        modalEl.style.display = 'block';
        modalEl.style.zIndex  = '1055';
        modalEl.classList.add('show');
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
    }

    function wangoCloseModal(modalEl) {
        if (!modalEl) return;
        if (window.bootstrap && window.bootstrap.Modal) {
            try { var inst = bootstrap.Modal.getInstance(modalEl); if (inst) { inst.hide(); return; } } catch(e) {}
        }
        if (window.$ && $.fn && $.fn.modal) {
            try { $(modalEl).modal('hide'); return; } catch(e) {}
        }
        modalEl.style.display = 'none';
        modalEl.classList.remove('show');
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.querySelectorAll('#wango-loc-backdrop').forEach(function(b){b.remove();});
    }

    // ── Actualizador de Cabecera Falabella (Desktop + Móvil) ──
    function updateHeaderLocation(distName, provName) {
        var desktopText = document.getElementById('falabella_header_location_text');
        var mobileText = document.getElementById('falabella_header_location_mobile_text');
        var displayText = distName ? ('Enviar a ' + distName) : 'Ingresa tu ubicación';

        if (desktopText) {
            desktopText.textContent = displayText;
            if (distName) desktopText.classList.add('font-weight-bold', 'text-dark');
        }
        if (mobileText) {
            mobileText.textContent = displayText;
            if (distName) mobileText.classList.add('text-dark');
        }
    }

    // ── Gestor Global de Ubicación (Modal con GPS + Selector Manual) ──
    function initGlobalLocationModal() {
        var modal   = document.getElementById('wangoProductLocationModal');
        var form    = document.getElementById('wango_product_location_form');
        var selDept = document.getElementById('sel_product_department');
        var selProv = document.getElementById('sel_product_province');
        var selDist = document.getElementById('sel_product_district');

        var btnGps     = document.getElementById('btn_detect_gps_location');
        var btnGpsText = document.getElementById('btn_detect_gps_text');
        var btnGpsIcon = document.getElementById('btn_detect_gps_icon');
        var gpsStatus  = document.getElementById('wango_gps_status_msg');

        var headerBtnDesktop = document.getElementById('falabella_header_location_btn');
        var headerBtnMobile  = document.getElementById('falabella_header_location_mobile');

        var savedAddrsContainer = document.getElementById('wango_user_saved_addresses_container');
        var savedAddrsList      = document.getElementById('wango_user_saved_addresses_list');
        var savedAddrsCount     = document.getElementById('wango_saved_addrs_count');
        var inpExactStreet      = document.getElementById('inp_product_exact_street');
        var inpExactStreet2     = document.getElementById('inp_product_exact_street2');
        var chkSaveToBook       = document.getElementById('chk_save_to_user_book');
        var saveAddrGroup       = document.getElementById('wango_save_addr_switch_group');

        // Sincronizar texto de la cabecera con localStorage al arrancar
        var savedDistName = localStorage.getItem('wango_del_dist_name');
        var savedProvName = localStorage.getItem('wango_del_prov_name');
        var savedExactStreet = localStorage.getItem('wango_del_exact_street');
        updateHeaderLocation(savedDistName, savedProvName);

        // Prellenar inputs de dirección si existen
        if (inpExactStreet && savedExactStreet) {
            inpExactStreet.value = savedExactStreet;
        }

        // Consultar direcciones guardadas del usuario autenticado
        function loadUserSavedAddresses() {
            if (!savedAddrsContainer || !savedAddrsList) return;
            fetch('/shop/delivery/user_addresses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: {} })
            })
            .then(function(res) { return res.json(); })
            .then(function(json) {
                var data = json && json.result ? json.result : null;
                if (!data || !data.logged_in) {
                    savedAddrsContainer.classList.add('d-none');
                    if (saveAddrGroup) saveAddrGroup.classList.add('d-none');
                    return;
                }

                // Usuario autenticado: mostrar opción de guardar en libreta
                if (saveAddrGroup) saveAddrGroup.classList.remove('d-none');

                var addrs = data.addresses || [];
                if (addrs.length === 0) {
                    savedAddrsContainer.classList.add('d-none');
                    return;
                }

                savedAddrsContainer.classList.remove('d-none');
                if (savedAddrsCount) savedAddrsCount.textContent = addrs.length + (addrs.length === 1 ? ' dirección' : ' direcciones');

                var currentDistId = localStorage.getItem('wango_del_dist_id');
                var currentStreet = localStorage.getItem('wango_del_exact_street') || '';

                var html = '';
                addrs.forEach(function(a) {
                    var isSelected = (a.district_id && a.district_id == currentDistId && a.street && a.street === currentStreet);
                    html += '<div class="wango-saved-addr-card p-2.5 px-3 border rounded d-flex align-items-center justify-content-between cursor-pointer ' + (isSelected ? 'border-success bg-light' : 'bg-white') + '" data-addr-id="' + a.id + '" data-dist-id="' + (a.district_id || '') + '" data-dist-name="' + (a.district_name || '') + '" data-prov-id="' + (a.province_id || '') + '" data-prov-name="' + (a.province_name || '') + '" data-dept-id="' + (a.department_id || '') + '" data-dept-name="' + (a.department_name || '') + '" data-street="' + (a.street || '') + '" data-street2="' + (a.street2 || '') + '" style="cursor: pointer; transition: all 0.2s; border-radius: 10px;">';
                    html += '  <div class="d-flex align-items-start" style="gap: 10px;">';
                    html += '    <i class="fa fa-map-marker text-success mt-1" style="font-size: 1.1rem; width: 16px;"/>';
                    html += '    <div>';
                    html += '      <div class="font-weight-bold text-dark small d-flex align-items-center" style="gap: 6px;">';
                    html += '        <span>' + (a.name || 'Mi Dirección') + '</span>';
                    if (a.is_main) {
                        html += '        <span class="badge badge-secondary py-0.5 px-1.5" style="font-size: 0.65rem; background-color: #6c757d; color: white;">Principal</span>';
                    }
                    html += '      </div>';
                    html += '      <div class="text-dark small text-truncate" style="max-width: 280px; font-weight: 500;">' + (a.street || (a.city || 'Sin dirección')) + (a.street2 ? (' - ' + a.street2) : '') + '</div>';
                    html += '      <div class="text-muted" style="font-size: 0.75rem;">' + (a.district_name || a.city || '') + (a.province_name ? (', ' + a.province_name) : '') + '</div>';
                    html += '    </div>';
                    html += '  </div>';
                    html += '  <button type="button" class="btn btn-sm btn-outline-success rounded-pill px-3 py-1 font-weight-bold btn-select-saved-addr" style="font-size: 0.75rem;">Elegir</button>';
                    html += '</div>';
                });

                savedAddrsList.innerHTML = html;

                // Delegar clic de selección de dirección guardada
                savedAddrsList.querySelectorAll('.wango-saved-addr-card, .btn-select-saved-addr').forEach(function(el) {
                    el.addEventListener('click', function(ev) {
                        var card = ev.target.closest('.wango-saved-addr-card');
                        if (!card) return;
                        ev.preventDefault();

                        var dId   = card.getAttribute('data-dist-id');
                        var dName = card.getAttribute('data-dist-name');
                        var pId   = card.getAttribute('data-prov-id');
                        var pName = card.getAttribute('data-prov-name');
                        var sId   = card.getAttribute('data-dept-id');
                        var sName = card.getAttribute('data-dept-name');
                        var strt  = card.getAttribute('data-street');
                        var strt2 = card.getAttribute('data-street2');

                        if (dId) localStorage.setItem('wango_del_dist_id', dId);
                        if (dName) localStorage.setItem('wango_del_dist_name', dName);
                        if (pId) localStorage.setItem('wango_del_prov_id', pId);
                        if (pName) localStorage.setItem('wango_del_prov_name', pName);
                        if (sId) localStorage.setItem('wango_del_dept_id', sId);
                        if (sName) localStorage.setItem('wango_del_dept_name', sName);
                        if (strt) localStorage.setItem('wango_del_exact_street', strt);
                        if (strt2) localStorage.setItem('wango_del_exact_street2', strt2);

                        updateHeaderLocation(dName, pName);

                        window.dispatchEvent(new CustomEvent('wango:location_changed', {
                            detail: {
                                department_id: sId,
                                department_name: sName,
                                province_id: pId,
                                province_name: pName,
                                district_id: dId,
                                district_name: dName,
                                street: strt,
                                street2: strt2
                            }
                        }));

                        wangoCloseModal(modal);
                    });
                });
            })
            .catch(function(err){ console.error("Error loading user addresses:", err); });
        }

        function openModal() {
            if (!modal) return;
            if (selDept && selDept.options.length <= 1) {
                loadDepartments();
            }
            loadUserSavedAddresses();
            if (gpsStatus) {
                gpsStatus.classList.add('d-none');
                gpsStatus.textContent = '';
            }
            wangoOpenModal(modal);
        }

        // Clics en la cabecera (Desktop y Móvil)
        if (headerBtnDesktop) {
            headerBtnDesktop.addEventListener('click', function(e) {
                e.preventDefault();
                openModal();
            });
        }
        if (headerBtnMobile) {
            headerBtnMobile.addEventListener('click', function(e) {
                e.preventDefault();
                openModal();
            });
        }

        // Botones de cerrar en el modal
        if (modal) {
            modal.querySelectorAll('[data-bs-dismiss="modal"],[data-dismiss="modal"]').forEach(function(b) {
                b.addEventListener('click', function(e) {
                    e.preventDefault();
                    wangoCloseModal(modal);
                });
            });
        }

        // 1. Cargar Departamentos
        function loadDepartments() {
            if (!selDept) return;
            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: {} })
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data && data.result && data.result.length > 0) {
                    selDept.innerHTML = '<option value="">Selecciona Departamento...</option>';
                    data.result.forEach(function(s) {
                        var opt = document.createElement('option');
                        opt.value = s.id;
                        opt.textContent = s.name;
                        selDept.appendChild(opt);
                    });
                    var savedDept = localStorage.getItem('wango_del_dept_id');
                    if (savedDept) {
                        selDept.value = savedDept;
                        triggerDepartmentChange(savedDept);
                    }
                }
            })
            .catch(function(err){ console.error("Error loading departments:", err); });
        }

        function triggerDepartmentChange(deptId) {
            if (!selProv || !selDist) return;
            selProv.innerHTML = '<option value="">Selecciona Provincia...</option>';
            selDist.innerHTML = '<option value="">Selecciona Distrito...</option>';
            selProv.disabled = true;
            selDist.disabled = true;
            if (!deptId) return;

            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { department_id: parseInt(deptId) } })
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data && data.result && data.result.length > 0) {
                    data.result.forEach(function(p) {
                        var opt = document.createElement('option');
                        opt.value = p.id;
                        opt.textContent = p.name;
                        selProv.appendChild(opt);
                    });
                    selProv.disabled = false;
                    var savedProv = localStorage.getItem('wango_del_prov_id');
                    if (savedProv) {
                        selProv.value = savedProv;
                        triggerProvinceChange(savedProv);
                    }
                }
            });
        }

        function triggerProvinceChange(provId) {
            if (!selDist) return;
            selDist.innerHTML = '<option value="">Selecciona Distrito...</option>';
            selDist.disabled = true;
            if (!provId) return;

            fetch('/shop/delivery/locations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { province_id: parseInt(provId) } })
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data && data.result && data.result.length > 0) {
                    data.result.forEach(function(d) {
                        var opt = document.createElement('option');
                        opt.value = d.id;
                        opt.textContent = d.name;
                        selDist.appendChild(opt);
                    });
                    selDist.disabled = false;
                    var savedDist = localStorage.getItem('wango_del_dist_id');
                    if (savedDist) {
                        selDist.value = savedDist;
                    }
                }
            });
        }

        if (selDept) {
            selDept.addEventListener('change', function() {
                triggerDepartmentChange(this.value);
            });
        }
        if (selProv) {
            selProv.addEventListener('change', function() {
                triggerProvinceChange(this.value);
            });
        }

        // 2. Formulario Manual Guardar Ubicación
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                var deptId   = selDept.value;
                var deptName = selDept.options[selDept.selectedIndex] ? selDept.options[selDept.selectedIndex].text : '';
                var provId   = selProv.value;
                var provName = selProv.options[selProv.selectedIndex] ? selProv.options[selProv.selectedIndex].text : '';
                var distId   = selDist.value;
                var distName = selDist.options[selDist.selectedIndex] ? selDist.options[selDist.selectedIndex].text : '';

                var exactStreet  = inpExactStreet ? inpExactStreet.value.trim() : '';
                var exactStreet2 = inpExactStreet2 ? inpExactStreet2.value.trim() : '';
                var shouldSaveToBook = chkSaveToBook ? chkSaveToBook.checked : false;

                if (!distId) return;

                localStorage.setItem('wango_del_dept_id', deptId);
                localStorage.setItem('wango_del_dept_name', deptName);
                localStorage.setItem('wango_del_prov_id', provId);
                localStorage.setItem('wango_del_prov_name', provName);
                localStorage.setItem('wango_del_dist_id', distId);
                localStorage.setItem('wango_del_dist_name', distName);
                localStorage.setItem('wango_del_exact_street', exactStreet);
                localStorage.setItem('wango_del_exact_street2', exactStreet2);

                updateHeaderLocation(distName, provName);

                // Si marcó guardar en su cuenta de Odoo y tiene calle
                if (shouldSaveToBook && exactStreet) {
                    fetch('/shop/delivery/save_user_address', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            jsonrpc: "2.0",
                            method: "call",
                            params: {
                                name: exactStreet.slice(0, 30),
                                street: exactStreet,
                                street2: exactStreet2,
                                district_id: parseInt(distId)
                            }
                        })
                    }).catch(function(err){ console.error("Error saving address to book:", err); });
                }

                window.dispatchEvent(new CustomEvent('wango:location_changed', {
                    detail: {
                        department_id: deptId,
                        department_name: deptName,
                        province_id: provId,
                        province_name: provName,
                        district_id: distId,
                        district_name: distName,
                        street: exactStreet,
                        street2: exactStreet2
                    }
                }));

                wangoCloseModal(modal);
            });
        }

        // 3. Geolocalización Automática por GPS (Estilo Mercado Libre)
        if (btnGps) {
            btnGps.addEventListener('click', function(e) {
                e.preventDefault();

                if (!navigator.geolocation) {
                    showGpsMsg('Tu navegador no admite geolocalización. Elige tu distrito abajo.', 'danger');
                    return;
                }

                setGpsLoading(true);

                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        var lat = pos.coords.latitude;
                        var lon = pos.coords.longitude;

                        fetch('/shop/delivery/locate_by_coords', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                jsonrpc: "2.0",
                                method: "call",
                                params: { latitude: lat, longitude: lon }
                            })
                        })
                        .then(function(res) { return res.json(); })
                        .then(function(json) {
                            setGpsLoading(false);
                            var data = (json && json.result) ? json.result : null;

                            if (data && data.success) {
                                // Guardar en localStorage
                                localStorage.setItem('wango_del_dept_id', data.department_id || '');
                                localStorage.setItem('wango_del_dept_name', data.department_name || '');
                                localStorage.setItem('wango_del_prov_id', data.province_id || '');
                                localStorage.setItem('wango_del_prov_name', data.province_name || '');
                                localStorage.setItem('wango_del_dist_id', data.district_id || '');
                                localStorage.setItem('wango_del_dist_name', data.district_name || '');
                                if (data.street) {
                                    localStorage.setItem('wango_del_exact_street', data.street);
                                    if (inpExactStreet) inpExactStreet.value = data.street;
                                }

                                updateHeaderLocation(data.district_name, data.province_name);
                                var feedbackText = '✓ Ubicación detectada: ' + data.district_name + ', ' + data.province_name;
                                if (data.street) feedbackText += ' (' + data.street + ')';
                                showGpsMsg(feedbackText, 'success');

                                window.dispatchEvent(new CustomEvent('wango:location_changed', {
                                    detail: {
                                        department_id: data.department_id,
                                        department_name: data.department_name,
                                        province_id: data.province_id,
                                        province_name: data.province_name,
                                        district_id: data.district_id,
                                        district_name: data.district_name,
                                        street: data.street || ''
                                    }
                                }));

                                setTimeout(function() {
                                    wangoCloseModal(modal);
                                    if (gpsStatus) gpsStatus.classList.add('d-none');
                                }, 1000);
                            } else {
                                showGpsMsg((data && data.message) ? data.message : 'No se pudo identificar el distrito. Elige manualmente abajo.', 'warning');
                            }
                        })
                        .catch(function(err) {
                            setGpsLoading(false);
                            console.error("GPS API error:", err);
                            showGpsMsg('Error al conectar con el servidor. Elige manualmente abajo.', 'danger');
                        });
                    },
                    function(err) {
                        setGpsLoading(false);
                        var msg = 'No se pudo obtener tu ubicación GPS.';
                        if (err.code === 1) {
                            msg = 'Permiso denegado. Activa el GPS de tu celular o selecciona manualmente abajo.';
                        } else if (err.code === 2) {
                            msg = 'Ubicación no disponible. Selecciona manualmente abajo.';
                        } else if (err.code === 3) {
                            msg = 'Tiempo agotado al obtener GPS. Selecciona manualmente abajo.';
                        }
                        showGpsMsg(msg, 'warning');
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 9000,
                        maximumAge: 60000
                    }
                );
            });
        }

        function setGpsLoading(isLoading) {
            if (!btnGps) return;
            btnGps.disabled = isLoading;
            if (isLoading) {
                if (btnGpsIcon) btnGpsIcon.className = 'fa fa-spinner fa-spin text-success';
                if (btnGpsText) btnGpsText.textContent = 'Detectando tu ubicación...';
                showGpsMsg('Obteniendo coordenadas por satélite / red...', 'info');
            } else {
                if (btnGpsIcon) btnGpsIcon.className = 'fa fa-crosshairs text-success';
                if (btnGpsText) btnGpsText.textContent = 'Usar mi ubicación actual (GPS)';
            }
        }

        function showGpsMsg(text, type) {
            if (!gpsStatus) return;
            gpsStatus.classList.remove('d-none', 'text-success', 'text-danger', 'text-warning', 'text-info');
            if (type === 'success') gpsStatus.classList.add('text-success', 'font-weight-bold');
            else if (type === 'danger') gpsStatus.classList.add('text-danger', 'font-weight-bold');
            else if (type === 'warning') gpsStatus.classList.add('text-warning', 'font-weight-bold');
            else gpsStatus.classList.add('text-info');
            gpsStatus.textContent = text;
        }

        // Cargar departamentos de fondo
        if (selDept && selDept.options.length <= 1) {
            loadDepartments();
        }
    }

    // ── Widget de Producto E-Commerce (Página de Producto) ──
    function initProductWidget() {
        var widget = document.getElementById('wango_product_delivery_widget');
        if (!widget) return;

        var productId    = parseInt(widget.getAttribute('data-product-id'));
        var locationSpan = document.getElementById('wango_widget_selected_location');
        var changeLink   = document.getElementById('wango_widget_change_location_link');
        var noLocState   = document.getElementById('wango_widget_no_location_state');
        var optionsContainer = document.getElementById('wango_widget_options_container');

        var pickupStatus    = document.getElementById('wango_pickup_status_msg');
        var viewBranchesLink = document.getElementById('wango_widget_view_branches');
        var homeCost        = document.getElementById('wango_home_delivery_cost');
        var homeTime        = document.getElementById('wango_home_delivery_time');
        var agencyCost      = document.getElementById('wango_agency_cost');
        var agencyTime      = document.getElementById('wango_agency_time');

        var locModal        = document.getElementById('wangoProductLocationModal');
        var branchesModal   = document.getElementById('wangoProductBranchesModal');
        var branchesListBody = document.getElementById('wango_product_branches_list_body');

        var optPickup = document.getElementById('wango_opt_pickup');
        var optHome   = document.getElementById('wango_opt_home');
        var optAgency = document.getElementById('wango_opt_agency');

        var currentBranches = [];

        function setActiveRow(row) {
            [optPickup, optHome, optAgency].forEach(function(r) {
                if (r) r.classList.remove('active');
            });
            if (row) row.classList.add('active');
        }

        function openLocModal() {
            wangoOpenModal(locModal);
        }

        if (locationSpan) {
            locationSpan.style.cursor = 'pointer';
            locationSpan.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                openLocModal();
            });
        }
        if (changeLink) {
            changeLink.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                openLocModal();
            });
        }

        if (branchesModal) {
            branchesModal.querySelectorAll('[data-bs-dismiss="modal"],[data-dismiss="modal"]').forEach(function(btn) {
                btn.addEventListener('click', function(e) { e.preventDefault(); wangoCloseModal(branchesModal); });
            });
        }

        var qtyInput = document.querySelector('input[name="add_qty"]');
        if (qtyInput) {
            qtyInput.addEventListener('change', function() {
                var distId = localStorage.getItem('wango_del_dist_id');
                if (distId) {
                    var dept = localStorage.getItem('wango_del_dept_id');
                    var prov = localStorage.getItem('wango_del_prov_id');
                    fetchDeliveryInfo(productId, parseInt(qtyInput.value) || 1, dept, prov, distId);
                }
            });
        }

        // Suscribirse a cambios de ubicación globales (GPS o Selector)
        window.addEventListener('wango:location_changed', function(ev) {
            var data = ev.detail || {};
            var distName = data.district_name || localStorage.getItem('wango_del_dist_name');
            var provName = data.province_name || localStorage.getItem('wango_del_prov_name');
            var distId   = data.district_id   || localStorage.getItem('wango_del_dist_id');
            var provId   = data.province_id   || localStorage.getItem('wango_del_prov_id');
            var deptId   = data.department_id || localStorage.getItem('wango_del_dept_id');

            if (locationSpan && distName) {
                locationSpan.textContent = distName + (provName ? (', ' + provName) : '');
            }
            if (distId) {
                var qty = qtyInput ? (parseInt(qtyInput.value) || 1) : 1;
                fetchDeliveryInfo(productId, qty, deptId, provId, distId);
            }
        });

        // Inicializar estado del widget
        function initProductState() {
            var distId   = localStorage.getItem('wango_del_dist_id');
            var distName = localStorage.getItem('wango_del_dist_name');
            var provName = localStorage.getItem('wango_del_prov_name');

            if (distId && distName) {
                if (locationSpan) locationSpan.textContent = distName + (provName ? (', ' + provName) : '');
                var qty = qtyInput ? (parseInt(qtyInput.value) || 1) : 1;
                var deptId = localStorage.getItem('wango_del_dept_id');
                var provId = localStorage.getItem('wango_del_prov_id');
                fetchDeliveryInfo(productId, qty, deptId, provId, distId);
            } else {
                if (noLocState) noLocState.classList.add('d-none');
                if (optionsContainer) optionsContainer.classList.remove('d-none');
                if (pickupStatus) pickupStatus.textContent = 'Ingresa tu ubicación para ver disponibilidad.';
                if (viewBranchesLink) viewBranchesLink.classList.add('d-none');
                if (homeCost) homeCost.textContent = '--';
                if (homeTime) homeTime.textContent = 'Ingresa tu ubicación para ver costos y plazos.';
                if (agencyCost) agencyCost.textContent = '--';
                if (agencyTime) agencyTime.textContent = 'Ingresa tu ubicación para ver agencias de envío.';
            }
        }

        initProductState();

        function fetchDeliveryInfo(prodId, qty, deptId, provId, distId) {
            if (noLocState) noLocState.classList.add('d-none');
            if (optionsContainer) optionsContainer.classList.remove('d-none');
            if (pickupStatus) pickupStatus.textContent = 'Calculando...';
            if (homeCost) homeCost.textContent = '';
            if (homeTime) homeTime.textContent = 'Calculando...';
            if (agencyCost) agencyCost.textContent = '';
            if (agencyTime) agencyTime.textContent = 'Calculando...';
            if (viewBranchesLink) viewBranchesLink.classList.add('d-none');

            fetch('/shop/delivery/product_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        product_id: prodId,
                        qty: qty,
                        department_id: parseInt(deptId) || false,
                        province_id: parseInt(provId) || false,
                        district_id: parseInt(distId) || false
                    }
                })
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data && data.error) {
                    if (pickupStatus) pickupStatus.innerHTML = '<span class="text-danger">Error al obtener stock</span>';
                    if (homeTime) homeTime.innerHTML = '<span class="text-danger">Error al calcular</span>';
                    if (agencyTime) agencyTime.innerHTML = '<span class="text-danger">Error al calcular</span>';
                    return;
                }

                if (data && data.result) {
                    var res = data.result;

                    // 1. Retiro en Tienda / Agente
                    var storePickup = res.store_pickup || {};
                    if (storePickup.available) {
                        if (pickupStatus) {
                            if (storePickup.time_display) {
                                pickupStatus.innerHTML = '<span class="text-success font-weight-bold">✓ Disponible para retiro</span> <br><small class="text-muted">' + storePickup.time_display + '</small>';
                            } else {
                                pickupStatus.innerHTML = '<span class="text-success font-weight-bold">✓ Disponible para retiro</span>';
                            }
                        }
                        if (viewBranchesLink) viewBranchesLink.classList.remove('d-none');
                        currentBranches = storePickup.branches || [];
                    } else {
                        if (pickupStatus) pickupStatus.innerHTML = '<span class="text-danger">✕ Sin stock en locales de la zona</span>';
                        if (viewBranchesLink) viewBranchesLink.classList.add('d-none');
                        currentBranches = [];
                    }

                    // 2. Despacho a Domicilio
                    var homeDel = res.home_delivery || {};
                    if (homeDel.available) {
                        if (homeCost) homeCost.textContent = homeDel.cost_display || '';
                        if (homeTime) homeTime.textContent = 'Llega en ' + (homeDel.time_display || '');
                        if (optHome) {
                            optHome.style.opacity = '1';
                            optHome.classList.remove('disabled');
                        }
                    } else {
                        if (homeCost) homeCost.textContent = '';
                        if (homeTime) homeTime.innerHTML = '<span class="text-danger">✕ Sin cobertura de reparto directo</span>';
                        if (optHome) {
                            optHome.style.opacity = '0.7';
                            optHome.classList.add('disabled');
                        }
                    }

                    // 3. Envío por Agencia
                    var agencyShip = res.agency_shipping || {};
                    if (agencyShip.available) {
                        if (agencyCost) agencyCost.textContent = agencyShip.cost_display || '';
                        if (agencyTime) agencyTime.textContent = 'Llega en ' + (agencyShip.time_display || '') + ' (' + (agencyShip.name || '') + ')';
                        if (optAgency) {
                            optAgency.style.opacity = '1';
                            optAgency.classList.remove('disabled');
                        }
                        widget.setAttribute('data-cheapest-agency-id', agencyShip.id);
                    } else {
                        if (agencyCost) agencyCost.textContent = '';
                        if (agencyTime) agencyTime.innerHTML = '<span class="text-danger">✕ Envío por agencia no disponible</span>';
                        if (optAgency) {
                            optAgency.style.opacity = '0.7';
                            optAgency.classList.add('disabled');
                        }
                        widget.removeAttribute('data-cheapest-agency-id');
                    }

                    // Selección previa
                    var savedType = localStorage.getItem('wango_selected_delivery_type');
                    if (savedType) {
                        if (savedType === 'home_delivery' && homeDel.available) {
                            setActiveRow(optHome);
                        } else if (savedType === 'agency_shipping' && agencyShip.available) {
                            setActiveRow(optAgency);
                        } else if (savedType === 'store_pickup' && storePickup.available) {
                            var savedBranchId = localStorage.getItem('wango_selected_branch_id');
                            var matchedBranch = (storePickup.branches || []).find(function(b) { return b.id == savedBranchId; });
                            if (matchedBranch && matchedBranch.has_stock) {
                                setActiveRow(optPickup);
                                if (pickupStatus) pickupStatus.innerHTML = '<span class="text-success font-weight-bold">✓ Seleccionado: ' + matchedBranch.name + '</span>';
                            }
                        }
                    } else {
                        setActiveRow(null);
                    }
                }
            })
            .catch(function(err) {
                console.error("Error fetching delivery info:", err);
            });
        }

        // Ver Sucursales / Agentes Wanka Modal
        if (viewBranchesLink) {
            viewBranchesLink.addEventListener('click', function(e) {
                e.preventDefault();
                if (currentBranches.length === 0 || !branchesModal || !branchesListBody) return;

                var html = '';
                var savedBranchId = localStorage.getItem('wango_selected_branch_id');
                var savedType = localStorage.getItem('wango_selected_delivery_type');

                currentBranches.forEach(function(b) {
                    html += '<div class="p-3 mb-2 border rounded" style="background-color: #fcfcfc;">';
                    html += '  <div class="d-flex justify-content-between align-items-center mb-1">';
                    html += '    <div>';
                    if (b.point_type === 'agent') {
                        html += '      <span class="badge badge-success text-white mr-1" style="font-size: 0.75rem; border-radius: 4px; background-color: #28a745;">Agente Wanka</span>';
                    } else {
                        html += '      <span class="badge badge-info text-white mr-1" style="font-size: 0.75rem; border-radius: 4px; background-color: #17a2b8;">Local del Vendedor</span>';
                    }
                    html += '      <span class="font-weight-bold text-dark" style="font-size: 0.95rem;">' + b.name + '</span>';
                    html += '    </div>';
                    html += '    <span class="badge ' + (b.has_stock ? 'badge-light text-success font-weight-bold border' : 'badge-danger') + '" style="font-size: 0.8rem; padding: 4px 8px; border-radius: 6px;">' + (b.has_stock ? 'Gratis' : 'Sin Stock') + '</span>';
                    html += '  </div>';
                    if (b.reference) html += '  <p class="text-primary small mb-1" style="font-weight: 500;"><i class="fa fa-info-circle mr-1"/>Ref: ' + b.reference + '</p>';
                    html += '  <p class="text-muted small mb-1"><i class="fa fa-map-marker text-success mr-1"/>' + b.address + '</p>';
                    if (b.schedule) html += '  <p class="text-muted small mb-1"><i class="fa fa-clock mr-1"/>' + b.schedule + '</p>';
                    if (b.has_stock) {
                        html += '  <div class="text-right mt-2">';
                        if (savedType === 'store_pickup' && savedBranchId == b.id) {
                            html += '    <button type="button" class="btn btn-sm btn-danger rounded-pill px-3 btn-cancel-widget-branch" data-branch-id="' + b.id + '" style="background-color: #dc3545; border: none; font-size: 0.8rem; font-weight: bold;">Cancelar retiro</button>';
                        } else {
                            html += '    <button type="button" class="btn btn-sm btn-success rounded-pill px-3 btn-select-widget-branch" data-branch-id="' + b.id + '" data-branch-name="' + b.name + '" style="background-color: #00a650; border: none; font-size: 0.8rem; font-weight: bold;">Retirar aquí</button>';
                        }
                        html += '  </div>';
                    }
                    html += '</div>';
                });

                branchesListBody.innerHTML = html;
                wangoOpenModal(branchesModal);
            });
        }

        // Clics en filas de entrega
        if (optPickup) {
            optPickup.addEventListener('click', function(e) {
                if (e.target.id === 'wango_widget_view_branches') return;
                var distId = localStorage.getItem('wango_del_dist_id');
                if (!distId) {
                    openLocModal();
                    return;
                }
                if (currentBranches.length > 0 && viewBranchesLink) {
                    viewBranchesLink.click();
                }
            });
        }

        if (optHome) {
            optHome.addEventListener('click', function() {
                var distId = localStorage.getItem('wango_del_dist_id');
                if (!distId) {
                    openLocModal();
                    return;
                }
                if (optHome.classList.contains('disabled')) return;
                setActiveRow(optHome);
                localStorage.setItem('wango_selected_delivery_type', 'home_delivery');
                localStorage.removeItem('wango_selected_branch_id');
                localStorage.removeItem('wango_selected_agency_id');
                sessionStorage.removeItem('wango_delivery_applied');
            });
        }

        if (optAgency) {
            optAgency.addEventListener('click', function() {
                var distId = localStorage.getItem('wango_del_dist_id');
                if (!distId) {
                    openLocModal();
                    return;
                }
                if (optAgency.classList.contains('disabled')) return;
                setActiveRow(optAgency);
                localStorage.setItem('wango_selected_delivery_type', 'agency_shipping');
                var agencyId = widget.getAttribute('data-cheapest-agency-id');
                if (agencyId) {
                    localStorage.setItem('wango_selected_agency_id', agencyId);
                }
                localStorage.removeItem('wango_selected_branch_id');
                sessionStorage.removeItem('wango_delivery_applied');
            });
        }

        // Selección y Cancelación de Sucursales
        document.addEventListener('click', function(ev) {
            var btn = ev.target.closest('.btn-select-widget-branch');
            if (btn) {
                ev.preventDefault();
                var branchId = btn.getAttribute('data-branch-id');
                var branchName = btn.getAttribute('data-branch-name');

                localStorage.setItem('wango_selected_delivery_type', 'store_pickup');
                localStorage.setItem('wango_selected_branch_id', branchId);
                localStorage.removeItem('wango_selected_agency_id');
                sessionStorage.removeItem('wango_delivery_applied');

                setActiveRow(optPickup);
                if (pickupStatus) pickupStatus.innerHTML = '<span class="text-success font-weight-bold">✓ Seleccionado: ' + branchName + '</span>';
                wangoCloseModal(branchesModal);
                return;
            }

            var cancelBtn = ev.target.closest('.btn-cancel-widget-branch');
            if (cancelBtn) {
                ev.preventDefault();
                localStorage.removeItem('wango_selected_delivery_type');
                localStorage.removeItem('wango_selected_branch_id');
                sessionStorage.removeItem('wango_delivery_applied');
                initProductState();
                wangoCloseModal(branchesModal);
                return;
            }
        });
    }

    // Inicializar siempre
    function onReady() {
        initGlobalLocationModal();
        initProductWidget();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', onReady);
    } else {
        onReady();
    }
})();
