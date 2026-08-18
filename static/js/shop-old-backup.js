// static/js/shop.js

// ===================== CSRF HELPER =====================
function getCsrfToken() {
    const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
    if (cookieMatch) return decodeURIComponent(cookieMatch[1]);
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) return metaTag.getAttribute('content');
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) return csrfInput.value;
    return '';
}

const DEFAULT_IMG = '/static/images/default_avatar.png';

// ===================== GLOBAL STATE =====================
let allProducts    = [];
let allCategories  = [];
let currentCategory = 'all';
let currentSort    = 'newest';

// ===================== DOM REFS =====================
const shopMainView       = document.getElementById('shop-main-view');
const productDetailView  = document.getElementById('product-detail-view');
const productsGrid       = document.getElementById('productsGrid');
const categoryList       = document.getElementById('categoryList');
const searchInput        = document.getElementById('search-input');
const searchSuggestions  = document.getElementById('search-suggestions');
const sortSelect         = document.getElementById('sortSelect');
const minPriceInput      = document.getElementById('minPrice');
const maxPriceInput      = document.getElementById('maxPrice');
const applyFilterBtn     = document.getElementById('applyFilter');
const loadingEl          = document.getElementById('loading');
const emptyState         = document.getElementById('emptyState');
const pageProductDetail  = document.getElementById('pageProductDetail');
const similarProductsGrid = document.getElementById('similarProductsGrid');
const backToShopBtn      = document.getElementById('back-to-shop');

const recentlyViewedSection = document.getElementById('recently-viewed-section');
const recentlyViewedGrid    = document.getElementById('recently-viewed-grid');

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    setupEventListeners();
    await loadCategories();
    await loadProducts();
    renderRecentlyViewed();
}

// ===================== NAVIGATION =====================
function showListView() {
    productDetailView.style.display = 'none';
    shopMainView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showDetailView() {
    shopMainView.style.display = 'none';
    productDetailView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

if (backToShopBtn) {
    backToShopBtn.addEventListener('click', showListView);
}

// ===================== RECENTLY VIEWED =====================
function renderRecentlyViewed() {
    if (!recentlyViewedSection || !recentlyViewedGrid) return;
    const history = JSON.parse(localStorage.getItem('recently_viewed') || '[]');
    
    if (history.length > 0) {
        recentlyViewedGrid.innerHTML = history.map(item => `
            <div class="product-card" onclick="openProductDetail(${item.id})">
                <div class="product-image-wrap">
                    <img src="${item.image || DEFAULT_IMG}" class="product-image" onerror="this.src='${DEFAULT_IMG}'">
                </div>
                <div class="product-info">
                    <h3 class="product-name">${escapeHtml(item.name)}</h3>
                    <div class="product-price">${formatPrice(item.price)} so'm</div>
                </div>
            </div>
        `).join('');
        recentlyViewedSection.style.display = 'block';
    } else {
        recentlyViewedSection.style.display = 'none';
    }
}

function saveToRecentlyViewed(product) {
    let history = JSON.parse(localStorage.getItem('recently_viewed') || '[]');
    history = history.filter(item => item.id !== product.id);
    history.unshift({
        id: product.id,
        name: product.name,
        price: product.price,
        image: product.main_image || (product.images && product.images.length ? product.images[0].image : DEFAULT_IMG)
    });
    if (history.length > 5) history.pop(); // keep last 5
    localStorage.setItem('recently_viewed', JSON.stringify(history));
    renderRecentlyViewed();
}

// ===================== CATEGORIES — AJAX =====================
async function loadCategories() {
    try {
        const res = await fetch('/api/v1/pharmacy/categories/');
        const data = await res.json();
        allCategories = data.results || data;
        renderCategories();
    } catch (err) {
        console.error('Categories error:', err);
    }
}

function renderCategories() {
    if (!categoryList) return;
    const html = allCategories.map(cat => `
        <label class="category-item" data-value="${cat.id}">
            <input type="radio" name="category" value="${cat.id}">
            <span>${escapeHtml(cat.name)}</span>
        </label>
    `).join('');

    categoryList.innerHTML += html;

    categoryList.querySelectorAll('.category-item').forEach(label => {
        label.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation();
            categoryList.querySelectorAll('.category-item').forEach(l => l.classList.remove('active'));
            label.classList.add('active');
            const radio = label.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
            currentCategory = label.dataset.value || 'all';
        });
    });
}

