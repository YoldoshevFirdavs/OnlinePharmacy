// Shop.js - Search-first UX with infinite scroll and filters

// ===================== CONSTANTS =====================
const DEFAULT_IMG = '/static/images/default_avatar.png';
const DEBOUNCE_DELAY = 300;
const PAGE_SIZE = 24;
const API_BASE = '/api/v1/pharmacy/products/';

// ===================== GLOBAL STATE =====================
let shopState = {
    query: '',
    categoryId: null,
    minPrice: null,
    maxPrice: null,
    ordering: '-reviews_count',
    currentPage: 1,
    totalCount: 0,
    results: [],
    loading: false,
    hasMore: true,
    cache: new Map(), // sessionStorage simulation
};

let debounceTimer = null;

// ===================== DOM REFS =====================
const elements = {
    loader: () => document.getElementById('loader'),
    shopMain: () => document.getElementById('shop-main-view'),
    detailView: () => document.getElementById('product-detail-view'),
    searchInput: () => document.getElementById('search-input'),
    filterPanel: () => document.getElementById('filter-panel'),
    resultsGrid: () => document.getElementById('products-grid'),
    filterBtn: () => document.getElementById('toggle-filters'),
    categorySelect: () => document.getElementById('category-filter'),
    minPriceInput: () => document.getElementById('min-price'),
    maxPriceInput: () => document.getElementById('max-price'),
    orderingSelect: () => document.getElementById('ordering'),
    loadMoreBtn: () => document.getElementById('load-more-btn'),
    resultCount: () => document.getElementById('result-count'),
    emptyState: () => document.getElementById('empty-state'),
};

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    initShop();
});

async function initShop() {
    setupEventListeners();
    restoreFilterState();
    
    // Search input focus = show filter panel
    elements.searchInput()?.addEventListener('focus', () => {
        elements.filterPanel()?.classList.add('show');
    });
}

// ===================== EVENT LISTENERS =====================
function setupEventListeners() {
    // Search input with debounce
    elements.searchInput()?.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            shopState.query = e.target.value.trim();
            shopState.currentPage = 1;
            shopState.results = [];
            saveFilterState();
            loadProducts();
        }, DEBOUNCE_DELAY);
    });

    // Search on Enter
    elements.searchInput()?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            clearTimeout(debounceTimer);
            shopState.query = e.target.value.trim();
            shopState.currentPage = 1;
            shopState.results = [];
            saveFilterState();
            loadProducts();
        }
    });

    // Filters
    elements.categorySelect()?.addEventListener('change', (e) => {
        shopState.categoryId = e.target.value || null;
        shopState.currentPage = 1;
        shopState.results = [];
        saveFilterState();
        loadProducts();
    });

    elements.minPriceInput()?.addEventListener('change', (e) => {
        shopState.minPrice = e.target.value ? parseFloat(e.target.value) : null;
        shopState.currentPage = 1;
        shopState.results = [];
        saveFilterState();
        loadProducts();
    });

    elements.maxPriceInput()?.addEventListener('change', (e) => {
        shopState.maxPrice = e.target.value ? parseFloat(e.target.value) : null;
        shopState.currentPage = 1;
        shopState.results = [];
        saveFilterState();
        loadProducts();
    });

    elements.orderingSelect()?.addEventListener('change', (e) => {
        shopState.ordering = e.target.value;
        shopState.currentPage = 1;
        shopState.results = [];
        saveFilterState();
        loadProducts();
    });

    // Load more button
    elements.loadMoreBtn()?.addEventListener('click', () => {
        shopState.currentPage += 1;
        loadProducts(true); // append mode
    });

    // Filter toggle (mobile)
    elements.filterBtn()?.addEventListener('click', () => {
        elements.filterPanel()?.classList.toggle('show');
    });

    // Infinite scroll
    setupInfiniteScroll();
}

function setupInfiniteScroll() {
    const sentinel = document.getElementById('scroll-sentinel');
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && shopState.hasMore && !shopState.loading) {
            shopState.currentPage += 1;
            loadProducts(true); // append mode
        }
    }, { rootMargin: '200px' });

    observer.observe(sentinel);
}

// ===================== API CALLS =====================
async function loadProducts(append = false) {
    shopState.loading = true;
    showLoader();

    const params = new URLSearchParams();
    if (shopState.query) params.append('q', shopState.query);
    if (shopState.categoryId) params.append('category', shopState.categoryId);
    if (shopState.minPrice !== null) params.append('min_price', shopState.minPrice);
    if (shopState.maxPrice !== null) params.append('max_price', shopState.maxPrice);
    params.append('ordering', shopState.ordering);
    params.append('page', shopState.currentPage);
    params.append('page_size', PAGE_SIZE);

    const url = `${API_BASE}?${params.toString()}`;
    const cacheKey = url;

    // Check cache
    if (shopState.cache.has(cacheKey)) {
        const cached = shopState.cache.get(cacheKey);
        processResults(cached, append);
        shopState.loading = false;
        hideLoader();
        return;
    }

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('API error');
        
        const data = await response.json();
        shopState.cache.set(cacheKey, data); // Cache results
        processResults(data, append);
    } catch (error) {
        console.error('Load products error:', error);
        showToast('Mahsulotlarni yuklashda xato', true);
    } finally {
        shopState.loading = false;
        hideLoader();
    }
}

