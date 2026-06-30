/**
 * admin-dashboard.js
 * Online Pharmacy — Admin Dashboard JS
 *
 * Responsibilities:
 *  1. Theme toggle (light/dark) with localStorage persistence
 *  2. Primary colour picker with localStorage persistence
 *  3. Sidebar open/close (mobile)
 *  4. User dropdown menu
 *  5. Design settings panel
 *  6. AJAX data fetch → stat cards
 *  7. Chart.js initialisation (ordersChart, categoriesChart, productsChart)
 *  8. Sparkline mini-charts on stat cards
 *  9. Recent orders table with pagination (AJAX)
 * 10. Toast notification helper
 * 11. Animated counter
 */

/* ─────────────────────────────────────────────
   CONSTANTS
───────────────────────────────────────────── */
const ENDPOINTS = {
  stats:             '/api/v1/admin/stats/',
  ordersStats:       '/api/v1/admin/orders/stats/',
  categoriesDist:    '/api/v1/admin/categories/distribution/',
  productsTop:       '/api/v1/admin/products/top/',
  recentOrders:      '/api/v1/admin/orders/recent/',
};

// Palette presets for the design panel
const PALETTE_PRESETS = [
  '#4f7ef8', // Indigo (default)
  '#10b981', // Emerald
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Violet
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#f97316', // Orange
];

/* ─────────────────────────────────────────────
   STATE
───────────────────────────────────────────── */
let ordersChart      = null;
let categoriesChart  = null;
let productsChart    = null;
let sparklineCharts  = {};

let currentPage = 1;
const PAGE_SIZE = 10;

/* ─────────────────────────────────────────────
   INIT
───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  restoreTheme();
  restorePrimaryColor();
  initThemeToggle();
  initSidebar();
  initDropdowns();
  initSettingsPanel();
  initColorPalette();
  fetchStats();
  fetchOrdersChart();
  fetchCategoriesChart();
  fetchProductsChart();
  fetchRecentOrders(1);
});

/* ─────────────────────────────────────────────
   1. THEME
───────────────────────────────────────────── */
function restoreTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  updateThemeIcon();
}

function initThemeToggle() {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;

  toggle.addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
    // Re-render charts so grid lines update
    [ordersChart, categoriesChart, productsChart].forEach(ch => ch && ch.update());
  });
}

function updateThemeIcon() {
  const icon = document.querySelector('#themeToggle i');
  if (!icon) return;
  const isDark = document.documentElement.classList.contains('dark');
  icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
}

/* ─────────────────────────────────────────────
   2. PRIMARY COLOR
───────────────────────────────────────────── */
function restorePrimaryColor() {
  const saved = localStorage.getItem('primaryColor');
  if (saved) setPrimaryColor(saved, false);
}

/**
 * @param {string} hex   - e.g. '#4f7ef8'
 * @param {boolean} save - persist to localStorage
 */
function setPrimaryColor(hex, save = true) {
  document.documentElement.style.setProperty('--primary', hex);

  // Also update derived alpha vars
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  document.documentElement.style.setProperty('--primary-hover',    shadeColor(hex, -15));
  document.documentElement.style.setProperty('--primary-alpha-10', `rgba(${r},${g},${b},0.10)`);
  document.documentElement.style.setProperty('--primary-alpha-20', `rgba(${r},${g},${b},0.20)`);

  // Sync color swatch in topbar
  const swatch = document.querySelector('.color-swatch');
  if (swatch) swatch.style.background = hex;

  // Sync custom color input fields
  const colorInput = document.getElementById('customColorInput');
  const hexInput   = document.getElementById('hexInput');
  if (colorInput) colorInput.value = hex;
  if (hexInput)   hexInput.value   = hex;

  // Update active palette swatch
  document.querySelectorAll('.palette-swatch').forEach(sw => {
    sw.classList.toggle('active', sw.dataset.color === hex);
  });

  if (save) localStorage.setItem('primaryColor', hex);

  // Redraw charts with new primary
  updateChartsColor(hex);
}

