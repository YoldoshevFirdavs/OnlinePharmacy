/**
 * Checkout & Cart Manager
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
        div.style.bottom = '24px';
        div.style.right = '24px';
        div.style.padding = '14px 24px';
        div.style.background = isError ? '#e74c3c' : '#2ecc71';
        div.style.color = '#ffffff';
        div.style.borderRadius = '8px';
        div.style.boxShadow = '0 6px 20px rgba(0,0,0,0.2)';
        div.style.zIndex = '99999';
        div.style.fontWeight = '500';
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 4000);
    }

    async function executeCheckout(address = '') {
        const btn = document.getElementById('proceed-to-order') || document.getElementById('btn-checkout');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buyurtma rasmiylashtirilmoqda...';
        }

        try {
            const res = await fetch('/api/v1/checkout/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ address: address })
            });

            const data = await res.json();

            if (res.status === 401) {
                window.location.href = '/auth/';
                return;
            }

            if (res.ok && data.success) {
                showToast(`Buyurtmangiz muvaffaqiyatli qabul qilindi! Buyurtma ID: #${data.order_id}`);
                localStorage.removeItem('cart');
                if (window.updateCartBadge) window.updateCartBadge();
                setTimeout(() => {
                    window.location.href = '/order/';
                }, 1500);
            } else {
                showToast(data.error || 'Rasmiylashtirishda xatolik yuz berdi.', true);
            }
        } catch (err) {
            console.error('Checkout error:', err);
            showToast('Tarmoqda xatolik yuz berdi. Qaytadan urinib ko\'ring.', true);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Rasmiylashtirishga o\'tish <i class="fas fa-arrow-right"></i>';
            }
        }
    }

    window.executeCheckout = executeCheckout;

    document.addEventListener('DOMContentLoaded', function() {
        const checkoutBtn = document.getElementById('proceed-to-order');
        if (checkoutBtn) {
            checkoutBtn.addEventListener('click', function(e) {
                // If direct API checkout is desired on cart page:
                // executeCheckout();
            });
        }
    });
})();