// ===================== PRODUCTS =====================
async function loadProducts() {
    if (loadingEl) loadingEl.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (productsGrid) productsGrid.innerHTML = '';

    try {
        const params = new URLSearchParams();
        if (currentCategory !== 'all') params.append('category', currentCategory);
        const search = searchInput ? searchInput.value.trim() : '';
        if (search) params.append('search', search);

        if (currentSort === 'price_asc') params.append('ordering', 'price');
        else if (currentSort === 'price_desc') params.append('ordering', '-price');
        else params.append('ordering', '-updated_at');

        const res = await fetch('/api/v1/pharmacy/products/?' + params.toString());
        const data = await res.json();
        allProducts = data.results || data;

        const minP = minPriceInput ? parseFloat(minPriceInput.value) : NaN;
        const maxP = maxPriceInput ? parseFloat(maxPriceInput.value) : NaN;
        let filtered = allProducts;
        if (!isNaN(minP)) filtered = filtered.filter(p => parseFloat(p.price) >= minP);
        if (!isNaN(maxP)) filtered = filtered.filter(p => parseFloat(p.price) <= maxP);

        if (loadingEl) loadingEl.style.display = 'none';
        if (!filtered || filtered.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
        } else {
            renderProducts(filtered, productsGrid);
        }
    } catch (err) {
        console.error('Products error:', err);
        if (loadingEl) loadingEl.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
    }
}

function getProductImg(product) {
    return product.main_image || (product.images && product.images.length ? product.images[0].image : DEFAULT_IMG);
}

function getCategoryName(product) {
    if (typeof product.category === 'object' && product.category) return product.category.name || '';
    return product.category_name || String(product.category || 'Dori');
}

