/**
 * Header Cart Badge Manager
 * OnlinePharmacy
 */
(function () {
    'use strict';

    function updateCartBadge() {
        const cartIcon = document.getElementById('cartIcon');
        const cartCount = document.getElementById('header-cart-count');

        const headers = {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        fetch('/api/v1/cart/summary/', {
            credentials: 'same-origin',
            headers: headers
        })
        .then(res => {
            if (!res.ok) {
                if (cartIcon && (res.status === 401 || res.status === 403)) {
                    cartIcon.style.display = 'none';
                }
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;
            const count = data.item_count || 0;
            if (cartCount) {
                cartCount.textContent = count;
            }
            if (cartIcon) {
                cartIcon.style.display = 'inline-flex';
            }
        })
        .catch(() => {});
    }

    document.addEventListener('DOMContentLoaded', updateCartBadge);
    window.updateCartBadge = updateCartBadge;
})();