function shadeColor(hex, percent) {
  const num = parseInt(hex.slice(1), 16);
  const amt = Math.round(2.55 * percent);
  const R = Math.min(255, Math.max(0, (num >> 16) + amt));
  const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + amt));
  const B = Math.min(255, Math.max(0, (num & 0x0000ff) + amt));
  return `#${(R << 16 | G << 8 | B).toString(16).padStart(6, '0')}`;
}

function updateChartsColor(hex) {
  if (ordersChart && ordersChart.data.datasets[0]) {
    ordersChart.data.datasets[0].borderColor = hex;
    const ctx = ordersChart.ctx;
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, hexToRgba(hex, 0.3));
    gradient.addColorStop(1, hexToRgba(hex, 0));
    ordersChart.data.datasets[0].backgroundColor = gradient;
    ordersChart.data.datasets[0].pointBackgroundColor = hex;
    ordersChart.update();
  }
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function getCurrentPrimary() {
  return getComputedStyle(document.documentElement)
    .getPropertyValue('--primary').trim() || '#4f7ef8';
}

/* ─────────────────────────────────────────────
   3. SIDEBAR (mobile)
───────────────────────────────────────────── */
function initSidebar() {
  const hamburger = document.getElementById('hamburgerBtn');
  const sidebar   = document.getElementById('adminSidebar');
  const overlay   = document.getElementById('sidebarOverlay');

  if (!hamburger || !sidebar) return;

  hamburger.addEventListener('click', () => toggleSidebar(true));
  overlay && overlay.addEventListener('click', () => toggleSidebar(false));

  // Close on nav link click (mobile UX)
  sidebar.querySelectorAll('.sidebar-nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 992) toggleSidebar(false);
    });
  });
}

function toggleSidebar(open) {
  const sidebar  = document.getElementById('adminSidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  sidebar  && sidebar.classList.toggle('open', open);
  overlay  && overlay.classList.toggle('show', open);
  document.body.style.overflow = open ? 'hidden' : '';
}

/* ─────────────────────────────────────────────
   4. DROPDOWNS
───────────────────────────────────────────── */
function initDropdowns() {
  document.querySelectorAll('[data-dropdown]').forEach(trigger => {
    const targetId = trigger.dataset.dropdown;
    const menu     = document.getElementById(targetId);
    if (!menu) return;

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = menu.classList.contains('show');
      closeAllDropdowns();
      if (!isOpen) menu.classList.add('show');
    });
  });

  document.addEventListener('click', closeAllDropdowns);
}

function closeAllDropdowns() {
  document.querySelectorAll('.dropdown-menu-custom.show')
    .forEach(m => m.classList.remove('show'));
}

/* ─────────────────────────────────────────────
   5. DESIGN SETTINGS PANEL
───────────────────────────────────────────── */
function initSettingsPanel() {
  const tab   = document.getElementById('settingsTab');
  const panel = document.getElementById('settingsPanel');
  const close = document.getElementById('closePanelBtn');

  if (!tab || !panel) return;

  tab.addEventListener('click', () => panel.classList.toggle('open'));
  close && close.addEventListener('click', () => panel.classList.remove('open'));
}

function initColorPalette() {
  const palette = document.getElementById('colorPalette');
  if (!palette) return;

  // Build swatches
  PALETTE_PRESETS.forEach(hex => {
    const btn = document.createElement('button');
    btn.className = 'palette-swatch';
    btn.style.background = hex;
    btn.dataset.color = hex;
    btn.title = hex;
    btn.setAttribute('aria-label', `Set primary colour to ${hex}`);
    btn.addEventListener('click', () => setPrimaryColor(hex));
    palette.appendChild(btn);
  });

  // Custom colour input
  const colorInput = document.getElementById('customColorInput');
  const hexInput   = document.getElementById('hexInput');

  if (colorInput) {
    colorInput.addEventListener('input', () => {
      setPrimaryColor(colorInput.value);
    });
  }

  if (hexInput) {
    hexInput.addEventListener('change', () => {
      const val = hexInput.value.startsWith('#') ? hexInput.value : '#' + hexInput.value;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) setPrimaryColor(val);
    });
  }

  // Quick topbar color picker
  const topbarColorInput = document.getElementById('topbarColorPicker');
  if (topbarColorInput) {
    topbarColorInput.addEventListener('input', () => {
      setPrimaryColor(topbarColorInput.value);
    });
  }
}

