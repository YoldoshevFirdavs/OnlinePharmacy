/**
 * OnlinePharmacy Dashboard — Theme Manager
 * Preview vs Save behavior for Dashboard appearance customization.
 */
(function () {
    'use strict';

    var THEME_KEY = 'dashboard-theme';
    var ACCENT_KEY = 'dashboard-accent-color';

    var pendingTheme = null;
    var pendingAccent = null;
    var initialSavedTheme = null;
    var initialSavedAccent = null;

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

    function applyAccentColor(color, persist) {
        if (!color) return;
        document.documentElement.style.setProperty('--clr-primary', color);
        if (persist !== false) {
            localStorage.setItem(ACCENT_KEY, color);
        }
    }

    function previewAccentColor(color) {
        if (!color) return;
        document.documentElement.style.setProperty('--preview-primary', color);
    }

    function initThemeCustomizer() {
        var savedTheme = localStorage.getItem(THEME_KEY) || 'light';
        var savedAccent = localStorage.getItem(ACCENT_KEY) || '#6a00f4';
        var savedBrandName = localStorage.getItem('dashboard-brand-name') || '';
        var savedBrandSticker = localStorage.getItem('dashboard-brand-sticker') || '';

        // Apply saved theme & accent on page load
        applyTheme(savedTheme, false);
        applyAccentColor(savedAccent, false);

        pendingTheme = savedTheme;
        pendingAccent = savedAccent;
        initialSavedTheme = savedTheme;
        initialSavedAccent = savedAccent;

        // Restore saved brand name & sticker into inputs and sidebar
        var brandInput = document.getElementById('inputBrandName');
        if (brandInput && savedBrandName) {
            brandInput.value = savedBrandName;
        }
        _updatePreview(
            brandInput ? brandInput.value : '',
            savedBrandSticker
        );

        // Mark active sticker button
        if (savedBrandSticker) {
            document.querySelectorAll('.sticker-btn').forEach(function(btn) {
                btn.classList.toggle('sticker-btn--active', btn.dataset.sticker === savedBrandSticker);
            });
        }

        // Brand name input → live preview
        if (brandInput) {
            brandInput.addEventListener('input', function() {
                _updatePreview(brandInput.value, _getActiveStickerValue());
            });
        }

        // Sticker picker → live preview
        document.querySelectorAll('.sticker-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.sticker-btn').forEach(function(b) { b.classList.remove('sticker-btn--active'); });
                btn.classList.add('sticker-btn--active');
                _updatePreview(brandInput ? brandInput.value : '', btn.dataset.sticker);
            });
        });

        // Clear sticker
        var clearBtn = document.getElementById('btnClearSticker');
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                document.querySelectorAll('.sticker-btn').forEach(function(b) { b.classList.remove('sticker-btn--active'); });
                _updatePreview(brandInput ? brandInput.value : '', '');
            });
        }

        // Theme toggle (sun/moon switch)
        var toggle = document.getElementById('toggle');
        if (toggle) {
            if (savedTheme === 'dark') toggle.checked = true;
            toggle.addEventListener('change', function() {
                var newTheme = this.checked ? 'dark' : 'light';
                applyTheme(newTheme, true);
            });
        }

        // Theme radios
        document.querySelectorAll('input[name="theme"]').forEach(function(radio) {
            if (radio.value === savedTheme) radio.checked = true;
            radio.addEventListener('change', function() {
                if (radio.checked) {
                    pendingTheme = radio.value;
                    applyTheme(radio.value, false);
                }
            });
        });

        // Accent radios
        document.querySelectorAll('input[name="accent"]').forEach(function(radio) {
            if (radio.value === savedAccent) radio.checked = true;
            radio.addEventListener('change', function() {
                if (radio.checked) {
                    pendingAccent = radio.value;
                    applyAccentColor(radio.value, false);
                }
            });
        });

        // Custom color picker
        var customPicker = document.getElementById('customAccent');
        if (customPicker) {
            if (savedAccent) customPicker.value = savedAccent;
            customPicker.addEventListener('input', function() {
                pendingAccent = customPicker.value;
                applyAccentColor(customPicker.value, false);
            });
        }

        // Save button
        var saveBtn = document.getElementById('btnSaveCustomize');
        if (saveBtn) {
            saveBtn.addEventListener('click', function() {
                var selectedTheme = pendingTheme || localStorage.getItem(THEME_KEY) || 'light';
                var selectedAccent = pendingAccent || localStorage.getItem(ACCENT_KEY) || '#6a00f4';
                var selectedName = brandInput ? brandInput.value.trim() : '';
                var selectedSticker = _getActiveStickerValue();

                applyTheme(selectedTheme, true);
                applyAccentColor(selectedAccent, true);
                localStorage.setItem('dashboard-brand-name', selectedName);
                localStorage.setItem('dashboard-brand-sticker', selectedSticker);

                // Apply to sidebar brand immediately
                _applySidebarBrand(selectedName, selectedSticker);

                if (typeof Swal !== 'undefined') {
                    Swal.fire({ icon: 'success', title: 'Saqlandi', text: 'Dizayn sozlamalari saqlandi.', confirmButtonText: 'OK' });
                } else {
                    alert('Dizayn sozlamalari muvaffaqiyatli saqlandi.');
                }
            });
        }

        // Cancel button
        var cancelBtn = document.getElementById('btnCancelCustomize');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                applyTheme(initialSavedTheme || 'light', false);
                applyAccentColor(initialSavedAccent || '#6a00f4', false);
                document.querySelectorAll('input[name="theme"]').forEach(function(r) { r.checked = (r.value === initialSavedTheme); });
                document.querySelectorAll('input[name="accent"]').forEach(function(r) { r.checked = (r.value === initialSavedAccent); });
                if (customPicker) customPicker.value = initialSavedAccent || '#6a00f4';
                pendingTheme = initialSavedTheme;
                pendingAccent = initialSavedAccent;
            });
        }
    }

    function _getActiveStickerValue() {
        var active = document.querySelector('.sticker-btn--active');
        return active ? active.dataset.sticker : '';
    }

    function _updatePreview(name, sticker) {
        // Update customize page preview box
        var previewName = document.getElementById('livePreviewName');
        var previewSticker = document.getElementById('livePreviewSticker');
        if (previewName) previewName.textContent = name || 'PharmacyAdmin';
        if (previewSticker) previewSticker.textContent = sticker || '';

        // Update sidebar brand in real-time
        _applySidebarBrand(name, sticker);
    }

    function _applySidebarBrand(name, sticker) {
        var brandText = document.querySelector('#sidebarBrand .sidebar-brand-text');
        var brandSticker = document.querySelector('#sidebarBrand .sidebar-brand-sticker');
        if (brandText && name) brandText.textContent = name;
        if (brandSticker !== null) brandSticker.textContent = sticker || '🏥';
    }

    document.addEventListener('DOMContentLoaded', function () {
        initThemeCustomizer();
    });

    window.DashboardTheme = {
        applyTheme: applyTheme,
        applyAccentColor: applyAccentColor,
        initThemeCustomizer: initThemeCustomizer
    };
})();