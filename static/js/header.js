// Inlined getCookie function from utils.js
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Inlined sendRequest function from utils.js
function sendRequest(url, method, data = null) {
    const csrftoken = getCookie('csrftoken');
    const token = localStorage.getItem('access_token');
    const headers = {
        'Accept': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (method !== 'GET') {
        headers['Content-Type'] = 'application/json';
        if (csrftoken) headers['X-CSRFToken'] = csrftoken;
    }

    const config = {
        method: method,
        headers: headers,
        credentials: 'include' // Include cookies for session auth
    };

    if (data) {
        config.body = JSON.stringify(data);
    }

    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                return response.json().catch(() => {
                    throw new Error(`HTTP error! Status: ${response.status} - ${response.statusText}`);
                }).then(err => {
                    throw err;
                });
            }
            return response.json();
        });
}


const HEADER_CONFIG = {
    AUTH_PAGE_URL: '/auth/',
    ADMIN_DASHBOARD_URL: '/dashboard/admin/',
    DELIVERER_DASHBOARD_URL: '/dashboard/delivery/',
    USER_ACCOUNT_URL: '/account/',
    LOGOUT_URL: '/api/v1/users/logout/',
    PROFILE_URL: '/api/v1/users/me/',
    DEFAULT_AVATAR: '/static/images/default_avatar.png',
    I18N: {
        en: { login: 'Login', logout: 'Logout', account: 'Account' },
        uz: { login: 'Kirish', logout: 'Chiqish', account: 'Kabinet' },
    },
    DEFAULT_LANG: 'uz',
};

function _h(key) {
    const lang = localStorage.getItem('user_lang') || HEADER_CONFIG.DEFAULT_LANG;
    return HEADER_CONFIG.I18N[lang][key] || HEADER_CONFIG.I18N[HEADER_CONFIG.DEFAULT_LANG][key] || key;
}

// NOTE: Function to clear authentication related data from storage
function clearAuthStorage() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    localStorage.removeItem('avatar_url');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_email');
    localStorage.removeItem('currentSessionId');
    localStorage.removeItem('currentIdentifier');
    localStorage.removeItem('showOtpPopup');
    sessionStorage.clear(); // NOTE: Clear session storage as well
    window.location.href = HEADER_CONFIG.AUTH_PAGE_URL; // NOTE: Redirect to login page
}

function getAuthHeaders() {
    const headers = { Accept: 'application/json' };
    const token = localStorage.getItem('access_token');
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }
    const csrf = getCookie('csrftoken');
    if (csrf) {
        headers['X-CSRFToken'] = csrf;
    }
    return headers;
}

async function fetchUserProfile() {
    const token = localStorage.getItem('access_token');
    const hasSession = Boolean(getCookie('sessionid'));
    if (!token && !hasSession) {
        updateHeaderUI(false); // NOTE: Update UI if no token or session
        return null;
    }

    try {
        const response = await fetch(HEADER_CONFIG.PROFILE_URL, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'include', // Include cookies for session auth
        });

        // NOTE: Handle 401/403 responses
        if (response.status === 401 || response.status === 403) {
            const errorData = await response.json().catch(() => ({}));
            // Only clear + redirect if JWT token is explicitly invalid AND we have a token stored
            const storedToken = localStorage.getItem('access_token');
            if (storedToken && errorData.code === 'token_not_valid') {
                console.warn('[Header] Token invalid. Clearing auth storage and redirecting.');
                clearAuthStorage();
                updateHeaderUI(false);
                return null;
            }
            // No token or session-based auth — silent fail, do NOT redirect
            console.warn(`[Header] Auth check returned ${response.status} — silent fail (session auth).`);
            updateHeaderUI(false);
            return null;
        }

        if (!response.ok) {
            throw new Error(`Failed to fetch user profile: ${response.status} ${response.statusText}`);
        }

        return response.json();
    } catch (err) {
        console.error('[Header] Error fetching user profile:', err);
        updateHeaderUI(false); // NOTE: Revert UI on any fetch error
        return null;
    }
}

function setupDropdownToggle() {
    const accountDropdownButton = document.getElementById('account-dropdown-button'); // NOTE: Use specific ID for button
    const accountDropdownMenu = document.getElementById('account-dropdown-menu'); // NOTE: Use specific ID for menu

    if (accountDropdownButton && accountDropdownMenu) {
        accountDropdownButton.addEventListener('click', (e) => {
            e.preventDefault();
            accountDropdownMenu.classList.toggle('show');
            accountDropdownButton.classList.toggle('active'); // NOTE: Add active class for styling
        });

        document.addEventListener('click', (e) => {
            if (!accountDropdownButton.contains(e.target) && !accountDropdownMenu.contains(e.target)) {
                accountDropdownMenu.classList.remove('show');
                accountDropdownButton.classList.remove('active');
            }
        });
    }
}

