/**
 * OnlinePharmacy — header.js (Delivery)
 * Header UI for delivery dashboard
 * - User dropdown interaction
 * - Profile display
 */

(function () {
    'use strict';

    function initTopbarUser() {
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
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
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

    document.addEventListener('DOMContentLoaded', function () {
        initTopbarUser();
    });

    window.DeliveryHeader = {
        initTopbarUser: initTopbarUser
    };
})();
