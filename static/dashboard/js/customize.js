/**
 * OnlinePharmacy Dashboard — Customize Page Module
 * Brand name, sticker, and accent color customization
 */
(function () {
    'use strict';

    var stickerPicker = document.getElementById('stickerPicker');
    var liveSticker = document.getElementById('livePreviewSticker');
    var brandNameInput = document.getElementById('inputBrandName');
    var liveName = document.getElementById('livePreviewName');
    var colorPalette = document.getElementById('colorPalette');
    var customColorPicker = document.getElementById('customAccent');
    var clearStickerBtn = document.getElementById('btnClearSticker');

    /* ── Sticker Picker Logic ──────────────────────────────────── */

    function initStickerPicker() {
        if (!stickerPicker) return;

        var savedSticker = localStorage.getItem('dashboard-sticker') || '🏥';

        // Set active sticker
        document.querySelectorAll('.sticker-btn').forEach(function (btn) {
            if (btn.dataset.sticker === savedSticker) {
                btn.classList.add('sticker-btn--active');
            } else {
                btn.classList.remove('sticker-btn--active');
            }
        });

        liveSticker.textContent = savedSticker;

        // Click handler
        stickerPicker.querySelectorAll('.sticker-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var sticker = btn.dataset.sticker;
                
                // Update UI
                document.querySelectorAll('.sticker-btn').forEach(function (b) {
                    b.classList.remove('sticker-btn--active');
                });
                btn.classList.add('sticker-btn--active');
                
                // Update preview
                liveSticker.textContent = sticker;
                localStorage.setItem('dashboard-sticker', sticker);

                // Show toast
                showToast('Sticker o\'zgartirildi: ' + sticker);
            });
        });

        // Clear sticker
        if (clearStickerBtn) {
            clearStickerBtn.addEventListener('click', function () {
                document.querySelectorAll('.sticker-btn').forEach(function (b) {
                    b.classList.remove('sticker-btn--active');
                });
                liveSticker.textContent = '';
                localStorage.removeItem('dashboard-sticker');
                showToast('Sticker tozalandi');
            });
        }
    }

    /* ── Brand Name Logic ──────────────────────────────────────── */

    function initBrandName() {
        if (!brandNameInput || !liveName) return;

        var savedName = localStorage.getItem('dashboard-brand-name') || 'OnlinePharmacy';
        brandNameInput.value = savedName;
        liveName.textContent = savedName;

        brandNameInput.addEventListener('input', function () {
            var name = brandNameInput.value.trim() || 'OnlinePharmacy';
            liveName.textContent = name;
            localStorage.setItem('dashboard-brand-name', name);
        });
    }

    /* ── Accent Color Logic ────────────────────────────────────── */

    function initAccentColor() {
        if (!colorPalette) return;

        var savedAccent = localStorage.getItem('dashboard-accent') || '#6a00f4';

        // Update radio buttons
        document.querySelectorAll('input[name="accent"]').forEach(function (radio) {
            if (radio.value === savedAccent) {
                radio.checked = true;
            }
            radio.addEventListener('change', function () {
                applyAccentColor(this.value);
            });
        });

        // Custom color picker
        if (customColorPicker) {
            customColorPicker.value = savedAccent;
            customColorPicker.addEventListener('input', function () {
                applyAccentColor(customColorPicker.value);
            });
        }
    }

    function applyAccentColor(color) {
        if (!color) return;
        document.documentElement.style.setProperty('--preview-primary', color);
        localStorage.setItem('dashboard-accent', color);
        showToast('Rang o\'zgartirildi');
    }

    /* ── Toast Notification ────────────────────────────────────── */

    function showToast(message) {
        var toast = document.createElement('div');
        toast.className = 'customize-toast customize-toast--success';
        toast.innerHTML = message;
        document.body.appendChild(toast);

        // Show toast
        requestAnimationFrame(function () {
            toast.classList.add('customize-toast--show');
        });

        // Auto hide after 3 seconds
        setTimeout(function () {
            toast.classList.remove('customize-toast--show');
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 3000);
    }

    /* ── Init ────────────────────────────────────────────────────── */

    document.addEventListener('DOMContentLoaded', function () {
        initStickerPicker();
        initBrandName();
        initAccentColor();
    });

    window.Customize = {
        showToast: showToast,
        applyAccentColor: applyAccentColor
    };
})();
