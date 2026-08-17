document.addEventListener('DOMContentLoaded', () => {
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartTotalPriceEl = document.getElementById('cart-total-price');
    const proceedToOrderBtn = document.getElementById('proceed-to-order');

    let cart = JSON.parse(localStorage.getItem('cart')) || [];

    function renderCart() {
        const countDisplay = document.getElementById('items-count-display');
        if (cart.length === 0) {
            cartItemsContainer.innerHTML = `
                <div class="empty-cart-state">
                    <i class="fas fa-shopping-basket"></i>
                    <p>Savatchangiz hozircha bo'sh</p>
                    <a href="/shop/" class="btn-secondary">Do'konga qaytish</a>
                </div>
            `;
            cartTotalPriceEl.textContent = '0 so\'m';
            if (countDisplay) countDisplay.textContent = '0 ta';
            return;
        }

        const totalItemsCount = cart.reduce((sum, item) => sum + item.quantity, 0);
        if (countDisplay) countDisplay.textContent = `${totalItemsCount} ta`;

        const cartHTML = cart.map(item => `
            <div class="cart-item-card" data-id="${item.id}">
                <div class="cart-item-image-wrap">
                    <img src="${item.image || '/static/images/default_avatar.png'}" alt="${item.name}" class="cart-item-image" onerror="this.src='/static/images/default_avatar.png'">
                </div>
                <div class="cart-item-details">
                    <div class="cart-item-header">
                        <h4 class="cart-item-name">${item.name}</h4>
                        <button class="btn-remove-item" onclick="removeFromCart(${item.id})" aria-label="O'chirish">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    <div class="cart-item-footer">
                        <div class="cart-item-price">${formatPrice(item.price)} so'm</div>
                        <div class="cart-item-quantity-controls">
                            <button class="qty-control-btn" onclick="updateQuantity(${item.id}, -1)">−</button>
                            <span class="qty-val">${item.quantity}</span>
                            <button class="qty-control-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        cartItemsContainer.innerHTML = cartHTML;
        updateTotalPrice();
    }

    function updateTotalPrice() {
        const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        cartTotalPriceEl.textContent = formatPrice(totalPrice) + ' so\'m';
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
    
    if (proceedToOrderBtn) {
        proceedToOrderBtn.addEventListener('click', () => {
            window.location.href = '/order/';
        });
    }

    renderCart();
});
