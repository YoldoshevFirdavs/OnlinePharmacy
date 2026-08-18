// Shop.js - Search-first UX with instant suggestions, infinite scroll and filters

// ===================== CONSTANTS =====================
const DEFAULT_IMG = '/static/images/default_avatar.png';
const DEBOUNCE_DELAY = 300;
const PAGE_SIZE = 24;
const API_BASE = '/api/v1/products/';
const SUGGESTIONS_API = '/api/v1/products/suggest/';

// ===================== GLOBAL STATE =====================
let shopState = {
    query: '',
    categoryId: null,
    minPrice: null,
    maxPrice: null,
    orderingParam: '-reviews_count',
    currentPage: 1,
    totalCount: 0,
    results: [],
    loading: false,
    hasMore: true,
    cache: new Map(),
    suggestions: [],
};

let debounceTimer = null;
let suggestionsDebounceTimer = null;

// ===================== DOM REFS =====================
const elements = {
    loader: () => document.getElementById('loader'),
    shopMain: () => document.getElementById('shop-main-view'),
    searchInput: () => document.getElementById('search-input'),
    suggestionsDropdown: () => document.getElementById('suggestions-dropdown'),
    filterPanel: () => document.getElementById('filter-panel'),
    resultsGrid: () => document.getElementById('products-grid'),
    filterBtn: () => document.getElementById('toggle-filters'),
    categorySelect: () => document.getElementById('category-filter'),
    minPriceInput: () => document.getElementById('min-price'),
    maxPriceInput: () => document.getElementById('max-price'),
    orderingSelect: () => document.getElementById('ordering'),
    loadMoreBtn: () => document.getElementById('load-more-btn'),
    resultCount: () => document.getElementById('result-count'),
};

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    initShop();
});

async function initShop() {
    createSuggestionsDropdown();
    setupEventListeners();
    restoreFilterState();
    
    // Load recommended products on page init
    await loadProducts();
    
    // Search input focus = show suggestions
    elements.searchInput()?.addEventListener('focus', () => {
        if (elements.suggestionsDropdown()) {
            elements.suggestionsDropdown().style.display = 'block';
        }
    });
};

// ===================== SUGGESTIONS DROPDOWN =====================
function createSuggestionsDropdown() {
    const searchBox = document.querySelector('.search-box');
    if (!searchBox) return;

    const dropdown = document.createElement('div');
    dropdown.id = 'suggestions-dropdown';
    dropdown.style.cssText = `
        position: absolute;
        top: 50px;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 4px 4px;
        max-height: 300px;
        overflow-y: auto;
        display: none;
        z-index: 1000;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    `;
    dropdown.setAttribute('role', 'listbox');
    searchBox.parentElement.insertBefore(dropdown, searchBox.nextSibling);
}

async function loadSuggestions(query) {
    if (!query || query.length < 1) {
        elements.suggestionsDropdown().style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`${SUGGESTIONS_API}?q=${encodeURIComponent(query)}&limit=10`);
        const data = await response.json();
        shopState.suggestions = data.suggestions || [];
        renderSuggestions();
    } catch (error) {
        console.error('Suggestions error:', error);
    }
}

function renderSuggestions() {
    const dropdown = elements.suggestionsDropdown();
    if (!dropdown) return;

    if (shopState.suggestions.length === 0) {
        dropdown.style.display = 'none';
        return;
    }

    const html = shopState.suggestions.map((s, i) => `
        <div 
            class="suggestion-item" 
            role="option"
            tabindex="0"
            onclick="selectSuggestion('${escapeHtml(s.name)}')"
            onkeypress="event.key === 'Enter' && selectSuggestion('${escapeHtml(s.name)}')"
            style="padding:12px;border-bottom:1px solid #f0f0f0;cursor:pointer;transition:background 0.2s;"
            onmouseover="this.style.background='#f9f9f9'"
            onmouseout="this.style.background='white'"
        >
            <div style="font-size:14px;font-weight:500;">${escapeHtml(s.name)}</div>
            <div style="font-size:12px;color:#999;">
                ${s.average_rating ? `<span>⭐ ${s.average_rating}</span>` : ''} 
                <span>${formatPrice(s.price)} so'm</span>
            </div>
        </div>
    `).join('');

    dropdown.innerHTML = html;
    dropdown.style.display = 'block';
}

function selectSuggestion(suggestion) {
    elements.searchInput().value = suggestion;
    shopState.query = suggestion;
    elements.suggestionsDropdown().style.display = 'none';
    shopState.currentPage = 1;
    shopState.results = [];
    saveFilterState();
    loadProducts();
}