function renderProducts(items, container) {
    if (!container) return;
    const html = items.map(product => {
        const imgSrc = getProductImg(product);
        const shortDesc = product.short_description || '';
        const catName = getCategoryName(product);
        const licenseBadge = product.is_prescription_required ? `<div class="license-badge"><i class="fas fa-shield-alt"></i> Retsept</div>` : '';
        const shortDescOverlay = shortDesc ? `<div class="product-short-desc-overlay">${escapeHtml(shortDesc)}</div>` : '';

        return `
            <div class="product-card" onclick="openProductDetail(${product.id})">
                <div class="product-image-wrap">
                    <img src="${imgSrc}" alt="${escapeHtml(product.name)}" class="product-image" loading="lazy" onerror="this.src='${DEFAULT_IMG}'">
                    ${shortDescOverlay}
                </div>
                <div class="product-info">
                    <div class="product-category">${escapeHtml(catName)}</div>
                    <h3 class="product-name">${escapeHtml(product.name)}</h3>
                    <div class="product-price">${formatPrice(product.price)} so'm</div>
                    ${licenseBadge}
                    <div class="product-purchase-bar" onclick="event.stopPropagation()">
                        <div class="qty-wrap">
                            <button class="qty-btn" onclick="changeQty(this,-1)">−</button>
                            <input type="number" class="product-qty-input" value="1" min="1" max="999" readonly>
                            <button class="qty-btn" onclick="changeQty(this,1)">+</button>
                        </div>
                        <button class="btn-add-to-cart" onclick="addToCart(${product.id}, this)">
                            <i class="fas fa-cart-plus"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    container.innerHTML = html;
}

// ===================== QTY HELPERS =====================
window.changeQty = function(btn, delta) {
    const input = btn.closest('.qty-wrap, .modal-qty-wrap')?.querySelector('.product-qty-input, .modal-qty-input');
    if (!input) return;
    let val = parseInt(input.value) || 1;
    val = Math.max(1, Math.min(999, val + delta));
    input.value = val;
};

// ===================== ADD TO CART =====================
window.addToCart = async function(productId, btnEl) {
    const card = btnEl?.closest('.product-card, .detail-body');
    const qtyInput = card?.querySelector('.product-qty-input, .modal-qty-input');
    const quantity = parseInt(qtyInput?.value) || 1;

    if (!btnEl) return;
    const originalHTML = btnEl.innerHTML;
    btnEl.disabled = true;
    btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    try {
        const csrf = getCsrfToken();
        const token = localStorage.getItem('access_token');
        const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
        if (csrf) headers['X-CSRFToken'] = csrf;
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/v1/orders/cart/', {
            method: 'POST', headers, credentials: 'include',
            body: JSON.stringify({ product_id: productId, quantity }),
        });

        if (res.status === 401 || res.status === 403) {
            showToast(`<i class="fas fa-lock"></i> Iltimos, avval tizimga kiring!`, true);
            return;
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || errData.error || `Xato: ${res.status}`);
        }

        showToast(`<i class="fas fa-check-circle"></i> Savatga qo'shildi!`);
        updateCartBadge();
    } catch (err) {
        showToast(`<i class="fas fa-exclamation-circle"></i> ${err.message || 'Xato yuz berdi'}`, true);
    } finally {
        btnEl.disabled = false;
        btnEl.innerHTML = originalHTML;
    }
};

async function updateCartBadge() {
    try {
        const token = localStorage.getItem('access_token');
        const headers = { 'Accept': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch('/api/v1/orders/cart/', { headers, credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        const count = data.items ? data.items.length : (data.total_items ?? 0);
        const badge = document.getElementById('header-cart-count');
        if (badge) badge.textContent = count;
    } catch (_) {}
}

// ===================== SEARCH SUGGESTIONS =====================
let debounceTimer;
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const q = e.target.value.trim();
        if (!q) {
            if (searchSuggestions) {
                searchSuggestions.style.display = 'none';
                searchSuggestions.innerHTML = '';
            }
            return;
        }
        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/v1/pharmacy/products/?search=${encodeURIComponent(q)}`);
                const data = await res.json();
                const list = (data.results || data).slice(0, 6);
                if (!searchSuggestions) return;
                if (list.length > 0) {
                    searchSuggestions.innerHTML = list.map(item => `
                        <div class="suggestion-card" onclick="handleSuggestionClick(${item.id})">
                            <img src="${item.main_image || DEFAULT_IMG}" onerror="this.src='${DEFAULT_IMG}'">
                            <div class="suggestion-card-info">
                                <div class="suggestion-card-title">${escapeHtml(item.name)}</div>
                                <div class="suggestion-card-price">${formatPrice(item.price)} so'm</div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    searchSuggestions.innerHTML = '<div style="padding:12px;color:#888;text-align:center;">Mahsulot topilmadi</div>';
                }
                searchSuggestions.style.display = 'block';
            } catch (err) {}
        }, 280);
    });
    document.addEventListener('click', (e) => {
        if (!searchInput?.contains(e.target) && !searchSuggestions?.contains(e.target)) {
            if (searchSuggestions) searchSuggestions.style.display = 'none';
        }
    });
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (searchSuggestions) searchSuggestions.style.display = 'none';
            loadProducts();
        }
    });
}

window.handleSuggestionClick = function(id) {
    if (searchSuggestions) searchSuggestions.style.display = 'none';
    openProductDetail(id);
};

