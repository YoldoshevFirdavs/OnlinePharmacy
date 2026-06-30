class Shop {
    constructor() {
        this.categories = [];
        this.products = [];
        this.selectedCategory = null;
        this.init();
    }

    async init() {
        await this.loadCategories();
        await this.loadProducts();
        this.setupEventListeners();
        this.setupSearch(); // Call setupSearch here
        console.log('Shop initialized');
    }

    // ========================================
    // API CALLS
    // ========================================

    async loadCategories() {
        try {
            const categories = await callApi('/api/v1/pharmacy/categories/', 'GET');
            this.categories = Array.isArray(categories) ? categories : [];
            this.renderCategories();
        } catch (error) {
            console.error('Error loading categories:', error);
            const categoriesList = document.getElementById('categories-list');
            if (categoriesList) {
                categoriesList.innerHTML = '<p class="empty">Hozircha kategoriyalar yo\'q</p>';
            }
        }
    }

    async loadProducts(categorySlug = null) {
        try {
            const endpoint = categorySlug
                ? `/api/v1/pharmacy/products/?category=${categorySlug}`
                : '/api/v1/pharmacy/products/';

            const products = await callApi(endpoint, 'GET');
            this.products = Array.isArray(products) ? products : [];
            this.renderProducts();
        } catch (error) {
            console.error('Error loading products:', error);
            const productsGrid = document.getElementById('products-grid');
            if (productsGrid) {
                productsGrid.innerHTML = '<p class="empty">Hozircha mahsulotlar yo\'q</p>';
            }
        }
    }

    // ========================================
    // RENDER
    // ========================================

    renderCategories() {
        const container = document.getElementById('categories-list');
        if (!container) return; // Ensure container exists

        if (this.categories.length === 0) {
            container.innerHTML = '<p class="empty">Hozircha kategoriyalar yo\'q</p>';
            return;
        }

        container.innerHTML = this.categories.map(cat => `
            <div class="category-item" data-slug="${cat.slug}">
                <i class="fas fa-${this.getCategoryIcon(cat.name)}"></i>
                ${cat.name}
            </div>
        `).join('');

        container.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                container.querySelectorAll('.category-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                this.selectedCategory = item.dataset.slug;
                this.loadProducts(this.selectedCategory);
                // document.getElementById('section-title').textContent = item.textContent; // section-title not found in shop.html
            });
        });
    }

    renderProducts() {
        const container = document.getElementById('products-grid');
        if (!container) return; // Ensure container exists

        if (this.products.length === 0) {
            container.innerHTML = '<p class="empty">Hozircha mahsulotlar yo\'q</p>';
            return;
        }

        container.innerHTML = this.products.map(product => `
            <div class="product-card" data-id="${product.id}">
                <div class="product-image">${this.getProductEmoji(product.name)}</div>
                <div class="product-info">
                    <div class="product-name">${product.name}</div>
                    <div class="product-desc">${product.description || 'Sog\'likni saqlash'}</div>
                    <div class="product-meta">
                        <div class="product-price">${product.price ? product.price.toLocaleString() + ' so\'m' : 'Narxi yo\'q'}</div>
                        <div class="product-rating">
                            <i class="fas fa-star"></i> ${product.average_rating || 4.5}
                        </div>
                    </div>
                    <div class="product-stock">
                        ${product.stock > 0 ? `Qoldi: ${product.stock}` : 'Qolmadi'}
                    </div>
                    <button class="btn-add">
                        <i class="fas fa-shopping-cart"></i> Savatchaga
                    </button>
                </div>
            </div>
        `).join('');

        container.querySelectorAll('.product-card').forEach(card => {
            card.addEventListener('click', () => this.showProductDetail(card.dataset.id));
            card.querySelector('.btn-add').addEventListener('click', (e) => {
                e.stopPropagation();
                alert('Savatchaga qo\'shildi!');
            });
        });
    }

    getProductEmoji(name) {
        const emojiMap = {
            'paracetamol': '💊',
            'vitamin': '💊',
            'aspirin': '💊',
            'og\'riq': '💊',
            'isitma': '🌡️',
            'antibiotik': '💉',
            'dori': '💊',
            'terapiya': '🏥'
        };

        for (const [key, emoji] of Object.entries(emojiMap)) {
            if (name.toLowerCase().includes(key)) return emoji;
        }
        return '💊';
    }

    getCategoryIcon(name) {
        const iconMap = {
            'og\'riq': 'pills',
            'isitma': 'thermometer',
            'vitamin': 'apple',
            'antibiotik': 'syringe',
            'dermatologiya': 'spa'
        };

        for (const [key, icon] of Object.entries(iconMap)) {
            if (name.toLowerCase().includes(key)) return icon;
        }
        return 'pills';
    }

    // ========================================
    // PRODUCT DETAIL
    // ========================================

    async showProductDetail(productId) {
        const product = this.products.find(p => p.id == productId);
        if (!product) return;

        const detailName = document.getElementById('detail-name');
        const detailDesc = document.getElementById('detail-short-description'); // Corrected ID
        const detailImage = document.getElementById('detail-image');
        const detailPrice = document.getElementById('detail-price');
        // const detailRating = document.getElementById('detail-rating'); // detail-rating not found in shop.html
        const detailReviews = document.getElementById('detail-reviews');
        const productDetailModal = document.getElementById('product-detail-modal');
        const addToCartBtn = productDetailModal ? productDetailModal.querySelector('.add-to-cart-btn') : null;


        if (detailName) detailName.textContent = product.name;
        if (detailDesc) detailDesc.textContent = product.description || 'Mahsulot haqida';
        if (detailImage) detailImage.src = product.image_url || ''; // Assuming product has image_url
        if (detailPrice) detailPrice.textContent = `${product.price ? product.price.toLocaleString() + ' so\'m' : 'Narxi yo\'q'}`;
        // if (detailRating) detailRating.innerHTML = `<i class="fas fa-star"></i> ${product.average_rating || 4.5} (${product.reviews_count || 0} sharh)`;

        // Reviews
        const reviewsHtml = product.reviews && product.reviews.length > 0
            ? product.reviews.map(review => `
                <div class="review-item">
                    <div class="review-author">${review.user}</div>
                    <div class="review-rating">${'⭐'.repeat(review.rating)}</div>
                    <div class="review-text">${review.content}</div>
                </div>
            `).join('')
            : '<p>Hozircha sharhlar yo\'q</p>';

        if (detailReviews) detailReviews.innerHTML = `<h4>Sharhlar</h4>${reviewsHtml}`;

        if (addToCartBtn) {
            addToCartBtn.onclick = () => { // Use onclick for simplicity or addEventListener
                alert(`"${product.name}" savatchaga qo'shildi!`);
                this.closeProductModal();
            };
        }

        if (productDetailModal) {
            productDetailModal.classList.remove('hidden');
        }
    }

    closeProductModal() {
        const productDetailModal = document.getElementById('product-detail-modal');
        if (productDetailModal) {
            productDetailModal.classList.add('hidden');
        }
    }

    // ========================================
    // SEARCH
    // ========================================

    setupSearch() {
        const searchInput = document.getElementById('search-input');
        const suggestionsDiv = document.getElementById('search-suggestions');

        if (!searchInput || !suggestionsDiv) {
            console.warn("Search input or suggestions div not found. Search functionality disabled.");
            return;
        }

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();

            if (!query) {
                suggestionsDiv.classList.remove('show');
                return;
            }

            const filtered = this.products.filter(p =>
                p.name.toLowerCase().includes(query) ||
                (p.description && p.description.toLowerCase().includes(query))
            );

            if (filtered.length === 0) {
                suggestionsDiv.innerHTML = '<div class="suggestion-item">Natija topilmadi</div>';
            } else {
                suggestionsDiv.innerHTML = filtered.slice(0, 8).map(p => `
                    <div class="suggestion-item" data-id="${p.id}">
                        ${p.name} - ${p.price ? p.price.toLocaleString() + ' so\'m' : 'Narxi yo\'q'}
                    </div>
                `).join('');

                suggestionsDiv.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        this.showProductDetail(item.dataset.id);
                        searchInput.value = '';
                        suggestionsDiv.classList.remove('show');
                    });
                });
            }

            suggestionsDiv.classList.add('show');
        });

        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
                suggestionsDiv.classList.remove('show');
            }
        });
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    setupEventListeners() {
        // Close product detail modal
        const closeProductDetailBtn = document.getElementById('close-product-detail');
        if (closeProductDetailBtn) {
            closeProductDetailBtn.addEventListener('click', () => this.closeProductModal());
        }

        // Close discount popup
        const closePopupBtn = document.getElementById('close-popup');
        const discountPopup = document.getElementById('discount-popup');
        if (closePopupBtn && discountPopup) {
            closePopupBtn.addEventListener('click', () => discountPopup.classList.add('hidden'));
        }

        // Close full guide modal
        const closeFullGuideBtn = document.getElementById('close-full-guide');
        const fullGuideModal = document.getElementById('full-guide-modal');
        if (closeFullGuideBtn && fullGuideModal) {
            closeFullGuideBtn.addEventListener('click', () => fullGuideModal.classList.add('hidden'));
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.shop = new Shop();
});