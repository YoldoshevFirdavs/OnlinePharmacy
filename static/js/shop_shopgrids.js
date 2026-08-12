document.addEventListener('DOMContentLoaded', () => {
    const productListContainer = document.getElementById('product-list');
    const prevPageButton = document.getElementById('prev-page');
    const nextPageButton = document.getElementById('next-page');
    const currentPageSpan = document.getElementById('current-page');

    let currentPage = 1;
    const productsPerPage = 6; // Assuming a fixed number of products per page for this example

    async function loadProducts(params = {}) {
        try {
            // Ensure window.api is available
            if (!window.api || typeof window.api.getProducts !== 'function') {
                console.error("window.api.getProducts is not defined. Make sure api.js is loaded correctly.");
                // Fallback or show an error message to the user
                productListContainer.innerHTML = '<p>Error loading products. Please try again later.</p>';
                return;
            }

            const data = await window.api.getProducts({ page: currentPage, page_size: productsPerPage, ...params });
            renderProducts(data.results || []);
            updatePagination(data.count);
        } catch (error) {
            console.error('Error loading products:', error);
            productListContainer.innerHTML = '<p>Failed to load products. Please check your internet connection or try again later.</p>';
        }
    }

    function renderProducts(products) {
        productListContainer.innerHTML = ''; // Clear existing products
        if (products.length === 0) {
            productListContainer.innerHTML = '<p>No products found.</p>';
            return;
        }

        products.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            productCard.dataset.productId = product.id;
            productCard.innerHTML = `
                <img src="${product.image || 'https://via.placeholder.com/150'}" alt="${product.name}">
                <h3>${product.name}</h3>
                <p class="price">$${product.price ? product.price.toFixed(2) : '0.00'}</p>
                <button onclick="addToCart(${product.id})">Add to Cart</button>
            `;
            productListContainer.appendChild(productCard);
        });
    }

    function updatePagination(totalProducts) {
        const totalPages = Math.ceil(totalProducts / productsPerPage);
        currentPageSpan.textContent = currentPage;

        prevPageButton.disabled = currentPage === 1;
        nextPageButton.disabled = currentPage === totalPages || totalPages === 0;
    }

    prevPageButton.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadProducts();
        }
    });

    nextPageButton.addEventListener('click', () => {
        currentPage++;
        loadProducts();
    });

    // Global function for Add to Cart
    window.addToCart = function(productId) {
        console.log(`Product ${productId} added to cart! (Functionality to be implemented)`);
        // Here you would typically call a cart API or add to localStorage
        // Example: window.api.addToCart({ product_id: productId, quantity: 1 });
        alert(`Product ${productId} added to cart!`);
    };

    // Initial load of products
    loadProducts();
});