/**
 * OnlinePharmacy — dashboard.js (Delivery)
 * Dashboard specific JavaScript
 * - Initialize deliverer profile data
 * - Map placeholder
 */

(function () {
    'use strict';

    // Load deliverer profile data from /me/ endpoint
    function loadDelivererProfile() {
        const csrftoken = document.querySelector('meta[name="csrf-token"]');
        if (!csrftoken) return;
        
        fetch('/api/v1/users/me/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrftoken.getAttribute('content'),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load profile');
            }
            return response.json();
        })
        .then(data => {
            // Update header display
            if (data.full_name) {
                const nameEl = document.getElementById('delivererName');
                if (nameEl) nameEl.textContent = data.full_name;
            }
            if (data.phone_number) {
                const phoneEl = document.getElementById('delivererPhone');
                if (phoneEl) phoneEl.textContent = data.phone_number;
            }
        })
        .catch(error => {
            console.error('Error loading profile:', error);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        loadDelivererProfile();
    });
})();