// ===================== EVENT LISTENERS =====================
function setupEventListeners() {
    // Search input with debounce for suggestions
    elements.searchInput()?.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        // Clear previous debounce
        clearTimeout(suggestionsDebounceTimer);
        
        // Load suggestions with debounce
        suggestionsDebounceTimer = setTimeout(() => {
            if (query.length >= 1) {
                loadSuggestions(query);
            } else {
                elements.suggestionsDropdown().style.display = 'none';
            }
        }, 150); // Faster debounce for suggestions
        
        // Reset search on input change
        shopState.query = query;
    });

    // Search on Enter or search button click
    elements.searchInput()?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            shopState.query = e.target.value.trim();
            elements.suggestionsDropdown().style.display = 'none';
            shopState.currentPage = 1;
            shopState.results = [];
            saveFilterState();
            loadProducts();
        }
    });

    // Close suggestions on blur
    elements.searchInput()?.addEventListener('blur', () => {
        setTimeout(() => {
            elements.suggestionsDropdown().style.display = 'none';
        }, 150);
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
        shopState.orderingParam = e.target.value;
        shopState.currentPage = 1;
        shopState.results = [];
        saveFilterState();
        loadProducts();
    });

    // Load more button
    elements.loadMoreBtn()?.addEventListener('click', () => {
        shopState.currentPage += 1;
        loadProducts(true);
    });

    // Filter toggle
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
            loadProducts(true);
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
    params.append('ordering', shopState.orderingParam);
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
        shopState.cache.set(cacheKey, data);
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
    
    // Show filter panel if results loaded
    if (shopState.results.length > 0) {
        elements.filterPanel()?.classList.add('show');
    }
}

// ===================== RENDERING =====================
function renderResults() {
    const grid = elements.resultsGrid();
    if (!grid) return;

    if (shopState.results.length === 0) {
        grid.innerHTML = '<div style="grid-column:1/-1;padding:40px;text-align:center;color:#999;">Hech qanday mahsulot topilmadi</div>';
        elements.loadMoreBtn()?.style.display = 'none';
        return;
    }

    const html = shopState.results.map(product => {
        const sellerName = product.seller_info?.shop_name || 'Noma\'lum sotuvchi';
        return `
            <div 
                class="product-card" 
                tabindex="0" 
                role="button" 
                aria-label="Mahsulot: ${escapeHtml(product.name)}, ${formatPrice(product.price)} so'm"
                onclick="window.location.href='/products/${product.id}/'"
                onkeypress="event.key === 'Enter' && (window.location.href='/products/${product.id}/')"
            >
                <div class="product-image-wrap">
                    <img 
                        src="${product.main_image || DEFAULT_IMG}" 
                        class="product-image" 
                        loading="lazy"
                        onerror="this.src='${DEFAULT_IMG}'"
                        alt="${escapeHtml(product.name)}"
                    >
                </div>
                <div class="product-info">
                    <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
                    <div class="product-rating">
                        ${product.average_rating ? `<span class="stars">⭐ ${product.average_rating}</span>` : ''}
                        <span class="reviews-count">${product.reviews_count || 0}</span>
                    </div>
                    <div style="font-size:12px;color:#666;margin-bottom:8px;">${escapeHtml(sellerName)}</div>
                    <div class="product-price"><strong>${formatPrice(product.price)}</strong> so'm</div>
                </div>
            </div>
        `;
    }).join('');

    grid.innerHTML = html;
    elements.loadMoreBtn()?.style.display = shopState.hasMore ? 'block' : 'none';
}

function updateResultCount() {
    const el = elements.resultCount();
    if (el) {
        el.textContent = `Natija: ${shopState.totalCount}`;
    }
}

// ===================== FILTER STATE =====================
function saveFilterState() {
    const state = {
        query: shopState.query,
        categoryId: shopState.categoryId,
        minPrice: shopState.minPrice,
        maxPrice: shopState.maxPrice,
        orderingParam: shopState.orderingParam,
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
        shopState.orderingParam = state.orderingParam || '-reviews_count';

        // Restore UI
        if (elements.searchInput()) elements.searchInput().value = shopState.query;
        if (elements.categorySelect()) elements.categorySelect().value = shopState.categoryId || '';
        if (elements.minPriceInput()) elements.minPriceInput().value = shopState.minPrice || '';
        if (elements.maxPriceInput()) elements.maxPriceInput().value = shopState.maxPrice || '';
        if (elements.orderingSelect()) elements.orderingSelect().value = shopState.orderingParam;
    }
}

function updateURLParams() {
    const params = new URLSearchParams();
    if (shopState.query) params.append('q', shopState.query);
    if (shopState.categoryId) params.append('category', shopState.categoryId);
    if (shopState.minPrice !== null) params.append('min_price', shopState.minPrice);
    if (shopState.maxPrice !== null) params.append('max_price', shopState.maxPrice);
    params.append('ordering', shopState.orderingParam);

    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newUrl);
}

// ===================== UTILITIES =====================
function showLoader() {
    const el = elements.loader();
    if (el) el.classList.add('show');
}

function hideLoader() {
    const el = elements.loader();
    if (el) el.classList.remove('show');
}

function showToast(message, isError = false) {
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
        font-size: 14px;
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
    if (!str) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return String(str).replace(/[&<>"']/g, (char) => map[char]);
}
