/* ======================================================
   WanGO Store - Frontend Interactive JS
   Ultraligero - Vanilla JS sin dependencias pesadas
   ====================================================== */

document.addEventListener('DOMContentLoaded', function () {
    initWangoSliders();
    initRecentlyViewedTracker();
    initCategoryTrigger();
    initBuyNowHandler();
});

/**
 * 1. Inicializa los controles de deslizamiento horizontal con CSS Scroll
 */
function initWangoSliders() {
    const sliderButtons = document.querySelectorAll('.wango-slider-btn');
    
    sliderButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const targetSelector = this.getAttribute('data-target');
            if (!targetSelector) return;
            
            const track = document.querySelector(targetSelector);
            if (!track) return;
            
            const isPrev = this.classList.contains('wango-slider-prev');
            const scrollDistance = Math.max(track.clientWidth * 0.75, 250);
            
            track.scrollBy({
                left: isPrev ? -scrollDistance : scrollDistance,
                behavior: 'smooth'
            });
        });
    });

    // Detectar scroll para mostrar/ocultar flechas según posición
    const tracks = document.querySelectorAll('.wango-cards-track, .wango-products-slider-track, .wango-categories-track');
    tracks.forEach(track => {
        updateArrowVisibility(track);
        track.addEventListener('scroll', function () {
            updateArrowVisibility(this);
        }, { passive: true });
    });
}

function updateArrowVisibility(track) {
    const wrapper = track.closest('.wango-slider-wrapper');
    if (!wrapper) return;

    const prevBtn = wrapper.querySelector('.wango-slider-prev');
    const nextBtn = wrapper.querySelector('.wango-slider-next');

    if (prevBtn) {
        if (track.scrollLeft > 15) {
            prevBtn.classList.remove('d-none');
        } else {
            prevBtn.classList.add('d-none');
        }
    }

    if (nextBtn) {
        const maxScroll = track.scrollWidth - track.clientWidth;
        if (track.scrollLeft >= maxScroll - 15) {
            nextBtn.classList.add('d-none');
        } else {
            nextBtn.classList.remove('d-none');
        }
    }
}

/**
 * 2. Rastreo de Productos Vistos en Navegador (localStorage)
 */
const STORAGE_KEY = 'wango_recently_viewed_ids';

function initRecentlyViewedTracker() {
    // Si estamos en la página de un producto, guardar su ID
    const productInput = document.querySelector('input[name="product_template_id"]') || 
                         document.querySelector('input.product_template_id') ||
                         document.querySelector('input[name="product_id"]');
    
    if (productInput && productInput.value) {
        saveViewedProduct(productInput.value);
    }

    // Si estamos en la portada con la sección de Visto Recientemente, cargar del historial
    const recentTrack = document.getElementById('wangoRecentTrack');
    if (recentTrack) {
        loadRecentlyViewedIntoHome(recentTrack);
    }
}

function saveViewedProduct(prodId) {
    try {
        const idInt = parseInt(prodId, 10);
        if (isNaN(idInt)) return;

        let history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        // Eliminar si ya existía para ponerlo al principio
        history = history.filter(id => id !== idInt);
        history.unshift(idInt);

        // Guardar hasta un máximo de 15 productos
        if (history.length > 15) {
            history = history.slice(0, 15);
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (e) {
        console.warn('WanGO Tracker localStorage notice:', e);
    }
}

function loadRecentlyViewedIntoHome(trackElement) {
    try {
        const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        if (!history || history.length === 0) {
            // No hay historial aún: la portada ya tiene el fallback del servidor
            return;
        }

        // Consultar el endpoint JSON de Odoo para obtener los productos del historial
        fetch('/wango_store/recently_viewed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    product_ids: history
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data && data.result && data.result.html) {
                trackElement.innerHTML = data.result.html;
                updateArrowVisibility(trackElement);
            }
        })
        .catch(err => {
            console.warn('WanGO Recent Products Fetch Error:', err);
        });
    } catch (e) {
        console.warn('WanGO History parse error:', e);
    }
}

/**
 * 3. Disparador para abrir menú lateral desde la tarjeta de categorías
 */
function initCategoryTrigger() {
    const triggerBtn = document.querySelector('.wbl-menu-btn-trigger');
    if (triggerBtn) {
        triggerBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const sidebarBtn = document.querySelector('.wbl-menu-btn');
            if (sidebarBtn) {
                sidebarBtn.click();
            } else {
                window.location.href = '/shop';
            }
        });
    }
}

/**
 * 4. Botón 'Comprar Ahora': Actualiza carrito vía JSON-RPC oficial y redirige a /shop/checkout
 * 100% infalible: no depende de submits de formulario ni se ve afectado por interceptores.
 */
