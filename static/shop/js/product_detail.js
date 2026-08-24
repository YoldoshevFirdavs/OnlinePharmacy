/**
 * Product Detail Page Scripts
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

    function showToast(msg, isError = false) {
        const div = document.createElement('div');
        div.className = 'toast';
        div.style.position = 'fixed';
        div.style.bottom = '20px';
        div.style.right = '20px';
        div.style.padding = '12px 20px';
        div.style.background = isError ? '#e74c3c' : '#2ecc71';
        div.style.color = '#fff';
        div.style.borderRadius = '8px';
        div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        div.style.zIndex = '9999';
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }

    function addToCartAJAX(productId, quantity, btnElement) {
        if (btnElement) {
            btnElement.disabled = true;
            btnElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Qo\'shilmoqda...';
        }

        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        };
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        fetch('/api/v1/cart/add/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: headers,
            body: JSON.stringify({
                product_id: productId,
                quantity: quantity
            })
        })
        .then(res => {
            if (res.status === 401) {
                const modal = document.getElementById('login-modal');
                if (modal) modal.classList.add('show');
                else window.location.href = '/auth/';
                throw new Error('Iltimos, avval tizimga kiring.');
            }
            return res.json();
        })
        .then(data => {
            if (data.success || data.item_count !== undefined) {
                showToast('Mahsulot savatchaga qo\'shildi!');
                if (window.updateCartBadge) {
                    window.updateCartBadge();
                }
            } else {
                showToast(data.error || 'Xatolik yuz berdi', true);
            }
        })
        .catch(err => {
            showToast(err.message || 'Xatolik yuz berdi', true);
        })
        .finally(() => {
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = '<i class="fas fa-shopping-cart"></i> Savatchaga qo\'shish';
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        const btnAdd = document.getElementById('btn-add-cart');
        if (btnAdd) {
            btnAdd.addEventListener('click', function(e) {
                e.preventDefault();
                const pId = this.dataset.productId || window.productId;
                const qtyInput = document.getElementById('quantity');
                const qty = qtyInput ? parseInt(qtyInput.value) || 1 : 1;
                addToCartAJAX(pId, qty, this);
            });
        }
    });

    window.addToCartAJAX = addToCartAJAX;
})();