function updateHeaderUI(isLoggedIn, username, avatarUrl, email, userRole) { // NOTE: Added userRole parameter
    const authLinks = document.getElementById('auth-links'); // NOTE: New ID for login/signup links container
    const accountDropdownContainer = document.getElementById('account-dropdown-container'); // NOTE: New ID for account dropdown container

    if (isLoggedIn) {
        if (authLinks) authLinks.style.display = 'none';
        if (accountDropdownContainer) accountDropdownContainer.style.display = 'block'; // NOTE: Show dropdown container

        const headerUserAvatar = document.querySelector('#account-dropdown-button .avatar'); // NOTE: Target avatar inside button
        const headerUserName = document.getElementById('username-display'); // NOTE: Target username display

        if (headerUserAvatar) headerUserAvatar.src = avatarUrl || HEADER_CONFIG.DEFAULT_AVATAR;
        if (headerUserName) headerUserName.textContent = username || '';

        // NOTE: Update dropdown links based on user role
        const adminLink = document.querySelector('.admin-link');
        const delivererLink = document.querySelector('.deliverer-link');
        const userLinks = document.querySelectorAll('.user-link');

        if (adminLink) adminLink.style.display = (userRole === 'admin') ? 'list-item' : 'none';
        if (delivererLink) delivererLink.style.display = (userRole === 'deliverer') ? 'list-item' : 'none';
        userLinks.forEach(link => link.style.display = (userRole === 'user' || !userRole) ? 'list-item' : 'none'); // Default to user if no specific role

        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.removeEventListener('click', handleHeaderLogout); // Prevent multiple listeners
            logoutButton.addEventListener('click', handleHeaderLogout);
        }
        setupDropdownToggle(); // Setup dropdown toggle after elements are visible
    } else {
        if (authLinks) authLinks.style.display = 'block';
        if (accountDropdownContainer) accountDropdownContainer.style.display = 'none'; // NOTE: Hide dropdown container
    }
}

async function handleHeaderLogout(e) {
    if (e) e.preventDefault();
    try {
        await sendRequest(HEADER_CONFIG.LOGOUT_URL, 'POST', {
            csrfmiddlewaretoken: getCookie('csrftoken'),
        });
    } catch (err) {
        console.warn('[Header] Logout xato:', err);
    } finally {
        clearAuthStorage(); // NOTE: Call clearAuthStorage for full logout process
    }
}

async function initHeader() {
    const user = await fetchUserProfile();

    if (user) {
        const username = user.full_name || localStorage.getItem('username');
        const avatarUrl = user.avatar || user.avatar_url || HEADER_CONFIG.DEFAULT_AVATAR;
        const email = user.email || localStorage.getItem('user_email');
        const userRole = user.role || localStorage.getItem('user_role'); // NOTE: Get user role

        localStorage.setItem('username', username || '');
        localStorage.setItem('avatar_url', avatarUrl);
        localStorage.setItem('user_email', email || '');
        if (user.role) {
            localStorage.setItem('user_role', user.role);
        }

        updateHeaderUI(true, username, avatarUrl, email, userRole); // NOTE: Pass userRole to updateHeaderUI

        // NOTE: Old admin/deliverer link logic removed as it's now handled in updateHeaderUI
    } else {
        updateHeaderUI(false);
    }
}

document.addEventListener('DOMContentLoaded', initHeader);

// COMPATIBILITY APPEND START
(function startSessionChecker() {
    const CHECK_URL = '/api/v1/users/login/check-session/';
    const INTERVAL_MS = 300000; // 5 minutes
    let checkInterval = null;
    let consecutiveNetworkErrors = 0;
    function getAuthToken() {
        try {
            return localStorage.getItem('access_token');
        } catch (e) {
            console.warn('Could not access localStorage to get auth token.');
            return null;
        }
    }
    async function checkSessionOnce() {
        const token = getAuthToken();
        // Only run the check if a token exists. If no token, the user is already logged out.
        if (!token) {
            if (checkInterval) clearInterval(checkInterval);
            return;
        }
        try {
            const res = await fetch(CHECK_URL, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` },
                credentials: 'include' // Include cookies for session auth
            });
            consecutiveNetworkErrors = 0; // Reset on successful connection
            if (res.status === 200) {
                const data = await res.json().catch(() => null);
                if (data && data.ok) {
                    // Session is valid, do nothing.
                    return;
                }
            }
            // Any non-200 or ok:false response means the session is invalid
            console.warn("Session expired or invalid. Logging out.");
            // Use the existing clearAuthStorage function which handles cleanup and redirect.
            if (typeof clearAuthStorage === 'function') {
                clearAuthStorage();
            } else {
                // Fallback if clearAuthStorage is not available
                localStorage.clear();
                sessionStorage.clear();
                window.location.href = '/auth/';
            }
        } catch (err) {
            consecutiveNetworkErrors++;
            console.warn(`Session check network error (${consecutiveNetworkErrors}).`);
            // Stop polling after 5 consecutive network errors to avoid spamming a down server.
            if (consecutiveNetworkErrors >= 5) {
                console.error("Session check failed 5 consecutive times due to network errors. Pausing checks.");
                if (checkInterval) {
                    clearInterval(checkInterval);
                    checkInterval = null;
                }
            }
        }
    }
    // Start the checker
    if (!checkInterval) {
        checkInterval = setInterval(checkSessionOnce, INTERVAL_MS);
    }
    // Ensure it's cleared on page unload to prevent memory leaks in single-page apps
    window.addEventListener('beforeunload', () => { if (checkInterval) clearInterval(checkInterval); });
})();