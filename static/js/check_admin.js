document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    const loadingDiv = document.getElementById('loading');
    const errorMessageDiv = document.getElementById('error-message');
    const blockMessageDiv = document.getElementById('block-message');
    const adminConfirmForm = document.getElementById('admin-confirm-form');
    const emailInput = document.getElementById('email');
    const fullNameInput = document.getElementById('full_name');
    const phoneNumberInput = document.getElementById('phone_number');
    const confirmButton = adminConfirmForm.querySelector('button[type="submit"]');
    const attemptCountDiv = document.getElementById('attempt-count');
    const attemptsLeftSpan = document.getElementById('attempts-left');

    // For noscript fallback form
    const noscriptTokenInput = document.getElementById('noscript-token-input');
    if (noscriptTokenInput && token) {
        noscriptTokenInput.value = token;
    }

    if (!token) {
        displayError('Login token is missing.');
        return;
    }

    // Function to display error messages
    function displayError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        loadingDiv.style.display = 'none';
        adminConfirmForm.style.display = 'none';
        attemptCountDiv.style.display = 'none';
    }

    // Function to display block message
    function displayBlockMessage() {
        blockMessageDiv.style.display = 'block';
        loadingDiv.style.display = 'none';
        adminConfirmForm.style.display = 'none';
        attemptCountDiv.style.display = 'none';
        confirmButton.disabled = true; // Disable button if blocked
    }

    // Fetch user data for confirmation
    fetch(`/api/v1/users/admin/check/?token=${token}`)
        .then(response => {
            if (response.status === 403) { // Forbidden, likely blocked
                displayBlockMessage();
                return null;
            }
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || 'Failed to fetch user data.'); });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Blocked or other non-JSON response handled

            loadingDiv.style.display = 'none';
            adminConfirmForm.style.display = 'block';

            emailInput.value = data.email || '';
            fullNameInput.value = data.full_name || '';
            phoneNumberInput.value = data.phone_number || '';

            // Display attempt count if available
            if (data.attempts_left !== undefined) {
                attemptsLeftSpan.textContent = data.attempts_left;
                attemptCountDiv.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            displayError(error.message || 'An unexpected error occurred.');
        });

    // Handle form submission for confirmation
    adminConfirmForm.addEventListener('submit', function(event) {
        event.preventDefault();

        confirmButton.disabled = true;
        confirmButton.textContent = 'Confirming...';

        const payload = {
            token: token,
            full_name: fullNameInput.value,
            phone_number: phoneNumberInput.value
        };

        fetch('/api/v1/users/admin/confirm-login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') // Get CSRF token from cookie
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (response.status === 403) { // Forbidden, likely blocked
                displayBlockMessage();
                return null;
            }
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || 'Login confirmation failed.'); });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Blocked or other non-JSON response handled

            if (data.ok && data.next) {
                window.location.href = data.next; // Redirect to admin dashboard
            } else {
                displayError(data.message || 'Login confirmation failed.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            displayError(error.message || 'An unexpected error occurred during confirmation.');
            confirmButton.disabled = false;
            confirmButton.textContent = 'Confirm Login';
        });
    });

    // Helper function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});