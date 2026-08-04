/**
 * OnlinePharmacy — delivery.js
 * Delivery dashboard specific JavaScript
 * - Sidebar toggle functionality
 * - Settings form submit handling
 * - Map placeholder animations
 * - /me/ API integration
 */

(function () {
    'use strict';

    /* ── Sidebar Toggle ─────────────────────────────────────────────── */

    var sidebar = document.getElementById('delivererSidebar');
    var mainArea = document.getElementById('delivererMain');
    var toggleBtn = document.getElementById('delivererSidebarToggle');
    var overlay = document.getElementById('delivererOverlay');

    var COLLAPSED_KEY = 'delivery_sidebar_collapsed';

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function setSidebarState(collapsed) {
        if (!sidebar) return;

        if (isMobile()) {
            if (collapsed) {
                sidebar.classList.remove('mobile-open');
                if (overlay) overlay.classList.remove('active');
                if (mainArea) mainArea.classList.remove('sidebar-mobile-open');
            } else {
                sidebar.classList.add('mobile-open');
                if (overlay) overlay.classList.add('active');
                if (mainArea) mainArea.classList.add('sidebar-mobile-open');
            }
        } else {
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
                    setSidebarState(isOpen);
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

    /* ── Settings Form Submit ────────────────────────────────────────── */

    function initSettingsForm() {
        var form = document.getElementById('delivererSettingsForm');
        if (!form) return;

        form.addEventListener('submit', function (e) {
            e.preventDefault();

            var submitBtn = form.querySelector('#delivererSettingsSaveBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saqlanmoqda...';
            }

            // Collect form data
            var formData = {
                full_name: document.getElementById('id_full_name').value.trim(),
                email: document.getElementById('id_email').value.trim(),
                phone_number: document.getElementById('id_phone_number').value.trim(),
                vehicle_info: document.getElementById('id_vehicle_info').value.trim(),
                notify_order: document.getElementById('id_notify_order').checked,
                notify_status: document.getElementById('id_notify_status').checked,
                notify_push: document.getElementById('id_notify_push').checked,
            };

            var csrftoken = document.querySelector('meta[name="csrf-token"]');
            if (!csrftoken) return;
            csrftoken = csrftoken.getAttribute('content');

            // Send to /me/ endpoint
            fetch('/api/v1/dashboard/me/', {
                method: 'PUT',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
                credentials: 'same-origin'
            })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Failed to save');
                }
                return response.json();
            })
            .then(function (data) {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-check"></i> Saqlandi!';
                    setTimeout(function () {
                        submitBtn.innerHTML = '<i class="fas fa-save"></i> Saqlash';
                    }, 2000);
                }

                // Show success alert
                var alertDiv = document.createElement('div');
                alertDiv.className = 'deliverer-alert deliverer-alert--success';
                alertDiv.innerHTML = '<i class="fas fa-check-circle"></i><span>Profil muvaffaqiyatli saqlandi!</span><button class="deliverer-alert__close" aria-label="Close alert"><i class="fas fa-times"></i></button>';

                var messagesContainer = document.querySelector('.deliverer-messages');
                if (messagesContainer) {
                    messagesContainer.appendChild(alertDiv);
                }
            })
            .catch(function (error) {
                console.error('Error saving profile:', error);
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-save"></i> Saqlash';
                }

                // Show error alert
                var alertDiv = document.createElement('div');
                alertDiv.className = 'deliverer-alert deliverer-alert--error';
                alertDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>Profilni saqlashda xatolik yuz berdi.</span><button class="deliverer-alert__close" aria-label="Close alert"><i class="fas fa-times"></i></button>';

                var messagesContainer = document.querySelector('.deliverer-messages');
                if (messagesContainer) {
                    messagesContainer.appendChild(alertDiv);
                }
            });
        });
    }

    /* ── Map Placeholder Animation ────────────────────────────────────── */

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

    /* ── Initialize All ──────────────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        initTopbarDropdown();
        initAlerts();
        initSettingsForm();
        initMapPlaceholder();
    });

    /* ── Expose API ──────────────────────────────────────────────────── */

    window.DeliveryDashboard = {
        setSidebarState: setSidebarState,
        initSidebar: initSidebar,
        initTopbarDropdown: initTopbarDropdown,
        initAlerts: initAlerts,
        initSettingsForm: initSettingsForm,
        initMapPlaceholder: initMapPlaceholder
    };

})();
