/**
 * Order Placement with Stripe Checkout (hosted page) Integration
 * OnlinePharmacy
 */
document.addEventListener('DOMContentLoaded', async () => {
    const orderForm = document.getElementById('order-form');
    const formError = document.getElementById('form-error');
    const orderSuccessMessage = document.getElementById('order-success-message');
    const successText = document.getElementById('success-text');
    const summaryItemsContainer = document.getElementById('summary-items');
    const summaryTotalPriceEl = document.getElementById('summary-total-price');
    const submitBtn = document.getElementById('place-order');
    const btnText = document.getElementById('btn-text');

    const optionCod = document.getElementById('option-cod');
    const optionStripe = document.getElementById('option-stripe');
    const stripeInfoBox = document.getElementById('stripe-info-box');

    let cartItems = [];
    let cartTotal = 0;

    // ─── Helpers ───
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

    function getUrlParam(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    // ─── Check for Stripe redirect result ───
    const paymentResult = getUrlParam('payment');
    const returnedOrderId = getUrlParam('order_id');

    if (paymentResult === 'success' && returnedOrderId) {
        // Stripe payment was successful — show success banner
        document.getElementById('payment-success-banner')?.classList.remove('hidden');
        if (orderForm) orderForm.classList.add('hidden');
        if (orderSuccessMessage) {
            orderSuccessMessage.classList.remove('hidden');
            if (successText) {
                successText.textContent = `Buyurtma #${returnedOrderId} muvaffaqiyatli to'landi va tasdiqlandi!`;
            }
        }
        if (window.updateCartBadge) window.updateCartBadge();
        return; // Don't load cart or render form
    }

    if (paymentResult === 'cancelled' && returnedOrderId) {
        document.getElementById('payment-cancelled-banner')?.classList.remove('hidden');
    }

    // ─── Toggle Payment Method UI ───
    document.querySelectorAll('input[name="payment_method"]').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'online_stripe') {
                optionStripe?.classList.add('active');
                optionCod?.classList.remove('active');
                stripeInfoBox?.classList.add('show');
                if (btnText) btnText.textContent = "Stripe to'lov sahifasiga o'tish";
            } else {
                optionCod?.classList.add('active');
                optionStripe?.classList.remove('active');
                stripeInfoBox?.classList.remove('show');
                if (btnText) btnText.textContent = "Buyurtmani tasdiqlash";
            }
        });
    });

    // ─── Load Cart Summary from Backend API ───
    async function loadOrderSummary() {
        try {
            const headers = {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            };
            const token = localStorage.getItem('access_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const res = await fetch('/api/v1/cart/summary/', {
                credentials: 'same-origin',
                headers: headers
            });

            if (res.status === 401 || res.status === 403) {
                // User not logged in — try to render empty and show message
                summaryItemsContainer.innerHTML = `
                    <div style="text-align: center; padding: 1.5rem; color: #64748b;">
                        <i class="fas fa-sign-in-alt"></i> 
                        Buyurtma berish uchun avval <a href="/auth/" style="color:#2563eb; font-weight:600;">tizimga kiring</a>.
                    </div>
                `;
                if (summaryTotalPriceEl) summaryTotalPriceEl.textContent = '0 so\'m';
                if (submitBtn) submitBtn.disabled = true;
                return;
            }

            const data = await res.json();
            cartItems = data.items || [];
            cartTotal = data.cart_total || 0;

            if (cartItems.length === 0) {
                summaryItemsContainer.innerHTML = `
                    <div style="text-align: center; padding: 1.5rem; color: #64748b;">
                        <i class="fas fa-shopping-cart"></i> 
                        Savatchangiz bo'sh. <a href="/shop/" style="color:#2563eb; font-weight:600;">Do'konga o'tish</a>
                    </div>
                `;
                if (summaryTotalPriceEl) summaryTotalPriceEl.textContent = '0 so\'m';
                if (submitBtn) submitBtn.disabled = true;
                return;
            }

            if (submitBtn) submitBtn.disabled = false;

            summaryItemsContainer.innerHTML = cartItems.map(item => `
                <div class="summary-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                    <span style="flex: 1;">
                        <strong>${item.product_name}</strong>
                        <span style="color:#64748b; font-size:0.85rem;"> × ${item.quantity}</span>
                    </span>
                    <span style="font-weight: 600; color: #2563eb; white-space: nowrap;">${formatPrice(item.subtotal)} so'm</span>
                </div>
            `).join('');

            if (summaryTotalPriceEl) {
                summaryTotalPriceEl.textContent = `${formatPrice(cartTotal)} so'm`;
            }
        } catch (err) {
            console.error('Order summary load error:', err);
            summaryItemsContainer.innerHTML = `<p style="color:#ef4444;"><i class="fas fa-exclamation-triangle"></i> Savatchani yuklashda xatolik.</p>`;
        }
    }

    // ─── Handle Order Submission ───
    orderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formError.textContent = '';

        const formData = new FormData(orderForm);
        const address = formData.get('address');
        const paymentMethod = formData.get('payment_method');

        if (!address) {
            formError.textContent = 'Iltimos, yetkazib berish manzilini kiriting.';
            return;
        }

        if (cartItems.length === 0) {
            formError.textContent = 'Savatchangiz bo\'sh. Avval mahsulot qo\'shing.';
            return;
        }

        submitBtn.disabled = true;
        if (btnText) btnText.textContent = 'Rasmiylashtirilmoqda...';
        submitBtn.querySelector('i')?.setAttribute('class', 'fas fa-spinner fa-spin');

        try {
            // Step 1: Create Order via atomic checkout
            const checkoutHeaders = {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            };
            const token = localStorage.getItem('access_token');
            if (token) {
                checkoutHeaders['Authorization'] = `Bearer ${token}`;
            }

            const name = formData.get('name') || '';
            const phone = formData.get('phone') || '';

            // Validate optional phone number format if provided
            if (phone && !/^\+998\d{9}$/.test(phone)) {
                formError.textContent = "Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak.";
                submitBtn.disabled = false;
                submitBtn.querySelector('i')?.setAttribute('class', 'fas fa-check-circle');
                if (btnText) {
                    btnText.textContent = paymentMethod === 'online_stripe'
                        ? "Stripe to'lov sahifasiga o'tish"
                        : "Buyurtmani tasdiqlash";
                }
                return;
            }

            const checkoutRes = await fetch('/api/v1/checkout/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: checkoutHeaders,
                body: JSON.stringify({
                    address: address,
                    name: name,
                    phone: phone
                })
            });

            const checkoutData = await checkoutRes.json();

            if (!checkoutRes.ok || !checkoutData.success) {
                throw new Error(checkoutData.error || 'Buyurtma rasmiylashtirishda xatolik yuz berdi.');
            }

            const orderId = checkoutData.order_id;

            // Step 2: If Stripe selected — create Checkout Session and redirect
            if (paymentMethod === 'online_stripe') {
                if (btnText) btnText.textContent = "Stripe sahifasiga yo'naltirilmoqda...";

                const sessionHeaders = {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                };
                if (token) {
                    sessionHeaders['Authorization'] = `Bearer ${token}`;
                }

                const sessionRes = await fetch('/api/v1/payments/checkout-session/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: sessionHeaders,
                    body: JSON.stringify({ order_id: orderId })
                });

                const sessionData = await sessionRes.json();

                if (!sessionRes.ok || !sessionData.success || !sessionData.checkout_url) {
                    throw new Error(sessionData.error || 'Stripe to\'lov sahifasini yaratishda xatolik.');
                }

                // Redirect to Stripe's hosted checkout page
                window.location.href = sessionData.checkout_url;
                return; // Don't reset button — page is redirecting
            }

            // Step 3: Cash on delivery — show success immediately
            if (window.updateCartBadge) window.updateCartBadge();
            orderForm.classList.add('hidden');
            orderSuccessMessage.classList.remove('hidden');
            if (successText) {
                successText.textContent = `Buyurtmangiz #${orderId} muvaffaqiyatli qabul qilindi! Yetkazib berishda naqd to'laysiz.`;
            }

        } catch (error) {
            console.error('Order error:', error);
            formError.textContent = error.message || 'Xatolik yuz berdi. Iltimos qaytadan urinib ko\'ring.';
            submitBtn.disabled = false;
            submitBtn.querySelector('i')?.setAttribute('class', 'fas fa-check-circle');
            if (btnText) {
                btnText.textContent = paymentMethod === 'online_stripe'
                    ? "Stripe to'lov sahifasiga o'tish"
                    : "Buyurtmani tasdiqlash";
            }
        }
    });

    // ─── Init ───
    await loadOrderSummary();
});
