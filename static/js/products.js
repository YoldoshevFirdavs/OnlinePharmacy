// Check authentication
if (!isAuthenticated()) {
    window.location.href = '../auth.html';
}

// Global state
let products = [];
let categories = [];
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let currentPage = 1;
let currentCategory = 'all';
let currentSort = 'newest';

// DOM Elements
const productsGrid = document.getElementById('productsGrid');
const categoryList = document.getElementById('categoryList');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const sortSelect = document.getElementById('sortSelect');
const minPriceInput = document.getElementById('minPrice');
const maxPriceInput = document.getElementById('maxPrice');
const applyFilterBtn = document.getElementById('applyFilter');
const cartBtn = document.getElementById('cartBtn');
const cartSidebar = document.getElementById('cartSidebar');
const closeCartBtn = document.getElementById('closeCart');
const overlay = document.getElementById('overlay');
const cartItems = document.getElementById('cartItems');
const cartTotal = document.getElementById('cartTotal');
const cartCount = document.querySelector('.cart-count');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const logoutBtn = document.getElementById('logoutBtn');
const sectionTitle = document.getElementById('sectionTitle');

// Initialize
init();

async function init() {
    await loadCategories();
    await loadProducts();
    updateCartUI();
    setupEventListeners();
}

// Load categories
async function loadCategories() {
    try {
        const data = await api.getCategories();
        categories = data.results || data;
        renderCategories();
    } catch (error) {
        console.error('Categories error:', error);
    }
}

// Render categories
function renderCategories() {
    const categoryHTML = categories.map(cat => `
        <label class="category-item">
            <input type="radio" name="category" value="${cat.id}">
            <span>${cat.name}</span>
        </label>
    `).join('');
    
    categoryList.innerHTML += categoryHTML;
    
    // Add event listeners
    document.querySelectorAll('input[name="category"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentCategory = e.target.value;
            currentPage = 1;
            loadProducts();
        });
    });
}

// Load products
async function loadProducts() {
    loading.style.display = 'block';
    emptyState.style.display = 'none';
    productsGrid.innerHTML = '';
    
    try {
        const params = {
            page: currentPage,
            ordering: getSortParam(),
        };
        
        if (currentCategory !== 'all') {
            params.category = currentCategory;
        }
        
        const search = searchInput.value.trim();
        if (search) {
            params.search = search;
        }
        
        const minPrice = minPriceInput.value;
        const maxPrice = maxPriceInput.value;
        if (minPrice) params.min_price = minPrice;
        if (maxPrice) params.max_price = maxPrice;
        
        const data = await api.getProducts(params);
        products = data.results || data;
        
        loading.style.display = 'none';
        
        if (products.length === 0) {
            emptyState.style.display = 'block';
        } else {
            renderProducts();
        }
    } catch (error) {
        console.error('Products error:', error);
        loading.style.display = 'none';
        emptyState.style.display = 'block';
    }
}

// Get sort parameter
function getSortParam() {
    const sortMap = {
        'newest': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'popular': '-views_count'
    };
    return sortMap[currentSort] || '-created_at';
}

// Render products
function renderProducts() {
    const productsHTML = products.map(product => `
        <div class="product-card" data-id="${product.id}">
            ${product.flash_sale ? '<span class="product-badge">Aksiya</span>' : ''}
            <img src="${product.image || 'https://via.placeholder.com/250'}" alt="${product.name}" class="product-image">
            <div class="product-info">
                <div class="product-category">${product.category_name || 'Dori'}</div>
                <h3 class="product-name">${product.name}</h3>
                <div class="product-price">${formatPrice(product.price)} so'm</div>
                <div class="product-actions">
                    <button class="btn-add-cart" onclick="addToCart(${product.id})">
                        Savatga
                    </button>
                    <button class="btn-view" onclick="viewProduct(${product.id})">
                        Ko'rish
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    productsGrid.innerHTML = productsHTML;
}

// Add to cart
function addToCart(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;
    
    const existingItem = cart.find(item => item.id === productId);
    
    if (existingItem) {
        existingItem.quantity++;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            quantity: 1
        });
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartUI();
    
    // Show notification
    showNotification('Savatga qo\'shildi!');
}

// View product
function viewProduct(productId) {
    window.location.href = `product-detail.html?id=${productId}`;
}

// Update cart UI
function updateCartUI() {
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    cartCount.textContent = totalItems;
    cartTotal.textContent = formatPrice(totalPrice) + ' so\'m';
    
    if (cart.length === 0) {
        cartItems.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">Savatcha bo\'sh</p>';
    } else {
        const cartHTML = cart.map(item => `
            <div class="cart-item">
                <img src="${item.image || 'https://via.placeholder.com/60'}" alt="${item.name}" class="cart-item-image">
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-price">${formatPrice(item.price)} so'm</div>
                    <div class="cart-item-quantity">
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, -1)">-</button>
                        <span>${item.quantity}</span>
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        <button class="qty-btn" onclick="removeFromCart(${item.id})" style="margin-left: auto; color: #ef4444;">O'chirish</button>
                    </div>
                </div>
            </div>
        `).join('');
        
        cartItems.innerHTML = cartHTML;
    }
}

// Update quantity
function updateQuantity(productId, change) {
    const item = cart.find(i => i.id === productId);
    if (!item) return;
    
    item.quantity += change;
    
    if (item.quantity <= 0) {
        removeFromCart(productId);
    } else {
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartUI();
    }
}

// Remove from cart
function removeFromCart(productId) {
    cart = cart.filter(item => item.id !== productId);
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartUI();
}

// Format price
function formatPrice(price) {
    return new Intl.NumberFormat('uz-UZ').format(price);
}

// Show notification
function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

// Setup event listeners
function setupEventListeners() {
    // Search
    searchBtn.addEventListener('click', () => {
        currentPage = 1;
        loadProducts();
    });
    
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentPage = 1;
            loadProducts();
        }
    });
    
    // Sort
    sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        loadProducts();
    });
    
    // Filter
    applyFilterBtn.addEventListener('click', () => {
        currentPage = 1;
        loadProducts();
    });
    
    // Cart
    cartBtn.addEventListener('click', () => {
        cartSidebar.classList.add('active');
        overlay.classList.add('active');
    });
    
    closeCartBtn.addEventListener('click', () => {
        cartSidebar.classList.remove('active');
        overlay.classList.remove('active');
    });
    
    overlay.addEventListener('click', () => {
        cartSidebar.classList.remove('active');
        overlay.classList.remove('active');
    });
    
    // Logout
    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        clearTokens();
        window.location.href = '../auth.html';
    });
    
    // Checkout
    document.getElementById('checkoutBtn').addEventListener('click', () => {
        if (cart.length === 0) {
            alert('Savatcha bo\'sh!');
            return;
        }
        window.location.href = 'checkout.html';
    });
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