function processResults(data, append = false) {
    if (!append) {
        shopState.results = data.results || [];
    } else {
        shopState.results.push(...(data.results || []));
    }

    shopState.totalCount = data.count || 0;
    shopState.hasMore = !!data.next;

    renderResults();
    updateResultCount();
    
    // Show/hide filters when results load
    if (shopState.results.length > 0) {
        elements.filterPanel()?.classList.add('show');
    }
}

// ===================== RENDERING =====================
function renderResults() {
    const grid = elements.resultsGrid();
    if (!grid) return;

    if (shopState.results.length === 0) {
        grid.innerHTML = '<div id="empty-state" style="grid-column:1/-1;padding:40px;text-align:center;color:#999;">Hech qanday mahsulot topilmadi</div>';
        elements.loadMoreBtn()?.style.display = 'none';
        return;
    }

    const html = shopState.results.map(product => `
        <div class="product-card" tabindex="0" role="button" aria-label="Product: ${escapeHtml(product.name)}" onclick="openProductDetail(${product.id})">
            <div class="product-image-wrap">
                <img 
                    src="${product.image || DEFAULT_IMG}" 
                    class="product-image" 
                    loading="lazy"
                    onerror="this.src='${DEFAULT_IMG}'"
                    alt="${escapeHtml(product.name)}"
                >
            </div>
            <div class="product-info">
                <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
                <div class="product-rating">
                    ${product.average_rating ? `<span class="stars">${'⭐'.repeat(Math.round(product.average_rating))}</span>` : ''}
                    <span class="reviews-count">${product.reviews_count || 0} fikr</span>
                </div>
                <div class="product-price"><strong>${formatPrice(product.price)}</strong> so'm</div>
            </div>
        </div>
    `).join('');

    grid.innerHTML = html;
    elements.loadMoreBtn()?.style.display = shopState.hasMore ? 'block' : 'none';
}

function updateResultCount() {
    const el = elements.resultCount();
    if (el) {
        el.textContent = `${shopState.totalCount} natija topildi`;
    }
}

// ===================== FILTER STATE =====================
function saveFilterState() {
    const state = {
        query: shopState.query,
        categoryId: shopState.categoryId,
        minPrice: shopState.minPrice,
        maxPrice: shopState.maxPrice,
        ordering: shopState.ordering,
    };
    sessionStorage.setItem('shopFilterState', JSON.stringify(state));
    updateURLParams();
}

function restoreFilterState() {
    const saved = sessionStorage.getItem('shopFilterState');
    if (saved) {
        const state = JSON.parse(saved);
        shopState.query = state.query || '';
        shopState.categoryId = state.categoryId || null;
        shopState.minPrice = state.minPrice || null;
        shopState.maxPrice = state.maxPrice || null;
        shopState.ordering = state.ordering || '-reviews_count';

        // Restore UI
        if (elements.searchInput()) elements.searchInput().value = shopState.query;
        if (elements.categorySelect()) elements.categorySelect().value = shopState.categoryId || '';
        if (elements.minPriceInput()) elements.minPriceInput().value = shopState.minPrice || '';
        if (elements.maxPriceInput()) elements.maxPriceInput().value = shopState.maxPrice || '';
        if (elements.orderingSelect()) elements.orderingSelect().value = shopState.ordering;
    }
}

function updateURLParams() {
    const params = new URLSearchParams();
    if (shopState.query) params.append('q', shopState.query);
    if (shopState.categoryId) params.append('category', shopState.categoryId);
    if (shopState.minPrice !== null) params.append('min_price', shopState.minPrice);
    if (shopState.maxPrice !== null) params.append('max_price', shopState.maxPrice);
    params.append('ordering', shopState.ordering);

    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newUrl);
}

// ===================== UTILITIES =====================
function showLoader() {
    elements.loader()?.classList.add('show');
}

function hideLoader() {
    elements.loader()?.classList.remove('show');
}

function showToast(message, isError = false) {
    // Simple toast notification
    const div = document.createElement('div');
    div.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${isError ? '#ff5252' : '#4caf50'};
        color: white;
        padding: 16px;
        border-radius: 4px;
        z-index: 9999;
    `;
    div.textContent = message;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(price || 0);
}

function escapeHtml(str) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return str.replace(/[&<>"']/g, (char) => map[char]);
}

// ===================== PRODUCT DETAIL =====================
async function openProductDetail(productId) {
    // Placeholder - implement similar to existing detail view
    console.log('Open product:', productId);
}
