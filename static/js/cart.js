document.addEventListener('DOMContentLoaded', () => {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartTotalPriceEl = document.getElementById('cart-total-price');
    const proceedToOrderBtn = document.getElementById('proceed-to-order');

    let cart = JSON.parse(localStorage.getItem('cart')) || [];

    function renderCart() {
        if (cart.length === 0) {
            cartItemsContainer.innerHTML = '<p class="empty-cart">Savatchangiz bo'sh.</p>';
            cartTotalPriceEl.textContent = '0 so'm';
            return;
        }

        const cartHTML = cart.map(item => `
            <div class="cart-item" data-id="${item.id}">
                <img src="${item.image || 'https://via.placeholder.com/80'}" alt="${item.name}" class="cart-item-image">
                <div class="cart-item-info">
                    <span class="cart-item-name">${item.name}</span>
                    <span class="cart-item-price">${formatPrice(item.price)} so'm</span>
                    <div class="cart-item-quantity">
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, -1)">-</button>
                        <span>${item.quantity}</span>
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        <button class="remove-item-btn" onclick="removeFromCart(${item.id})">O'chirish</button>
                    </div>
                </div>
            </div>
        `).join('');

        cartItemsContainer.innerHTML = cartHTML;
        updateTotalPrice();
    }

    function updateTotalPrice() {
        const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        cartTotalPriceEl.textContent = formatPrice(totalPrice) + ' so'm';
    }

    window.updateQuantity = function(productId, change) {
        const item = cart.find(i => i.id === productId);
        if (!item) return;

        item.quantity += change;

        if (item.quantity <= 0) {
            removeFromCart(productId);
        } else {
            saveCart();
            renderCart();
        }
    }

    window.removeFromCart = function(productId) {
        cart = cart.filter(item => item.id !== productId);
        saveCart();
        renderCart();
    }

    function saveCart() {
        localStorage.setItem('cart', JSON.stringify(cart));
    }

    function formatPrice(price) {
        return new Intl.NumberFormat('uz-UZ').format(price);
    }
    
    proceedToOrderBtn.addEventListener('click', () => {
        // Redirect to the order page.
        // I will assume the order page is at /order/
        window.location.href = '/order/';
    });

    renderCart();
});