// ===================== PRODUCT DETAIL VIEW (SPA) =====================
window.openProductDetail = async function(id) {
    try {
        const res = await fetch(`/api/v1/pharmacy/products/${id}/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const product = await res.json();
        
        saveToRecentlyViewed(product);

        // Try to get main_image from local list or fallback
        let mainImage = product.main_image;
        if (!mainImage) {
            const localProduct = allProducts.find(p => p.id === id);
            if (localProduct && localProduct.main_image) {
                mainImage = localProduct.main_image;
            }
        }
        if (!mainImage && product.images && product.images.length) {
            mainImage = product.images[0].image;
        }
        if (!mainImage) {
            try {
                const listRes = await fetch(`/api/v1/pharmacy/products/`);
                const listData = await listRes.json();
                const items = listData.results || listData;
                const found = items.find(p => p.id === id);
                if (found && found.main_image) {
                    mainImage = found.main_image;
                }
            } catch (e) {}
        }
        const imgSrc = mainImage || DEFAULT_IMG;

        const catName = getCategoryName(product);
        const licenseBadge = product.is_prescription_required ? `<div class="license-badge" style="margin-bottom:15px; font-size:0.9rem;"><i class="fas fa-shield-alt"></i> Retsept talab qilinadi</div>` : '';
        const descHtml = product.short_description ? `<p class="detail-desc"><strong>Tavsif:</strong> ${escapeHtml(product.short_description)}</p>` : '';
        const instrHtml = product.instruction ? `<div class="detail-instruction"><strong>Qo'llash usuli:</strong> ${escapeHtml(product.instruction)}</div>` : '';

        if (pageProductDetail) {
            pageProductDetail.innerHTML = `
                <img src="${imgSrc}" class="detail-img" onerror="this.src='${DEFAULT_IMG}'">
                <div class="detail-body">
                    <h2>${escapeHtml(product.name)}</h2>
                    ${catName ? `<div class="detail-category"><i class="fas fa-tag"></i> ${escapeHtml(catName)}</div>` : ''}
                    <div class="detail-price">${formatPrice(product.price)} so'm</div>
                    ${licenseBadge}
                    ${descHtml}
                    ${instrHtml}
                    <div class="modal-purchase-bar">
                        <div class="modal-qty-wrap">
                            <button class="modal-qty-btn" onclick="changeQty(this,-1)">−</button>
                            <input type="number" class="modal-qty-input" value="1" min="1" max="999" readonly>
                            <button class="modal-qty-btn" onclick="changeQty(this,1)">+</button>
                        </div>
                        <button class="btn-modal-cart" onclick="addToCart(${product.id}, this)">
                            <i class="fas fa-cart-plus"></i> Savatga qo'shish
                        </button>
                    </div>
                </div>
            `;
        }
        
        const catId = product.category?.id ?? (typeof product.category === 'number' ? product.category : null);
        fetchSimilarProducts(catId, product.id);
        
        showDetailView();

    } catch (err) {
        console.error('Product detail error:', err);
    }
};

async function fetchSimilarProducts(categoryId, currentId) {
    if (!similarProductsGrid) return;
    if (!categoryId) {
        similarProductsGrid.innerHTML = '<p style="color:#888;">Topilmadi.</p>';
        return;
    }
    try {
        const res = await fetch(`/api/v1/pharmacy/products/?category=${categoryId}`);
        const data = await res.json();
        const similar = (data.results || data).filter(p => p.id !== currentId).slice(0, 4);
        if (similar.length > 0) {
            renderProducts(similar, similarProductsGrid);
        } else {
            similarProductsGrid.innerHTML = '<p style="color:#888;">Topilmadi.</p>';
        }
    } catch (err) {
        console.error('Similar products error:', err);
    }
}

// ===================== EVENT LISTENERS =====================
function setupEventListeners() {
    if (applyFilterBtn) applyFilterBtn.addEventListener('click', () => loadProducts());
    if (sortSelect) sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        loadProducts();
    });
}

// ===================== TOAST & UTILS =====================
function showToast(html, isError = false) {
    document.querySelectorAll('.cart-toast').forEach(t => t.remove());
    const toast = document.createElement('div');
    toast.className = 'cart-toast' + (isError ? ' error' : '');
    toast.innerHTML = html;
    document.body.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 2900);
}

function formatPrice(price) {
    if (!price) return '0';
    return Number(price).toLocaleString('uz-UZ');
}

function escapeHtml(str) {
    if (typeof str !== 'string') return String(str ?? '');
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}