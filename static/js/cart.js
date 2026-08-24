/**
 * Real-time Backend-Synchronized Cart Page Manager
 * OnlinePharmacy
 */
(function() {
    'use strict';

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function formatPrice(price) {
        return new Intl.NumberFormat('uz-UZ').format(price || 0);
    }

    function showToast(msg, isError = false) {
        const div = document.createElement('div');
        div.className = 'toast';
        div.style.position = 'fixed';
        div.style.bottom = '24px';
        div.style.right = '24px';
        div.style.padding = '12px 20px';
        div.style.background = isError ? '#e74c3c' : '#2ecc71';
        div.style.color = '#ffffff';
        div.style.borderRadius = '8px';
        div.style.boxShadow = '0 4px 15px rgba(0,0,0,0.15)';
        div.style.zIndex = '99999';
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }

    async function loadCartFromServer() {
        const cartItemsContainer = document.getElementById('cart-items-container');
        const cartTotalPriceEl = document.getElementById('cart-total-price');
        const countDisplay = document.getElementById('items-count-display');
        const proceedBtn = document.getElementById('proceed-to-order');

        if (!cartItemsContainer) return;

        try {
            const headers = {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            const token = localStorage.getItem('access_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const res = await fetch('/api/v1/cart/summary/', {
                credentials: 'same-origin',
                headers: headers
            });

            if (res.status === 401) {
                cartItemsContainer.innerHTML = `
                    <div class="empty-cart-state" style="text-align: center; padding: 3rem 1rem;">
                        <i class="fas fa-user-lock" style="font-size: 3rem; color: #94a3b8; margin-bottom: 1rem; display: block;"></i>
                        <p style="font-size: 1.1rem; color: #475569; margin-bottom: 1rem;">Savatchani ko'rish uchun tizimga kiring</p>
                        <a href="/auth/" class="btn-secondary" style="display: inline-block; padding: 10px 20px; background: #2563eb; color: #fff; border-radius: 6px; text-decoration: none;">Tizimga kirish</a>
                    </div>
                `;
                if (cartTotalPriceEl) cartTotalPriceEl.textContent = '0 so\'m';
                if (countDisplay) countDisplay.textContent = '0 ta';
                if (proceedBtn) proceedBtn.disabled = true;
                return;
            }

            const data = await res.json();
            const items = data.items || [];
            const itemCount = data.item_count || 0;
            const totalSum = data.cart_total || 0;

            if (countDisplay) countDisplay.textContent = `${itemCount} ta`;
            if (cartTotalPriceEl) cartTotalPriceEl.textContent = `${formatPrice(totalSum)} so'm`;
            if (window.updateCartBadge) window.updateCartBadge();

            if (items.length === 0) {
                cartItemsContainer.innerHTML = `
                    <div class="empty-cart-state" style="text-align: center; padding: 3rem 1rem;">
                        <i class="fas fa-shopping-basket" style="font-size: 3rem; color: #94a3b8; margin-bottom: 1rem; display: block;"></i>
                        <p style="font-size: 1.1rem; color: #475569; margin-bottom: 1rem;">Savatchangiz hozircha bo'sh</p>
                        <a href="/shop/" class="btn-secondary" style="display: inline-block; padding: 10px 20px; background: #2563eb; color: #fff; border-radius: 6px; text-decoration: none;">Do'konga qaytish</a>
                    </div>
                `;
                if (proceedBtn) proceedBtn.disabled = true;
                return;
            }

            if (proceedBtn) proceedBtn.disabled = false;

            cartItemsContainer.innerHTML = items.map(item => `
                <div class="cart-item-card" data-id="${item.product_id}" style="display: flex; gap: 1rem; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; align-items: center;">
                    <div class="cart-item-image-wrap" style="width: 80px; height: 80px; flex-shrink: 0; background: #f8fafc; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center;">
                        <img src="${item.product_image || '/static/images/default_avatar.png'}" alt="${item.product_name}" class="cart-item-image" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/static/images/default_avatar.png'">
                    </div>
                    <div class="cart-item-details" style="flex: 1;">
                        <div class="cart-item-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <h4 class="cart-item-name" style="margin: 0 0 6px; font-size: 1rem; color: #0f172a;">${item.product_name}</h4>
                            <button class="btn-remove-item" onclick="window.removeCartItem(${item.product_id})" aria-label="O'chirish" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.1rem;">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                        <div class="cart-item-footer" style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                            <div class="cart-item-price" style="font-weight: 700; color: #2563eb; font-size: 1rem;">${formatPrice(item.product_price)} so'm</div>
                            <div class="cart-item-quantity-controls" style="display: inline-flex; align-items: center; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                                <button class="qty-control-btn" onclick="window.changeCartQuantity(${item.product_id}, -1)" style="padding: 4px 10px; background: #f1f5f9; border: none; cursor: pointer; font-weight: 700;">−</button>
                                <span class="qty-val" style="padding: 4px 12px; font-weight: 600; font-size: 0.95rem; min-width: 24px; text-align: center;">${item.quantity}</span>
                                <button class="qty-control-btn" onclick="window.changeCartQuantity(${item.product_id}, 1)" style="padding: 4px 10px; background: #f1f5f9; border: none; cursor: pointer; font-weight: 700;">+</button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (err) {
            console.error('Cart load error:', err);
            cartItemsContainer.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 2rem;">Savatchani yuklashda xatolik yuz berdi.</div>`;
        }
    }

    window.changeCartQuantity = async function(productId, delta) {
        try {
            // Call atomic add with delta (1 or -1)
            const res = await fetch('/api/v1/cart/add/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: delta
                })
            });
            if (res.ok) {
                await loadCartFromServer();
            } else {
                const data = await res.json();
                showToast(data.error || 'Xatolik yuz berdi', true);
            }
        } catch (err) {
            showToast('Tarmoqda xatolik', true);
        }
    };

    window.removeCartItem = async function(productId) {
        try {
            const res = await fetch('/api/v1/orders/cart/remove-item/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    product_id: productId
                })
            });
            if (res.ok || res.status === 204) {
                showToast('Mahsulot savatchadan olib tashlandi');
                await loadCartFromServer();
            } else {
                showToast('O\'chirishda xatolik yuz berdi', true);
            }
        } catch (err) {
            showToast('Tarmoqda xatolik', true);
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        loadCartFromServer();

        const proceedBtn = document.getElementById('proceed-to-order');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = '/order/';
            });
        }
    });

    window.loadCartFromServer = loadCartFromServer;
})();