/* ─────────────────────────────────────────────
   6. STAT CARDS — AJAX
───────────────────────────────────────────── */
async function fetchStats() {
  try {
    const resp = await fetch(ENDPOINTS.stats, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    animateCounter('statCategories', data.categories_count ?? 0);
    animateCounter('statProducts',   data.products_count   ?? 0);
    animateCounter('statCustomers',  data.users_count      ?? 0);
    animateCounter('statOrders',     data.orders_count     ?? 0);

    // Render sparklines
    renderSparkline('sparkCategories', generateSparkData(data.categories_count));
    renderSparkline('sparkProducts',   generateSparkData(data.products_count));
    renderSparkline('sparkCustomers',  generateSparkData(data.users_count));
    renderSparkline('sparkOrders',     generateSparkData(data.orders_count));

  } catch (err) {
    console.warn('[Dashboard] Stats fetch failed, using mock data:', err);

    // Graceful fallback with mock values
    const mock = { categories_count: 24, products_count: 342, users_count: 1850, orders_count: 5920 };
    animateCounter('statCategories', mock.categories_count);
    animateCounter('statProducts',   mock.products_count);
    animateCounter('statCustomers',  mock.users_count);
    animateCounter('statOrders',     mock.orders_count);

    ['sparkCategories','sparkProducts','sparkCustomers','sparkOrders'].forEach(id => {
      renderSparkline(id, generateSparkData(100));
    });
  }
}

function generateSparkData(peak) {
  const arr = [];
  for (let i = 0; i < 8; i++) {
    arr.push(Math.floor(peak * (0.5 + 0.5 * Math.random())));
  }
  arr[arr.length - 1] = peak; // end at peak
  return arr;
}

/* ─────────────────────────────────────────────
   7a. CHART — Orders Line
───────────────────────────────────────────── */
async function fetchOrdersChart() {
  const el = document.getElementById('ordersChart');
  if (!el) return;

  let labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  let data   = [85, 120, 95, 160, 130, 200, 175];

  try {
    const resp = await fetch(ENDPOINTS.ordersStats, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (resp.ok) {
      const json = await resp.json();
      labels = json.labels || labels;
      data   = json.data   || data;
    }
  } catch (e) {
    console.warn('[Dashboard] Orders stats fetch failed, using mock data');
  }

  const ctx      = el.getContext('2d');
  const primary  = getCurrentPrimary();
  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, hexToRgba(primary, 0.35));
  gradient.addColorStop(1, hexToRgba(primary, 0));

  ordersChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Orders',
        data,
        borderColor: primary,
        backgroundColor: gradient,
        borderWidth: 2.5,
        pointBackgroundColor: primary,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 7,
        fill: true,
        tension: 0.42,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#1a1d2e',
          titleColor: getComputedStyle(document.documentElement).getPropertyValue('--text').trim(),
          bodyColor:  getComputedStyle(document.documentElement).getPropertyValue('--muted').trim(),
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--border').trim(),
          borderWidth: 1,
          padding: 12,
          cornerRadius: 10,
          displayColors: false,
          callbacks: {
            label: ctx => ` ${ctx.parsed.y} orders`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-tick').trim(),
            font: { size: 11, family: "'Inter', sans-serif" }
          }
        },
        y: {
          grid: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim(),
          },
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-tick').trim(),
            font: { size: 11 },
            padding: 8
          }
        }
      }
    }
  });
}

