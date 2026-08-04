/**
 * OnlinePharmacy Dashboard — Orders page module
 * Fetches orders, renders table, status update with SweetAlert confirm.
 */
(function () {
    'use strict';

    var STATUS_OPTIONS = ['Pending', 'Processing', 'Delivered', 'Cancelled'];

    function getApi() {
        return window.Dashboard || {};
    }

    function getOrdersTable() {
        var table = document.getElementById('ordersTable');
        if (table) {
            return table.tagName === 'TABLE' ? table : table.querySelector('table');
        }
        return document.getElementById('dataTable');
    }

    function getTableBody() {
        var table = getOrdersTable();
        return table ? table.querySelector('tbody') : null;
    }

    function statusTag(status, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var cls = 'info';
        var icon = 'fa-circle-info';

        if (status === 'Delivered') {
            cls = 'success';
            icon = 'fa-circle-check';
        } else if (status === 'Pending') {
            cls = 'warning';
            icon = 'fa-hourglass-half';
        } else if (status === 'Cancelled') {
            cls = 'error';
            icon = 'fa-circle-xmark';
        } else if (status === 'Processing') {
            cls = 'primary';
            icon = 'fa-spinner';
        }

        return '<span class="tag tag--' + cls + '"><i class="fa-solid ' + icon + '"></i> ' + escapeHtml(status || '—') + '</span>';
    }

    function renderEmptyRow(colspan) {
        return '<tr class="data-table__empty">' +
            '<td colspan="' + colspan + '">' +
            '<i class="fa-solid fa-inbox"></i>' +
            '<span>Buyurtmalar topilmadi</span>' +
            '</td></tr>';
    }

    function renderStatusButtons(orderId, currentStatus, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        return STATUS_OPTIONS.filter(function (s) {
            return s !== currentStatus;
        }).map(function (status) {
            var icon = 'fa-arrow-right';
            if (status === 'Delivered') {
                icon = 'fa-circle-check';
            } else if (status === 'Cancelled') {
                icon = 'fa-circle-xmark';
            } else if (status === 'Pending') {
                icon = 'fa-hourglass-half';
            }
            return '<button type="button" class="btn btn--sm btn--ghost order-status-btn" ' +
                'data-order-id="' + escapeHtml(String(orderId)) + '" ' +
                'data-status="' + escapeHtml(status) + '" title="' + escapeHtml(status) + '">' +
                '<i class="fa-solid ' + icon + '"></i> ' + escapeHtml(status) +
                '</button>';
        }).join('');
    }

    function renderOrderRow(order, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var formatDate = api.formatDate || function (v) { return v || '—'; };
        var customer = order.customer || order.username || (order.user && order.user.username) || '—';
        var itemCount = order.items_count || order.item_count || (order.items && order.items.length) || 0;
        var driver = order.driver || order.deliverer || 'Tayinlanmagan';

        return '<tr data-order-id="' + escapeHtml(String(order.id)) + '">' +
            '<td><strong>#' + escapeHtml(String(order.id)) + '</strong></td>' +
            '<td><div class="user-cell"><i class="fa-solid fa-circle-user"></i> ' + escapeHtml(customer) + '</div></td>' +
            '<td>' + escapeHtml(String(itemCount)) + '</td>' +
            '<td><strong>' + escapeHtml(String(order.total_price || order.total || 0)) + ' so\'m</strong></td>' +
            '<td>' + statusTag(order.status, api) + '</td>' +
            '<td>' + escapeHtml(driver) + '</td>' +
            '<td>' + escapeHtml(formatDate(order.created_at)) + '</td>' +
            '<td><div class="table-actions">' +
            '<button type="button" class="btn btn--sm btn--ghost order-view-btn" data-order-id="' + escapeHtml(String(order.id)) + '" title="Ko\'rish">' +
            '<i class="fa-solid fa-eye"></i></button>' +
            renderStatusButtons(order.id, order.status, api) +
            '</div></td></tr>';
    }

    function updateOrderStatus(orderId, newStatus, api) {
        return api.apiFetch('orders/' + orderId + '/status/', {
            method: 'PATCH',
            body: JSON.stringify({ status: newStatus })
        });
    }

    function confirmStatusChange(orderId, newStatus, api) {
        var doUpdate = function () {
            updateOrderStatus(orderId, newStatus, api)
                .then(function () {
                    loadOrders();
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'success',
                            title: 'Yangilandi',
                            text: 'Buyurtma statusi: ' + newStatus,
                            confirmButtonText: 'OK'
                        });
                    }
                })
                .catch(function (err) {
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'error',
                            title: 'Xato',
                            text: err.message || 'Status yangilanmadi',
                            confirmButtonText: 'OK'
                        });
                    }
                });
        };

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Statusni o\'zgartirish',
                text: 'Buyurtma #' + orderId + ' statusini "' + newStatus + '" ga o\'zgartirasizmi?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: '<i class="fa-solid fa-check"></i> Tasdiqlash',
                cancelButtonText: 'Bekor qilish'
            }).then(function (result) {
                if (result.isConfirmed) {
                    doUpdate();
                }
            });
        } else if (window.confirm('Statusni "' + newStatus + '" ga o\'zgartirasizmi?')) {
            doUpdate();
        }
    }

    function bindOrderActions(api) {
        document.querySelectorAll('.order-status-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var orderId = btn.getAttribute('data-order-id');
                var status = btn.getAttribute('data-status');
                confirmStatusChange(orderId, status, api);
            });
        });

        document.querySelectorAll('.order-view-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var orderId = btn.getAttribute('data-order-id');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Buyurtma #' + orderId,
                        text: 'Buyurtma tafsilotlari tez orada qo\'shiladi.',
                        icon: 'info',
                        confirmButtonText: 'OK'
                    });
                }
            });
        });
    }

    function updateTableCount(count) {
        var countEl = document.getElementById('tableCount');
        if (countEl) {
            countEl.textContent = count + ' ta buyurtma';
        }
    }

    function loadOrders() {
        var tbody = getTableBody();
        if (!tbody) {
            return;
        }

        var api = getApi();
        if (!api.apiFetch) {
            return;
        }

        api.apiFetch('orders/')
            .then(api.extractList)
            .then(function (orders) {
                if (!orders.length) {
                    tbody.innerHTML = renderEmptyRow(8);
                    updateTableCount(0);
                    return;
                }

                tbody.innerHTML = orders.map(function (order) {
                    return renderOrderRow(order, api);
                }).join('');

                updateTableCount(orders.length);
                bindOrderActions(api);
            })
            .catch(function () {
                /* Keep SSR-rendered rows on API failure */
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!getTableBody()) {
            return;
        }
        loadOrders();
    });
})();
