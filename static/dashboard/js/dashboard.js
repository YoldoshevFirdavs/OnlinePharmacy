/**
 * OnlinePharmacy Dashboard — Core module
 * Shared utilities, chart, theme, sidebar, table search, vendor init.
 */
(function () {
    'use strict';

    var API_BASE = '/api/v1/dashboard/';
    var AUTH_REDIRECT = '/auth/';
    var THEME_KEY = 'dashboard-theme';
    var ACCENT_KEY = 'dashboard-accent';

    var salesChartInstance = null;
    var resizeTimer = null;

    /* ── CSRF & API ─────────────────────────────────────────── */

    function getCSRFToken() {
        if (window.DashboardAuth && typeof window.DashboardAuth.getCSRFToken === 'function') {
            return window.DashboardAuth.getCSRFToken();
        }
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.getAttribute('content')) {
            return meta.getAttribute('content');
        }
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function handleUnauthorized(response) {
        if (response && response.status === 401) {
            window.location.href = AUTH_REDIRECT;
            return true;
        }
        return false;
    }

    /**
     * Fetch wrapper with CSRF, JSON handling, and 401 redirect.
     * @param {string} endpoint
     * @param {RequestInit} [options]
     * @returns {Promise<any>}
     */
    function apiFetch(endpoint, options) {
        var opts = options || {};
        var headers = Object.assign(
            { Accept: 'application/json' },
            opts.headers || {}
        );

        if (opts.body && typeof opts.body === 'string' && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        var csrf = getCSRFToken();
        if (csrf && (!opts.method || opts.method.toUpperCase() !== 'GET')) {
            headers['X-CSRFToken'] = csrf;
        }

        var url = endpoint.indexOf('/api/') === 0 ? endpoint : API_BASE + endpoint.replace(/^\//, '');

        // Add cache-busting parameter to GET requests
        if (!opts.method || opts.method.toUpperCase() === 'GET') {
            url += (url.includes('?') ? '&' : '?') + '_=' + new Date().getTime();
        }

        return fetch(url, {
            method: opts.method || 'GET',
            credentials: opts.credentials || 'same-origin',
            headers: headers,
            body: opts.body || undefined
        }).then(function (response) {
            if (handleUnauthorized(response)) {
                return Promise.reject(new Error('Unauthorized'));
            }
            if (!response.ok) {
                return response.json().catch(function () {
                    return {};
                }).then(function (errData) {
                    var msg = errData.detail || errData.message || ('HTTP ' + response.status);
                    return Promise.reject(new Error(msg));
                });
            }
            if (response.status === 204) {
                return null;
            }
            var contentType = response.headers.get('content-type') || '';
            if (contentType.indexOf('application/json') !== -1) {
                return response.json();
            }
            return response.text();
        });
    }

    function extractList(data) {
        if (Array.isArray(data)) {
            return data;
        }
        if (data && Array.isArray(data.results)) {
            return data.results;
        }
        return [];
    }

    /* ── Chart ────────────────────────────────────────────────── */

    function getPrimaryColor() {
        var root = document.documentElement;
        var color = getComputedStyle(root).getPropertyValue('--clr-primary').trim();
        return color || '#6a00f4';
    }

    function initSalesChart() {
        var canvas = document.getElementById('salesChart');
        if (!canvas || typeof Chart === 'undefined') {
            return null;
        }

        var primary = getPrimaryColor();

        salesChartInstance = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Sotuvlar',
                    data: [],
                    borderColor: primary,
                    backgroundColor: 'rgba(106, 0, 244, 0.08)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });

        loadSalesChartData(getChartPeriod());

        var periodSelect = document.getElementById('chartPeriod');
        if (periodSelect) {
            periodSelect.addEventListener('change', function () {
                loadSalesChartData(periodSelect.value);
            });
        }

        return salesChartInstance;
    }

    function getChartPeriod() {
        var el = document.getElementById('chartPeriod');
        return el ? el.value : '30';
    }

    function loadSalesChartData(days) {
        apiFetch('stats/sales/?days=' + encodeURIComponent(days))
            .then(function (data) {
                if (!salesChartInstance || !data) {
                    return;
                }
                if (data.labels && data.labels.length > 0) {
                    salesChartInstance.data.labels = data.labels;
                    salesChartInstance.data.datasets[0].data = data.values || data.data || [];
                    salesChartInstance.update();
                } else {
                    salesChartInstance.data.labels = ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak'];
                    salesChartInstance.data.datasets[0].data = [12, 19, 14, 25, 22, 30, 28];
                    salesChartInstance.update();
                }
            })
            .catch(function () {
                if (salesChartInstance) {
                    salesChartInstance.data.labels = ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak'];
                    salesChartInstance.data.datasets[0].data = [12, 19, 14, 25, 22, 30, 28];
                    salesChartInstance.update();
                }
            });
    }

    /* ── Data fetchers ────────────────────────────────────────── */

    function fetchDashboardStats() {
        return apiFetch('stats/main/');
    }

    function renderDashboardStats(stats) {
        if (!stats) return;
        for (const key in stats) {
            const el = document.getElementById(`stat-${key}`);
            if (el) {
                el.textContent = stats[key];
            }
        }
    }

    function fetchRecentOrders() {
        return apiFetch('orders/recent/').then(extractList);
    }

    function fetchCategories() {
        return apiFetch('categories/').then(extractList);
    }

    function fetchProducts() {
        return apiFetch('products/').then(extractList);
    }

    function fetchUsers() {
        return apiFetch('users/').then(extractList);
    }

    function renderRecentOrders(orders) {
        var table = document.getElementById('recentOrders');
        if (!table) {
            return;
        }
        var tbody = table.querySelector('tbody');
        if (!tbody) {
            return;
        }

        if (!orders.length) {
            tbody.innerHTML =
                '<tr class="data-table__empty"><td colspan="5">' +
                '<i class="fa-solid fa-inbox"></i><span>Hozircha buyurtmalar yo\'q</span></td></tr>';
            return;
        }

        tbody.innerHTML = orders.map(function (order) {
            var statusIcon = 'fa-circle-info';
            if (order.status === 'Delivered') {
                statusIcon = 'fa-circle-check';
            } else if (order.status === 'Pending') {
                statusIcon = 'fa-hourglass-half';
            } else if (order.status === 'Cancelled') {
                statusIcon = 'fa-circle-xmark';
            }
            return '<tr>' +
                '<td><strong>#' + escapeHtml(String(order.id)) + '</strong></td>' +
                '<td><i class="fa-solid fa-circle-user"></i> ' + escapeHtml(order.customer || order.username || '—') + '</td>' +
                '<td>' + escapeHtml(String(order.total || order.total_price || 0)) + ' so\'m</td>' +
                '<td><i class="fa-solid ' + statusIcon + '"></i> ' + escapeHtml(order.status || '—') + '</td>' +
                '<td>' + escapeHtml(formatDate(order.created_at || order.date)) + '</td>' +
                '</tr>';
        }).join('');
    }

    function populateCategoriesWidget(categories) {
        var widget = document.getElementById('categoriesWidget');
        if (!widget) {
            return;
        }
        if (!categories.length) {
            widget.innerHTML = '<p class="widget-placeholder"><i class="fa-solid fa-inbox"></i> Kategoriyalar yo\'q</p>';
            return;
        }
        widget.innerHTML = '<ul class="widget-list">' + categories.slice(0, 8).map(function (cat) {
            return '<li class="widget-list__item">' +
                '<i class="fa-solid fa-layer-group"></i> ' +
                '<span>' + escapeHtml(cat.name) + '</span>' +
                '<span class="widget-list__count">' + escapeHtml(String(cat.product_count || cat.medicines_count || 0)) + '</span>' +
                '</li>';
        }).join('') + '</ul>';
    }

    /* ── UI helpers ───────────────────────────────────────────── */

    function escapeHtml(str) {
        if (str == null) {
            return '';
        }
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(value) {
        if (!value) {
            return '—';
        }
        try {
            var d = new Date(value);
            if (isNaN(d.getTime())) {
                return String(value);
            }
            return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return String(value);
        }
    }

    function initSidebarToggle() {
        var toggle = document.getElementById('sidebarToggle');
        var wrapper = document.getElementById('dashboardWrapper');
        var sidebar = document.getElementById('sidebar');
        if (!toggle || !wrapper) {
            return;
        }
        toggle.addEventListener('click', function () {
            wrapper.classList.toggle('sidebar-collapsed');
            if (sidebar) {
                sidebar.classList.toggle('sidebar--open');
            }
            if (salesChartInstance) {
                setTimeout(function () {
                    salesChartInstance.resize();
                }, 300);
            }
        });
    }

    function initResponsiveHandler() {
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                if (salesChartInstance) {
                    salesChartInstance.resize();
                }
            }, 150);
        });
    }

    function alertDismiss() {
        document.querySelectorAll('.alert-close').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var alert = btn.closest('.alert');
                if (alert) {
                    alert.remove();
                }
            });
        });
    }

    /* ── Theme & accent ───────────────────────────────────────── */

    var pendingTheme = null;
    var pendingAccent = null;

    function applyTheme(mode, persist) {
        var root = document.documentElement;
        var resolved = mode;

        if (mode === 'auto') {
            resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }

        root.setAttribute('data-theme', resolved);
        if (persist !== false) {
            localStorage.setItem(THEME_KEY, mode);
            localStorage.setItem('dashboard_theme', JSON.stringify({ theme: mode, updated_at: new Date().toISOString() }));
        }
    }

    function initThemeSwitch() {
        var saved = localStorage.getItem(THEME_KEY) || 'light';
        applyTheme(saved, false);
        pendingTheme = saved;

        document.querySelectorAll('input[name="theme"]').forEach(function (radio) {
            if (radio.value === saved) {
                radio.checked = true;
            }
            radio.addEventListener('change', function () {
                if (radio.checked) {
                    pendingTheme = radio.value;
                    applyTheme(radio.value, false); // Preview only
                }
            });
        });

        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
            var current = pendingTheme || localStorage.getItem(THEME_KEY);
            if (current === 'auto') {
                applyTheme('auto', false);
            }
        });
    }

    function applyAccentColor(color, persist) {
        if (!color) {
            return;
        }
        document.documentElement.style.setProperty('--clr-primary', color);
        if (persist !== false) {
            localStorage.setItem(ACCENT_KEY, color);
        }

        if (salesChartInstance) {
            salesChartInstance.data.datasets[0].borderColor = color;
            salesChartInstance.update();
        }
    }

    function initAccentColorChange() {
        var saved = localStorage.getItem(ACCENT_KEY);
        if (saved) {
            applyAccentColor(saved, false);
        }
        pendingAccent = saved;

        document.querySelectorAll('input[name="accent"]').forEach(function (radio) {
            if (saved && radio.value === saved) {
                radio.checked = true;
            }
            radio.addEventListener('change', function () {
                if (radio.checked) {
                    pendingAccent = radio.value;
                    document.documentElement.style.setProperty('--preview-primary', radio.value);
                }
            });
        });

        var customPicker = document.getElementById('customAccent');
        if (customPicker) {
            if (saved) {
                customPicker.value = saved;
            }
            customPicker.addEventListener('input', function () {
                pendingAccent = customPicker.value;
                document.documentElement.style.setProperty('--preview-primary', customPicker.value);
            });
        }

        var saveBtn = document.getElementById('btnSaveCustomize');
        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                var theme = pendingTheme || localStorage.getItem(THEME_KEY) || 'light';
                var accent = pendingAccent || localStorage.getItem(ACCENT_KEY) || '#6a00f4';

                applyTheme(theme, true);
                applyAccentColor(accent, true);

                apiFetch('settings/', {
                    method: 'POST',
                    body: JSON.stringify({ theme: theme, accent: accent })
                }).then(function () {
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({ icon: 'success', title: 'Saqlandi', text: 'Sozlamalar muvaffaqiyatli saqlandi.', confirmButtonText: 'OK' });
                    }
                }).catch(function () {
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({ icon: 'info', title: 'Mahalliy saqlandi', text: 'Sozlamalar brauzerda saqlandi.', confirmButtonText: 'OK' });
                    }
                });
            });
        }
    }

    /* ── Table search ─────────────────────────────────────────── */

    function initTableSearch() {
        var input = document.getElementById('tableSearch');
        if (!input) {
            return;
        }
        var table = document.getElementById('dataTable') || document.getElementById('recentOrders') || document.getElementById('ordersTable');
        if (!table) {
            return;
        }

        input.addEventListener('input', function () {
            var query = input.value.toLowerCase().trim();
            var rows = table.querySelectorAll('tbody tr');
            var visible = 0;

            rows.forEach(function (row) {
                if (row.classList.contains('data-table__empty')) {
                    return;
                }
                var text = row.textContent.toLowerCase();
                var match = !query || text.indexOf(query) !== -1;
                row.style.display = match ? '' : 'none';
                if (match) {
                    visible += 1;
                }
            });

            var countEl = document.getElementById('tableCount');
            if (countEl) {
                countEl.textContent = visible + ' ta qator';
            }
        });
    }

    /* ── Password toggle ──────────────────────────────────────── */

    function initPasswordToggle() {
        var toggle = document.getElementById('passwordToggle');
        var pwd = document.getElementById('id_password');
        if (!toggle || !pwd) {
            return;
        }
        toggle.addEventListener('click', function () {
            var isPassword = pwd.type === 'password';
            pwd.type = isPassword ? 'text' : 'password';
            var icon = toggle.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye', !isPassword);
                icon.classList.toggle('fa-eye-slash', isPassword);
            }
        });
    }

    /* ── Vendor integrations ──────────────────────────────────── */

    function initVendorPlugins() {
        if (typeof WOW !== 'undefined') {
            new WOW({ live: false }).init();
        }

        if (typeof PerfectScrollbar !== 'undefined') {
            var sidebarNav = document.getElementById('sidebarNav');
            if (sidebarNav) {
                new PerfectScrollbar(sidebarNav, { suppressScrollX: true });
            }
        }

        if (typeof jQuery !== 'undefined' && jQuery.fn.select2) {
            jQuery('#chartPeriod, .select2-field').select2({ minimumResultsForSearch: Infinity, width: '100%' });
        }

        if (typeof jQuery !== 'undefined' && jQuery.fn.slick) {
            jQuery('.slick-carousel').slick({ dots: true, arrows: true, infinite: true });
        }

        if (typeof lightbox !== 'undefined') {
            lightbox.option({ resizeDuration: 200, wrapAround: true });
        }

        var calendarEl = document.getElementById('dashboardCalendar');
        if (calendarEl && typeof FullCalendar !== 'undefined') {
            new FullCalendar.Calendar(calendarEl, {
                initialView: 'dayGridMonth',
                headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' },
                events: API_BASE + 'calendar/events/'
            }).render();
        }
    }

    /* ── Dashboard page bootstrap ─────────────────────────────── */

    function initDashboardPage() {
        if (document.getElementById('salesChart')) {
            initSalesChart();
        }

        fetchDashboardStats()
            .then(renderDashboardStats)
            .catch(function () { /* SSR fallback */ });

        fetchRecentOrders()
            .then(renderRecentOrders)
            .catch(function () { /* SSR fallback */ });

        fetchCategories()
            .then(populateCategoriesWidget)
            .catch(function () { /* SSR fallback */ });
    }

    /* ── Init ─────────────────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initSidebarToggle();
        initResponsiveHandler();
        alertDismiss();
        initThemeSwitch();
        initAccentColorChange();
        initTableSearch();
        initPasswordToggle();
        initVendorPlugins();
        initDashboardPage();
    });

    window.Dashboard = {
        API_BASE: API_BASE,
        getCSRFToken: getCSRFToken,
        apiFetch: apiFetch,
        extractList: extractList,
        escapeHtml: escapeHtml,
        formatDate: formatDate,
        initSalesChart: initSalesChart,
        fetchRecentOrders: fetchRecentOrders,
        fetchCategories: fetchCategories,
        fetchProducts: fetchProducts,
        fetchUsers: fetchUsers,
        alertDismiss: alertDismiss
    };
})();