/* ─────────────────────────────────────────────
   7b. CHART — Categories Pie
───────────────────────────────────────────── */
async function fetchCategoriesChart() {
  const el = document.getElementById('categoriesChart');
  if (!el) return;

  let labels = ['Antibiotics', 'Vitamins', 'Painkillers', 'Supplements', 'Other'];
  let data   = [28, 35, 19, 12, 6];

  try {
    const resp = await fetch(ENDPOINTS.categoriesDist, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (resp.ok) {
      const json = await resp.json();
      labels = json.labels || labels;
      data   = json.data   || data;
    }
  } catch (e) {
    console.warn('[Dashboard] Categories dist fetch failed, using mock data');
  }

  const pieColors = [
    getCurrentPrimary(),
    '#10b981', '#f59e0b', '#8b5cf6', '#ef4444',
    '#06b6d4', '#ec4899', '#f97316'
  ].slice(0, labels.length);

  const ctx = el.getContext('2d');
  categoriesChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: pieColors,
        borderWidth: 2,
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#1a1d2e',
        hoverOffset: 10,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--muted').trim(),
            padding: 14,
            usePointStyle: true,
            pointStyle: 'circle',
            font: { size: 11, family: "'Inter', sans-serif" }
          }
        },
        tooltip: {
          backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim(),
          titleColor: getComputedStyle(document.documentElement).getPropertyValue('--text').trim(),
          bodyColor:  getComputedStyle(document.documentElement).getPropertyValue('--muted').trim(),
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--border').trim(),
          borderWidth: 1,
          padding: 12,
          cornerRadius: 10,
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed}%`
          }
        }
      }
    }
  });
}

/* ─────────────────────────────────────────────
   7c. CHART — Top Products Bar
───────────────────────────────────────────── */
async function fetchProductsChart() {
  const el = document.getElementById('productsChart');
  if (!el) return;

  let labels = ['Paracetamol', 'Amoxicillin', 'Vitamin D3', 'Ibuprofen', 'Omega-3'];
  let data   = [420, 370, 310, 280, 240];

  try {
    const resp = await fetch(ENDPOINTS.productsTop, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (resp.ok) {
      const json = await resp.json();
      labels = json.labels || labels;
      data   = json.data   || data;
    }
  } catch (e) {
    console.warn('[Dashboard] Products top fetch failed, using mock data');
  }

  const primary = getCurrentPrimary();
  const ctx = el.getContext('2d');
  productsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Units sold',
        data,
        backgroundColor: hexToRgba(primary, 0.75),
        borderColor: primary,
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false,
        hoverBackgroundColor: primary,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim(),
          titleColor: getComputedStyle(document.documentElement).getPropertyValue('--text').trim(),
          bodyColor:  getComputedStyle(document.documentElement).getPropertyValue('--muted').trim(),
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--border').trim(),
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            label: ctx => ` ${ctx.parsed.x} units`
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim(),
          },
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-tick').trim(),
            font: { size: 11 }
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-tick').trim(),
            font: { size: 11 }
          }
        }
      }
    }
  });
}

/* ─────────────────────────────────────────────
   8. SPARKLINES
───────────────────────────────────────────── */
function renderSparkline(canvasId, dataArr) {
  const el = document.getElementById(canvasId);
  if (!el) return;

  const primary = getCurrentPrimary();

  if (sparklineCharts[canvasId]) {
    sparklineCharts[canvasId].destroy();
  }

  sparklineCharts[canvasId] = new Chart(el, {
    type: 'line',
    data: {
      labels: dataArr.map((_, i) => i),
      datasets: [{
        data: dataArr,
        borderColor: primary,
        backgroundColor: hexToRgba(primary, 0.15),
        borderWidth: 1.5,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
      }]
    },
    options: {
      responsive: false,
      animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}

/* ─────────────────────────────────────────────
   9. RECENT ORDERS TABLE
───────────────────────────────────────────── */
async function fetchRecentOrders(page = 1) {
  currentPage = page;
  const tbody = document.getElementById('ordersTableBody');
  const infoEl = document.getElementById('tableInfo');
  if (!tbody) return;

  // Show skeleton rows
  tbody.innerHTML = Array(5).fill(0).map(() => `
    <tr>
      ${Array(7).fill(0).map(() => `<td><span class="skeleton" style="height:14px;display:block;width:${60+Math.random()*60}%"></span></td>`).join('')}
    </tr>
  `).join('');

  try {
    const resp = await fetch(`${ENDPOINTS.recentOrders}?page=${page}&page_size=${PAGE_SIZE}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();

    renderOrdersTable(json.results || json.orders || [], json.count || 0, page);

  } catch (err) {
    console.warn('[Dashboard] Recent orders fetch failed, using mock data:', err);
    renderOrdersTable(getMockOrders(), 47, page);
  }
}