window.wangoBuyNow = function (btn) {
    var buyBtn = btn || document.getElementById('wango_buy_now_btn');
    if (!buyBtn) return;

    // Feedback visual inmediato y prevención de dobles clics
    buyBtn.classList.add('disabled');
    buyBtn.style.opacity = '0.85';
    buyBtn.style.pointerEvents = 'none';
    buyBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2 mr-2"></i> Redirigiendo a caja...';

    // 1. Obtener ID del producto o variante
    var form = buyBtn.closest('form') || document.querySelector('form[action*="/shop/cart/update"]');
    var prodInput = form ? form.querySelector('input[name="product_id"]') : null;
    var productId = prodInput ? prodInput.value : null;

    if (!productId) {
        var altProd = document.querySelector('input.product_id') || 
                      document.querySelector('#product_details input[name="product_id"]') ||
                      document.querySelector('input[name="product_template_id"]');
        productId = altProd ? altProd.value : null;
    }

    // 2. Obtener cantidad seleccionada en el stepper o sticky
    var qtyDisplay = document.querySelector('#product_details input.quantity') || 
                      document.getElementById('sticky_qty') ||
                      (form ? form.querySelector('input[name="add_qty"]') : null);
    var addQty = qtyDisplay ? parseInt(qtyDisplay.value, 10) : 1;
    if (isNaN(addQty) || addQty < 1) addQty = 1;

    // Si por alguna razón extrema no encontramos productId, fallback a submit
    if (!productId) {
        if (form) {
            var expressInput = form.querySelector('input[name="express"]');
            if (!expressInput) {
                expressInput = document.createElement('input');
                expressInput.type = 'hidden';
                expressInput.name = 'express';
                expressInput.value = '1';
                form.appendChild(expressInput);
            }
            form.submit();
        } else {
            window.location.href = '/shop/checkout';
        }
        return;
    }

    // 3. Agregar producto al carrito usando el endpoint oficial de Odoo /shop/cart/update_json
    fetch('/shop/cart/update_json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            params: {
                product_id: parseInt(productId, 10),
                add_qty: parseInt(addQty, 10)
            }
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        // Redirigir directamente a la pantalla de checkout
        window.location.href = '/shop/checkout';
    })
    .catch(function(err) {
        console.warn('Wango BuyNow fetch fallback:', err);
        window.location.href = '/shop/checkout';
    });
};

/**
 * 5. Botón 'Comprar por WhatsApp': Social Selling automatizado
 * Envía mensaje pre-estructurado con link exacto, precio, total y cantidad a WhatsApp.
 */
window.wangoBuyWhatsApp = function (btn) {
    // 1. Nombre del producto
    var nameEl = document.querySelector('h1[itemprop="name"]') || document.querySelector('h1');
    var productName = nameEl ? nameEl.textContent.trim() : 'Producto';

    // 2. Cantidad seleccionada
    var qtyDisplay = document.querySelector('#product_details input.quantity') || 
                      document.getElementById('sticky_qty');
    var qty = qtyDisplay ? parseInt(qtyDisplay.value, 10) : 1;
    if (isNaN(qty) || qty < 1) qty = 1;

    // 3. Precio unitario y cálculo del total
    var priceValueEl = document.querySelector('.oe_price_value');
    var unitPriceNum = 0;
    var unitPriceText = 'S/ 0.00';

    if (priceValueEl) {
        var priceParent = priceValueEl.closest('.oe_price') || priceValueEl.parentElement;
        var currencyEl = priceParent ? (priceParent.querySelector('.oe_currency_value') || priceParent.querySelector('.currency')) : null;
        var currency = currencyEl ? currencyEl.textContent.trim() : 'S/';
        unitPriceText = currency + ' ' + priceValueEl.textContent.trim();
        unitPriceNum = parseFloat(priceValueEl.textContent.trim().replace(',', '.')) || 0;
    } else {
        var priceEl = document.querySelector('.product_price .oe_price') || document.querySelector('.oe_price');
        unitPriceText = priceEl ? priceEl.textContent.trim() : 'S/ 0.00';
        var numMatch = unitPriceText.match(/[\d.,]+/);
        if (numMatch) {
            unitPriceNum = parseFloat(numMatch[0].replace(',', '.')) || 0;
        }
    }

    var totalPriceText = unitPriceNum > 0 ? ('S/ ' + (unitPriceNum * qty).toFixed(2)) : unitPriceText;

    // 4. Link exacto del producto (limpiando hashes)
    var productUrl = window.location.href.split('#')[0];

    // 5. Teléfono de destino (vendedor o tienda oficial)
    var phone = '';
    var phoneInput = document.getElementById('wango_whatsapp_phone_target');
    if (phoneInput && phoneInput.value) {
        phone = phoneInput.value.replace(/\D/g, '');
    }
    // Si tiene 9 dígitos (formato estándar de celular en Perú), anteponer código país 51
    if (phone.length === 9) {
        phone = '51' + phone;
    }
    // Fallback si no tiene teléfono configurado
    if (!phone) {
        phone = '51964123456';
    }

    // 6. Mensaje optimizado para venta y cierre rápido
    var msg = "¡Hola WanGO! 👋 Deseo realizar la compra de este producto:\n\n" +
              "🛍️ *Producto:* " + productName + "\n" +
              "🔢 *Cantidad:* " + qty + " unidad(es)\n" +
              "💰 *Precio unitario:* " + unitPriceText + "\n" +
              "💵 *Total a pagar:* " + totalPriceText + "\n\n" +
              "🔗 *Ver producto:* " + productUrl + "\n\n" +
              "💳 *Método de pago preferido:* Yape / Plin / Transferencia\n" +
              "¿Me confirman disponibilidad para coordinar el envío de inmediato?";

    var waUrl = "https://wa.me/" + phone + "?text=" + encodeURIComponent(msg);
    window.open(waUrl, '_blank');
};

function initBuyNowHandler() {
    document.addEventListener('click', function (e) {
        // Disparador Comprar Ahora (soporta tanto ID como clase wango-btn-buy-now)
        var buyNowBtn = e.target.closest('#wango_buy_now_btn, .wango-btn-buy-now');
        if (buyNowBtn) {
            e.preventDefault();
            e.stopPropagation();
            window.wangoBuyNow(buyNowBtn);
            return;
        }

        // Disparador Comprar por WhatsApp
        var waBtn = e.target.closest('#wango_whatsapp_btn');
        if (waBtn) {
            e.preventDefault();
            e.stopPropagation();
            window.wangoBuyWhatsApp(waBtn);
            return;
        }
    });
}
