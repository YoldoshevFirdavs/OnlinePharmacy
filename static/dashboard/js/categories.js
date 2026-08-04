/**
 * OnlinePharmacy Dashboard — Categories page module
 * Fetches categories via API and renders into list.html table template.
 */
(function () {
    'use strict';

    function getApi() {
        return window.Dashboard || {};
    }

    function getTargetContainer() {
        return document.getElementById('categoriesList') ||
            document.querySelector('#dataTable tbody');
    }

    function renderEmptyRow(colspan) {
        return '<tr class="data-table__empty">' +
            '<td colspan="' + colspan + '">' +
            '<i class="fa-solid fa-inbox"></i>' +
            '<span>Kategoriyalar topilmadi</span>' +
            '</td></tr>';
    }

    function renderCategoryRow(cat, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var imageHtml;

        if (cat.image || cat.image_url) {
            var src = cat.image_url || cat.image;
            imageHtml = '<div class="table-image"><img src="' + escapeHtml(src) + '" alt="' + escapeHtml(cat.name) + '" loading="lazy"></div>';
        } else {
            imageHtml = '<div class="table-image"><div class="table-image__placeholder"><i class="fa-solid fa-image"></i></div></div>';
        }

        var editUrl = cat.edit_url || ('/dashboard/categories/' + cat.id + '/edit/');
        var deleteUrl = cat.delete_url || ('/dashboard/categories/' + cat.id + '/delete/');
        var csrf = (api.getCSRFToken && api.getCSRFToken()) || '';

        return '<tr data-category-id="' + escapeHtml(String(cat.id)) + '">' +
            '<td>' + escapeHtml(String(cat.id)) + '</td>' +
            '<td>' + imageHtml + '</td>' +
            '<td><strong>' + escapeHtml(cat.name) + '</strong></td>' +
            '<td>' + escapeHtml(String(cat.product_count || cat.medicines_count || cat.count || 0)) + '</td>' +
            '<td><div class="table-actions">' +
            '<a href="' + escapeHtml(editUrl) + '" class="btn btn--sm btn--ghost" title="Tahrirlash">' +
            '<i class="fa-solid fa-pen"></i></a>' +
            '<form method="post" action="' + escapeHtml(deleteUrl) + '" class="inline-form category-delete-form">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + escapeHtml(csrf) + '">' +
            '<button type="submit" class="btn btn--sm btn--ghost btn--danger" title="O\'chirish">' +
            '<i class="fa-solid fa-trash"></i></button></form></div></td></tr>';
    }

    function bindDeleteConfirm() {
        document.querySelectorAll('.category-delete-form').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                event.preventDefault();
                var submitForm = function () {
                    form.submit();
                };

                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'O\'chirishni tasdiqlang',
                        text: 'Ushbu kategoriyani o\'chirmoqchimisiz?',
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonText: '<i class="fa-solid fa-trash"></i> Ha, o\'chirish',
                        cancelButtonText: 'Bekor qilish'
                    }).then(function (result) {
                        if (result.isConfirmed) {
                            submitForm();
                        }
                    });
                } else if (window.confirm('Ushbu kategoriyani o\'chirmoqchimisiz?')) {
                    submitForm();
                }
            });
        });
    }

    function updateTableCount(count) {
        var countEl = document.getElementById('tableCount');
        if (countEl) {
            countEl.textContent = count + ' ta kategoriya';
        }
    }

    function loadCategories() {
        var container = getTargetContainer();
        if (!container) {
            return;
        }

        var api = getApi();
        var fetchFn = api.fetchCategories || api.apiFetch && function () {
            return api.apiFetch('categories/').then(api.extractList);
        };

        if (!fetchFn) {
            return;
        }

        fetchFn()
            .then(function (categories) {
                if (!categories.length) {
                    container.innerHTML = renderEmptyRow(5);
                    updateTableCount(0);
                    return;
                }

                container.innerHTML = categories.map(function (cat) {
                    return renderCategoryRow(cat, api);
                }).join('');

                updateTableCount(categories.length);
                bindDeleteConfirm();

                if (typeof lightbox !== 'undefined') {
                    container.querySelectorAll('.table-image img').forEach(function (img) {
                        img.setAttribute('data-lightbox', 'categories');
                    });
                }
            })
            .catch(function () {
                /* Keep SSR-rendered rows on API failure */
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!getTargetContainer()) {
            return;
        }
        loadCategories();
    });
})();
