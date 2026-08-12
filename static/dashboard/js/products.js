/**
 * OnlinePharmacy Dashboard — Products page module
 * Fetches products and renders image, name, price, quantity columns.
 */
(function () {
    'use strict';

    function getApi() {
        return window.Dashboard || {};
    }

    function getTargetContainer() {
        var productsContainer = document.getElementById('productsContainer');
        if (productsContainer) {
            return productsContainer;
        }
        return document.querySelector('#dataTable tbody');
    }

    function renderEmptyRow(colspan) {
        return '<tr class="data-table__empty">' +
            '<td colspan="' + colspan + '">' +
            '<i class="fa-solid fa-inbox"></i>' +
            '<span>Mahsulotlar topilmadi</span>' +
            '</td></tr>';
    }

    function stockStatus(quantity) {
        var qty = Number(quantity) || 0;
        if (qty > 0) {
            return '<span class="tag tag--success"><i class="fa-solid fa-circle-check"></i> Mavjud</span>';
        }
        return '<span class="tag tag--error"><i class="fa-solid fa-circle-xmark"></i> Tugagan</span>';
    }

    function renderProductRow(product, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var imageHtml;

        if (product.image || product.image_url) {
            var src = product.image_url || product.image;
            imageHtml = '<div class="table-image"><img src="' + escapeHtml(src) + '" alt="' + escapeHtml(product.name) + '" loading="lazy" data-lightbox="products"></div>';
        } else {
            imageHtml = '<div class="table-image"><div class="table-image__placeholder"><i class="fa-solid fa-image"></i></div></div>';
        }

        var categoryName = product.category_name || (product.category && product.category.name) || '—';
        var editUrl = product.edit_url || ('/dashboard/medicines/' + product.id + '/edit/');
        var deleteUrl = product.delete_url || ('/dashboard/medicines/' + product.id + '/delete/');
        var csrf = (api.getCSRFToken && api.getCSRFToken()) || '';

        return '<tr data-product-id="' + escapeHtml(String(product.id)) + '">' +
            '<td>' + escapeHtml(String(product.id)) + '</td>' +
            '<td>' + imageHtml + '</td>' +
            '<td><strong>' + escapeHtml(product.name) + '</strong></td>' +
            '<td>' + escapeHtml(categoryName) + '</td>' +
            '<td>' + escapeHtml(String(product.price || 0)) + ' so\'m</td>' +
            '<td>' + escapeHtml(String(product.quantity || 0)) + '</td>' +
            '<td>' + stockStatus(product.quantity) + '</td>' +
            '<td><div class="table-actions">' +
            '<a href="' + escapeHtml(editUrl) + '" class="btn btn--sm btn--ghost" title="Tahrirlash">' +
            '<i class="fa-solid fa-pen"></i></a>' +
            '<form method="post" action="' + escapeHtml(deleteUrl) + '" class="inline-form product-delete-form">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + escapeHtml(csrf) + '">' +
            '<button type="submit" class="btn btn--sm btn--ghost btn--danger" title="O\'chirish">' +
            '<i class="fa-solid fa-trash"></i></button></form></div></td></tr>';
    }

    function renderProductsGrid(products, api, container) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };

        container.innerHTML = products.map(function (product) {
            var src = product.image_url || product.image || '';
            var imgBlock = src
                ? '<img src="' + escapeHtml(src) + '" alt="' + escapeHtml(product.name) + '" loading="lazy">'
                : '<div class="table-image__placeholder"><i class="fa-solid fa-image"></i></div>';

            return '<div class="product-card" data-product-id="' + escapeHtml(String(product.id)) + '">' +
                '<div class="product-card__image">' + imgBlock + '</div>' +
                '<div class="product-card__body">' +
                '<h3 class="product-card__title"><i class="fa-solid fa-pills"></i> ' + escapeHtml(product.name) + '</h3>' +
                '<p class="product-card__price"><i class="fa-solid fa-tag"></i> ' + escapeHtml(String(product.price || 0)) + ' so\'m</p>' +
                '<p class="product-card__qty"><i class="fa-solid fa-boxes-stacked"></i> Miqdor: ' + escapeHtml(String(product.quantity || 0)) + '</p>' +
                '</div></div>';
        }).join('');
    }

    function bindDeleteConfirm() {
        document.querySelectorAll('.product-delete-form').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                event.preventDefault();
                var submitForm = function () { form.submit(); };

                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'O\'chirishni tasdiqlang',
                        text: 'Ushbu mahsulotni o\'chirmoqchimisiz?',
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonText: '<i class="fa-solid fa-trash"></i> Ha, o\'chirish',
                        cancelButtonText: 'Bekor qilish'
                    }).then(function (result) {
                        if (result.isConfirmed) {
                            submitForm();
                        }
                    });
                } else if (window.confirm('Ushbu mahsulotni o\'chirmoqchimisiz?')) {
                    submitForm();
                }
            });
        });
    }

    function updateTableCount(count) {
        var countEl = document.getElementById('tableCount');
        if (countEl) {
            countEl.textContent = count + ' ta mahsulot';
        }
    }

    function loadProducts() {
        var container = getTargetContainer();
        if (!container) {
            return;
        }

        var api = getApi();
        var fetchFn = api.fetchProducts || (api.apiFetch && function () {
            return api.apiFetch('products/').then(api.extractList);
        });

        if (!fetchFn) {
            return;
        }

        var isGrid = container.id === 'productsContainer';

        fetchFn()
            .then(function (products) {
                if (!products.length) {
                    if (isGrid) {
                        container.innerHTML = '<p class="widget-placeholder"><i class="fa-solid fa-inbox"></i> Mahsulotlar topilmadi</p>';
                    } else {
                        container.innerHTML = renderEmptyRow(8);
                    }
                    updateTableCount(0);
                    return;
                }

                if (isGrid) {
                    renderProductsGrid(products, api, container);
                } else {
                    container.innerHTML = products.map(function (p) {
                        return renderProductRow(p, api);
                    }).join('');
                    bindDeleteConfirm();
                }

                updateTableCount(products.length);

                if (typeof lightbox !== 'undefined') {
                    lightbox.option({ resizeDuration: 200, wrapAround: true });
                }
            })
            .catch(function () {
                /* Keep SSR-rendered content on API failure */
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!getTargetContainer()) {
            return;
        }
        loadProducts();
    });
})();
