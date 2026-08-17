 // ============================================
// main.js - Main page dynamic logic
// ============================================

// FIX: Add a reload monitor to prevent loops.
window.__reloadMonitor = {
    count: 0,
    lastReload: 0,
    logAndCheck: function() {
        const now = Date.now();
        if (now - this.lastReload < 5000) { // 5-second threshold
            this.count++;
            console.warn(`[ReloadGuard] Rapid reload detected! Count: ${this.count}. Suppressing.`);
            return false; // Suppress reload
        }
        this.lastReload = now;
        this.count = 1;
        console.log("[ReloadGuard] Reload permitted.");
        return true;
    }
};

// Override location.reload to use the guard
const originalReload = window.location.reload;
window.location.reload = function() {
    if (window.__reloadMonitor.logAndCheck()) {
        originalReload.apply(window.location, arguments);
    }
};


document.addEventListener('DOMContentLoaded', () => {
    // Safely initialize all components
    try {
        initBuyButtons();
    } catch (e) {
        console.error("Error initializing buy buttons:", e);
    }
    
    try {
        initFaq(); // Ensure this is safe if .faq-container doesn't exist
    } catch (e) {
        console.error("Error initializing FAQ:", e);
    }

    try {
        loadPopularProducts(30); // Load popular products for the last 30 days
    } catch (e) {
        console.error("Error loading popular products:", e);
    }
});

/**
 * FEAT: Loads popular products from the API and renders them.
 * @param {number} range - The number of days to look back for popular products.
 */
async function loadPopularProducts(range = 30) {
    const container = document.getElementById('popular-products-grid');
    const loader = document.getElementById('popular-products-loader');

    if (!container) {
        console.warn('Popular products container not found.');
        return;
    }

    try {
        if (loader) loader.style.display = 'block';

        const response = await fetch(`/api/v1/pharmacy/products/popular/?range=${range}`);
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        const products = await response.json();

        if (loader) loader.style.display = 'none';

        if (!products || products.length === 0) {
            container.innerHTML = '<p>Hozircha ommabop mahsulotlar yo‘q.</p>';
            return;
        }

        // Clear loader and render products
        container.innerHTML = '';
        products.forEach(product => {
            const productCard = `
                <div class="product-card">
                    <div class="product-image">
                        <img src="${product.thumbnail || 'https://via.placeholder.com/280x200?text=No+Image'}" alt="${product.name}" style="width:100%; height:100%; object-fit: cover;">
                    </div>
                    <div class="product-info">
                        <h3>${product.name}</h3>
                        <p class="product-desc">${product.short_description || 'Tavsif mavjud emas'}</p>
                        <div class="product-price">${new Intl.NumberFormat('uz-UZ').format(product.price)} so'm</div>
                        <button class="btn btn-primary btn-small btn-buy-mini" data-product-id="${product.id}">Savatga qo'shish</button>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', productCard);
        });

    } catch (error) {
        console.error('Failed to load popular products:', error);
        if (loader) loader.style.display = 'none';
        if (container) container.innerHTML = '<p>Mahsulotlarni yuklashda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko‘ring.</p>';
    }
}


/**
 * FIX: Strengthened initBuyButtons with event delegation and real AJAX call.
 */
function initBuyButtons() {
    const productGrid = document.getElementById('popular-products-grid');
    if (!productGrid) {
        console.warn("Popular products grid not found for buy button delegation.");
        return;
    }

    productGrid.addEventListener('click', async (e) => {
        const button = e.target.closest('.btn-buy-mini'); // More specific target
        if (!button) {
            return;
        }
        
        e.preventDefault();
        
        const card = button.closest('.product-card');

        const productId = button.dataset.productId;
        if (!productId) {
            console.error("Product ID not found on button.");
            return;
        }

        const token = localStorage.getItem('access_token');
        if (!token && confirm('Savatga qo‘shish uchun tizimga kirishingiz kerak. Kirish sahifasiga o‘tasizmi?')) {
            window.location.href = '/auth/';
            return;
        }

        button.disabled = true;
        button.textContent = 'Qo‘shilmoqda...';

        try {
            const response = await fetch('/api/v1/orders/cart/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    medicine_id: productId,
                    quantity: 1
                })
            });

            if (response.ok) {
                const result = await response.json();
                showFeedbackBanner(result.message || 'Mahsulot savatga qo‘shildi!', 'success');
                button.textContent = 'Savatda';
            } else {
                const error = await response.json();
                showFeedbackBanner(error.detail || 'Savatga qo‘shishda xatolik yuz berdi.', 'error');
                button.disabled = false;
                button.textContent = "Savatga qo'shish";
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            showFeedbackBanner('Tarmoq xatosi. Iltimos, qayta urinib ko‘ring.', 'error');
            button.disabled = false;
            button.textContent = "Savatga qo'shish";
        }
    });
}

function initFaq() {
    const faqContainer = document.querySelector('.faq-container');
    if (!faqContainer) return;

    faqContainer.addEventListener('click', (e) => {
        const question = e.target.closest('.faq-question');
        if (question) {
            const item = question.parentElement;
            item.classList.toggle('active');
        }
    });
}

// Helper functions for UI feedback
function showFeedbackBanner(message, type = 'success') {
    const banner = document.createElement('div');
    banner.className = `feedback-banner ${type}`;
    banner.textContent = message;
    document.body.appendChild(banner);
    setTimeout(() => banner.remove(), type === 'error' ? 5000 : 3000);
}

// Inlined Helper to get CSRF token
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