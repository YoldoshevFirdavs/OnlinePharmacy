document.addEventListener('DOMContentLoaded', () => {
    const orderForm = document.getElementById('order-form');
    const formError = document.getElementById('form-error');
    const orderSuccessMessage = document.getElementById('order-success-message');
    
    const summaryItemsContainer = document.getElementById('summary-items');
    const summaryTotalPriceEl = document.getElementById('summary-total-price');

    let cart = JSON.parse(localStorage.getItem('cart')) || [];

    function renderOrderSummary() {
        if (cart.length === 0) {
            // If the cart is empty, maybe redirect to the shop page.
            window.location.href = '/shop/';
            return;
        }

        const summaryHTML = cart.map(item => `
            <div class="summary-item">
                <span>${item.name} (x${item.quantity})</span>
                <span>${formatPrice(item.price * item.quantity)} so'm</span>
            </div>
        `).join('');

        summaryItemsContainer.innerHTML = summaryHTML;

        const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        summaryTotalPriceEl.textContent = formatPrice(totalPrice) + ' so'm';
    }

    orderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formError.textContent = '';
        
        const formData = new FormData(orderForm);
        const orderData = {
            customer_name: formData.get('name'),
            customer_email: formData.get('email'),
            customer_phone: formData.get('phone'),
            delivery_address: formData.get('address'),
            payment_method: formData.get('payment_method'),
            order_items: cart.map(item => ({
                product: item.id,
                quantity: item.quantity
            }))
        };

        try {
            // I'll assume a global `apiPost` function exists, as seen in api.js
            const response = await apiPost('/api/orders/', orderData);

            if (response.status === 201) { // 201 Created
                // Order successful
                localStorage.removeItem('cart'); // Clear the cart
                orderForm.classList.add('hidden');
                orderSuccessMessage.classList.remove('hidden');
            } else {
                // Handle non-201 success responses if any, or other errors
                const errorData = response.data || {};
                const errorMessage = Object.values(errorData).flat().join(' ');
                formError.textContent = errorMessage || 'Buyurtma berishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.';
            }
        } catch (error) {
            formError.textContent = error.message || 'Server bilan bog'lanishda xatolik yuz berdi.';
        }
    });

    function formatPrice(price) {
        return new Intl.NumberFormat('uz-UZ').format(price);
    }

    renderOrderSummary();
});
