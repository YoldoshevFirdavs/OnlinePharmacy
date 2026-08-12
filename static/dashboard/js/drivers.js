/**
 * OnlinePharmacy Dashboard — Drivers page module
 * Row hover, delete confirmation modal, edit navigation.
 */
(function () {
    'use strict';

    var API_BASE = '/api/v1/dashboard/drivers/';

    function getCSRFToken() {
        if (window.Dashboard && window.Dashboard.getCSRFToken) {
            return window.Dashboard.getCSRFToken();
        }
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function getHoverColor() {
        return getComputedStyle(document.documentElement)
            .getPropertyValue('--table-row-hover-bg-color')
            .trim();
    }

    function initRowHover() {
        var hoverColor = getHoverColor();
        document.querySelectorAll('.drivers-table tbody tr:not(.data-table__empty)').forEach(function (row) {
            row.addEventListener('mouseenter', function () {
                row.classList.add('drivers-table__row--hover');
                if (hoverColor) {
                    row.style.backgroundColor = hoverColor;
                }
            });
            row.addEventListener('mouseleave', function () {
                row.classList.remove('drivers-table__row--hover');
                row.style.backgroundColor = '';
            });
        });
    }

    function confirmDelete(onConfirm) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'O\'chirishni tasdiqlang',
                text: 'Haqiqatan ham bu haydovchini o\'chirmoqchimisiz?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: '<i class="fa-solid fa-trash"></i> Ha, o\'chirish',
                cancelButtonText: 'Bekor qilish',
            }).then(function (result) {
                if (result.isConfirmed) {
                    onConfirm();
                }
            });
            return;
        }
        if (window.confirm('Haqiqatan ham bu haydovchini o\'chirmoqchimisiz?')) {
            onConfirm();
        }
    }

    function deleteDriver(driverId, row) {
        fetch(API_BASE + driverId + '/', {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken(),
            },
            credentials: 'same-origin',
        })
            .then(function (response) {
                if (response.ok || response.status === 204) {
                    row.remove();
                    updateTableCount();
                    showEmptyStateIfNeeded();
                    return;
                }
                window.alert('Haydovchini o\'chirishda xatolik yuz berdi.');
            })
            .catch(function () {
                window.alert('Haydovchini o\'chirishda xatolik yuz berdi.');
            });
    }

    function showEmptyStateIfNeeded() {
        var tbody = document.querySelector('.drivers-table tbody');
        if (!tbody) {
            return;
        }
        var rows = tbody.querySelectorAll('tr:not(.data-table__empty)');
        if (rows.length) {
            return;
        }
        tbody.innerHTML =
            '<tr class="data-table__empty">' +
            '<td colspan="5">' +
            '<i class="fa-solid fa-inbox"></i>' +
            '<span>Haydovchilar topilmadi</span>' +
            '</td></tr>';
    }

    function bindDeleteButtons() {
        document.querySelectorAll('.driver-delete-btn').forEach(function (button) {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                var driverId = button.dataset.driverId;
                var row = button.closest('tr');
                if (!driverId || !row) {
                    return;
                }
                confirmDelete(function () {
                    deleteDriver(driverId, row);
                });
            });
        });
    }

    function updateTableCount() {
        var countEl = document.getElementById('tableCount');
        if (!countEl) {
            return;
        }
        var rows = document.querySelectorAll('.drivers-table tbody tr:not(.data-table__empty)');
        countEl.textContent = rows.length + ' ta haydovchi';
    }

    document.addEventListener('DOMContentLoaded', function () {
        var table = document.getElementById('dataTable');
        if (!table) {
            return;
        }
        table.classList.add('drivers-table');
        initRowHover();
        bindDeleteButtons();
        updateTableCount();
    });
})();