function renderOrdersTable(orders, total, page) {
  const tbody  = document.getElementById('ordersTableBody');
  const infoEl = document.getElementById('tableInfo');
  const paginEl = document.getElementById('paginationWrap');

  if (!tbody) return;

  if (!orders.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center;padding:40px;color:var(--muted)">
          <i class="fa-solid fa-inbox" style="font-size:28px;margin-bottom:10px;display:block"></i>
          No orders found
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = orders.map(order => `
    <tr>
      <td class="td-id" aria-label="Order ID">#${order.id}</td>
      <td>
        <div class="td-customer">
          <div class="customer-avatar" aria-hidden="true">${getInitials(order.customer_name || 'U N')}</div>
          <div>
            <div class="customer-name">${escHtml(order.customer_name || 'Unknown')}</div>
            <div class="customer-email">${escHtml(order.customer_email || '')}</div>
          </div>
        </div>
      </td>
      <td class="td-address" title="${escHtml(order.address || '')}">
        <i class="fa-solid fa-location-dot text-muted" aria-hidden="true"></i>
        ${escHtml(order.address || '—')}
      </td>
      <td>
        <span class="payment-badge">
          <i class="fa-solid fa-credit-card" aria-hidden="true"></i>
          ${escHtml(order.payment_method || 'Cash')}
        </span>
      </td>
      <td>
        <span class="status-badge status-badge--${(order.status || 'pending').toLowerCase().replace(' ', '-')}"
              aria-label="Status: ${escHtml(order.status || 'Pending')}">
          ${escHtml(order.status || 'Pending')}
        </span>
      </td>
      <td style="color:var(--muted);font-size:12px">
        <i class="fa-regular fa-calendar" aria-hidden="true"></i>
        ${formatDate(order.created_at)}
      </td>
      <td>
        <div class="td-actions">
          <a href="/dashboard/order/${order.id}/" class="btn-icon-sm btn-success"
             aria-label="View order #${order.id}" title="View">
            <i class="fa-solid fa-eye" aria-hidden="true"></i>
          </a>
          <a href="/dashboard/order/${order.id}/edit/" class="btn-icon-sm"
             aria-label="Edit order #${order.id}" title="Edit">
            <i class="fa-solid fa-pen" aria-hidden="true"></i>
          </a>
          ${window._isSuperadmin ? `
          <button class="btn-icon-sm btn-danger"
                  aria-label="Delete order #${order.id}"
                  title="Delete"
                  onclick="deleteOrder(${order.id})">
            <i class="fa-solid fa-trash" aria-hidden="true"></i>
          </button>` : ''}
        </div>
      </td>
    </tr>
  `).join('');

  // Update info
  const start = (page - 1) * PAGE_SIZE + 1;
  const end   = Math.min(page * PAGE_SIZE, total);
  if (infoEl) infoEl.textContent = `Showing ${start}–${end} of ${total} orders`;

  // Build pagination
  if (paginEl) renderPagination(paginEl, total, page);
}

function renderPagination(container, total, currentPage) {
  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (totalPages <= 1) { container.innerHTML = ''; return; }

  const pages = [];

  // Prev
  pages.push(`
    <li>
      <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''}
              aria-label="Previous page"
              onclick="fetchRecentOrders(${currentPage - 1})">
        <i class="fa-solid fa-chevron-left" aria-hidden="true"></i>
      </button>
    </li>`);

  // Pages
  for (let p = 1; p <= totalPages; p++) {
    if (totalPages > 7 && Math.abs(p - currentPage) > 2 && p !== 1 && p !== totalPages) {
      if (p === currentPage - 3 || p === currentPage + 3) pages.push(`<li><span style="padding:0 4px;color:var(--muted)">…</span></li>`);
      continue;
    }
    pages.push(`
      <li>
        <button class="page-btn ${p === currentPage ? 'page-btn--active' : ''}"
                aria-label="Page ${p}" aria-current="${p === currentPage ? 'page' : 'false'}"
                onclick="fetchRecentOrders(${p})">
          ${p}
        </button>
      </li>`);
  }

  // Next
  pages.push(`
    <li>
      <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''}
              aria-label="Next page"
              onclick="fetchRecentOrders(${currentPage + 1})">
        <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
      </button>
    </li>`);

  container.innerHTML = `<ul class="pagination" role="navigation" aria-label="Orders pagination">${pages.join('')}</ul>`;
}

/* ─────────────────────────────────────────────
   9a. DELETE ORDER (superadmin only)
───────────────────────────────────────────── */
async function deleteOrder(orderId) {
  if (!confirm(`Delete order #${orderId}? This cannot be undone.`)) return;

  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || getCookie('csrftoken');

  try {
    const resp = await fetch(`/api/v1/admin/orders/${orderId}/delete/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      }
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    showToast('Order deleted successfully', 'success');
    fetchRecentOrders(currentPage);
  } catch (err) {
    showToast('Failed to delete order', 'error');
    console.error('[deleteOrder]', err);
  }
}

/* ─────────────────────────────────────────────
   10. TOAST
───────────────────────────────────────────── */
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'polite');

  const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
  toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}" aria-hidden="true"></i>${escHtml(message)}`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s';
    setTimeout(() => toast.remove(), 320);
  }, 3500);
}

/* ─────────────────────────────────────────────
   11. ANIMATED COUNTER
───────────────────────────────────────────── */
function animateCounter(elementId, target, duration = 1200) {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.classList.remove('loading');
  const start     = 0;
  const startTime = performance.now();

  function update(now) {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current  = Math.round(eased * target);
    el.textContent = current.toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
}

/* ─────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────── */
function escHtml(str) {
  if (str == null) return '';
  return String(str).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[ch]);
}

function getInitials(name) {
  return (name || 'U N').split(' ').slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function getCookie(name) {
  return document.cookie.split('; ')
    .find(row => row.startsWith(name + '='))
    ?.split('=')?.[1] ?? '';
}

/* ─────────────────────────────────────────────
   MOCK DATA (fallback)
───────────────────────────────────────────── */
function getMockOrders() {
  const statuses  = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled'];
  const payments  = ['Cash', 'Card', 'Payme', 'Click', 'Uzum'];
  const names     = [
    ['Alisher Nazarov', 'a.nazarov@mail.uz'],
    ['Malika Tosheva', 'm.tosheva@mail.uz'],
    ['Bobur Xasanov', 'b.xasanov@mail.uz'],
    ['Nilufar Rahimova', 'n.rahimova@mail.uz'],
    ['Jasur Qodirov', 'j.qodirov@mail.uz'],
    ['Gulnora Abdullayeva', 'g.abdullayeva@mail.uz'],
    ['Otabek Mirzayev', 'o.mirzayev@mail.uz'],
    ['Sarvinoz Yunusova', 's.yunusova@mail.uz'],
    ['Kamol Ergashev', 'k.ergashev@mail.uz'],
    ['Dilnoza Tursunova', 'd.tursunova@mail.uz'],
  ];

  return Array.from({ length: 10 }, (_, i) => {
    const [customer_name, customer_email] = names[i % names.length];
    return {
      id: 1000 + i + (currentPage - 1) * 10,
      customer_name,
      customer_email,
      address: ['Yunusobod 5, Tashkent', 'Chilonzor 8, Tashkent', 'Olmazor 3, Tashkent'][i % 3],
      payment_method: payments[i % payments.length],
      status: statuses[i % statuses.length],
      created_at: new Date(Date.now() - i * 86400000 * 2).toISOString(),
    };
  });
}
