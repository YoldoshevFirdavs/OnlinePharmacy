/**
 * OnlinePharmacy — deliverer.js
 * Deliverer dashboard uchun minimal JS:
 * - Sidebar collapse/expand (desktop + mobile)
 * - Mobile overlay
 * - Alert auto-close
 * - Settings form submit feedback
 */
(function () {
    'use strict';

    /* ── Sidebar Toggle ─────────────────────────────────────────────── */

    var sidebar = document.getElementById('delivererSidebar');
    var mainArea = document.getElementById('delivererMain');
    var toggleBtn = document.getElementById('delivererSidebarToggle');
    var overlay = document.getElementById('delivererOverlay');

    var COLLAPSED_KEY = 'deliverer_sidebar_collapsed';

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function setSidebarState(collapsed) {
        if (!sidebar) return;
        if (isMobile()) {
            // Mobile: show/hide via mobile-open class
            if (collapsed) {
                sidebar.classList.remove('mobile-open');
                if (overlay) overlay.classList.remove('active');
            } else {
                sidebar.classList.add('mobile-open');
                if (overlay) overlay.classList.add('active');
            }
        } else {
            // Desktop: collapse width
            if (collapsed) {
                sidebar.classList.add('collapsed');
                if (mainArea) mainArea.classList.add('sidebar-collapsed');
            } else {
                sidebar.classList.remove('collapsed');
                if (mainArea) mainArea.classList.remove('sidebar-collapsed');
            }
            try {
                localStorage.setItem(COLLAPSED_KEY, collapsed ? '1' : '0');
            } catch (e) { /* ignore */ }
        }
    }

    function initSidebar() {
        if (!sidebar) return;

        // Restore state on desktop
        if (!isMobile()) {
            try {
                var saved = localStorage.getItem(COLLAPSED_KEY);
                if (saved === '1') {
                    setSidebarState(true);
                }
            } catch (e) { /* ignore */ }
        }

        if (toggleBtn) {
            toggleBtn.addEventListener('click', function () {
                if (isMobile()) {
                    var isOpen = sidebar.classList.contains('mobile-open');
                    setSidebarState(isOpen); // toggle
                } else {
                    var isCollapsed = sidebar.classList.contains('collapsed');
                    setSidebarState(!isCollapsed);
                }
            });
        }

        // Close sidebar when overlay is clicked (mobile)
        if (overlay) {
            overlay.addEventListener('click', function () {
                setSidebarState(true);
            });
        }

        // Keyboard: Escape closes mobile sidebar
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isMobile() && sidebar.classList.contains('mobile-open')) {
                setSidebarState(true);
            }
        });

        // Handle resize
        var resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                if (!isMobile()) {
                    sidebar.classList.remove('mobile-open');
                    if (overlay) overlay.classList.remove('active');
                }
            }, 150);
        });
    }

    /* ── Alert Auto-close ───────────────────────────────────────────── */

    function initAlerts() {
        var closeBtns = document.querySelectorAll('.deliverer-alert__close');
        closeBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var alert = btn.closest('.deliverer-alert');
                if (alert) {
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-4px)';
                    alert.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                    setTimeout(function () {
                        alert.remove();
                    }, 280);
                }
            });
        });

        // Auto-dismiss success alerts after 5s
        var successAlerts = document.querySelectorAll('.deliverer-alert--success');
        successAlerts.forEach(function (alert) {
            setTimeout(function () {
                if (alert && alert.parentNode) {
                    alert.style.opacity = '0';
                    alert.style.transition = 'opacity 0.4s ease';
                    setTimeout(function () { alert.remove(); }, 420);
                }
            }, 5000);
        });
    }

    /* ── Settings Form Feedback ─────────────────────────────────────── */

    function initSettingsForm() {
        var form = document.getElementById('delivererSettingsForm');
        if (!form) return;

        form.addEventListener('submit', function () {
            var submitBtn = form.querySelector('#delivererSettingsSaveBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saqlanmoqda...';
            }
        });
    }

    /* ── Map Placeholder ────────────────────────────────────────────── */

    function initMapPlaceholder() {
        var mapDiv = document.getElementById('deliveryMap');
        if (!mapDiv) return;

        // Pulse animation for the icon
        var icon = mapDiv.querySelector('.map-placeholder-icon');
        if (icon) {
            var opacity = 0.4;
            var direction = -1;
            setInterval(function () {
                opacity += direction * 0.015;
                if (opacity <= 0.2) direction = 1;
                if (opacity >= 0.55) direction = -1;
                icon.style.opacity = opacity.toFixed(2);
            }, 60);
        }
    }

    /* ── Topbar User Dropdown ───────────────────────────────────────── */

    function initTopbarDropdown() {
        var topbarUser = document.getElementById('delivererTopbarUser');
        var dropdown = document.getElementById('delivererTopbarDropdown');
        if (!topbarUser || !dropdown) return;

        function toggleDropdown(e) {
            if (e) e.stopPropagation();
            var isOpen = dropdown.style.display === 'block';
            dropdown.style.display = isOpen ? 'none' : 'block';
            topbarUser.setAttribute('aria-expanded', String(!isOpen));
        }

        topbarUser.addEventListener('click', toggleDropdown);
        topbarUser.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleDropdown(e);
            }
            if (e.key === 'Escape') {
                dropdown.style.display = 'none';
                topbarUser.setAttribute('aria-expanded', 'false');
                topbarUser.focus();
            }
        });

        document.addEventListener('click', function (event) {
            if (!topbarUser.contains(event.target) && !dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
                topbarUser.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ── Page loader on nav click ───────────────────────────────────── */

    function initNavLoader() {
        var loader = document.getElementById('delivererLoader');
        if (!loader) return;
        var links = document.querySelectorAll('a[href]');
        links.forEach(function (link) {
            link.addEventListener('click', function (e) {
                var href = this.getAttribute('href');
                if (href && href !== '#' && !href.startsWith('javascript:') && !href.startsWith('mailto:')) {
                    loader.classList.add('show');
                }
            });
        });
        window.addEventListener('pageshow', function (event) {
            if (event.persisted) loader.classList.remove('show');
        });
    }

    /* ── Init ───────────────────────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        initAlerts();
        initSettingsForm();
        initMapPlaceholder();
        initTopbarDropdown();
        initNavLoader();
    });

    window.DelivererDashboard = {
        setSidebarState: setSidebarState,
        initSidebar: initSidebar,
    };

})();
