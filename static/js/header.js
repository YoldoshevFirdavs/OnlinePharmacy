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
    const authKeys = [
        'access_token', 'refresh_token', 'username', 'avatar_url', 'user_role',
        'user_email', 'user_id', 'currentSessionId', 'currentIdentifier',
        'currentAuthMethod', 'showOtpPopup'
    ];
    authKeys.forEach(key => localStorage.removeItem(key));
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('auth_block_') || key.startsWith('field_bf_')) {
            localStorage.removeItem(key);
        }
    });
    sessionStorage.clear();
    updateHeaderUI(false);
    const profileElements = document.querySelectorAll(
        '#header-username-display, #header-user-email, .account-user-name, .account-user-email'
    );
    profileElements.forEach(element => { element.textContent = ''; });
    const avatar = document.getElementById('header-user-avatar');
    if (avatar) avatar.src = HEADER_CONFIG.DEFAULT_AVATAR;
    window.location.replace(HEADER_CONFIG.AUTH_PAGE_URL);
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
    const accountDropdownButton = document.getElementById('account-dropdown-button');
    const accountDropdownMenu = document.getElementById('account-dropdown-menu');

    if (!accountDropdownButton || !accountDropdownMenu) return;

    accountDropdownButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isOpen = accountDropdownMenu.classList.contains('show');
        if (isOpen) {
            accountDropdownMenu.classList.remove('show');
            accountDropdownButton.classList.remove('active');
        } else {
            accountDropdownMenu.classList.add('show');
            accountDropdownButton.classList.add('active');
        }
    });

    document.addEventListener('click', (e) => {
        if (!accountDropdownButton.contains(e.target) && !accountDropdownMenu.contains(e.target)) {
            accountDropdownMenu.classList.remove('show');
            accountDropdownButton.classList.remove('active');
        }
    });
}

function updateHeaderUI(isLoggedIn, username, avatarUrl, email, userRole, shouldShowDropdown = true) {
    const authLinks = document.getElementById('auth-links');
    const accountDropdownContainer = document.getElementById('account-dropdown-container');
    const accountDropdownButton = document.getElementById('account-dropdown-button');
    const headerUserAvatar = document.getElementById('header-user-avatar');
    const headerUserName = document.getElementById('header-username-display');

    if (isLoggedIn) {
        if (authLinks) authLinks.style.display = 'none';
        
        if (shouldShowDropdown) {
            // Show dropdown container for admin, seller, user
            if (accountDropdownContainer) accountDropdownContainer.style.display = 'block';
            if (headerUserAvatar) headerUserAvatar.src = avatarUrl || HEADER_CONFIG.DEFAULT_AVATAR;
            if (headerUserName) headerUserName.textContent = username || '';
            
            // Update dropdown links based on user role
            const adminLink = document.querySelector('.admin-link');
            const delivererLink = document.querySelector('.deliverer-link');
            const userLinks = document.querySelectorAll('.user-link');

            if (adminLink) adminLink.style.display = (userRole === 'admin') ? 'list-item' : 'none';
            if (delivererLink) delivererLink.style.display = (userRole === 'deliverer') ? 'list-item' : 'none';
            userLinks.forEach(link => link.style.display = (userRole === 'user' || !userRole) ? 'list-item' : 'none');

            const logoutButton = document.getElementById('logout-button');
            if (logoutButton) {
                logoutButton.removeEventListener('click', handleHeaderLogout);
                logoutButton.addEventListener('click', handleHeaderLogout);
            }
            setupDropdownToggle();
        } else {
            // Deliverer: hide dropdown, show only avatar and name
            if (accountDropdownContainer) accountDropdownContainer.style.display = 'none';
            if (headerUserAvatar) headerUserAvatar.src = avatarUrl || HEADER_CONFIG.DEFAULT_AVATAR;
            if (headerUserName) headerUserName.textContent = username || '';
        }
    } else {
        if (authLinks) authLinks.style.display = 'block';
        if (accountDropdownContainer) accountDropdownContainer.style.display = 'none';
    }
}

async function handleHeaderLogout(e) {
    if (e) e.preventDefault();
    try {
        await sendRequest(HEADER_CONFIG.LOGOUT_URL, 'POST', {
            csrfmiddlewaretoken: getCookie('csrftoken'),
        });
        await sendRequest('/api/v1/users/logout/jwt/', 'POST');
    } catch (err) {
        console.warn('[Header] Logout xato:', err);
    } finally {
        clearAuthStorage(); // NOTE: Call clearAuthStorage for full logout process
    }
}

async function initHeader() {
    const user = await fetchUserProfile();

    if (user) {
        // Get full_name, username, or email - NOT role!
        const username = user.full_name || user.username || user.email || localStorage.getItem('username');
        const avatarUrl = user.avatar || user.avatar_url || HEADER_CONFIG.DEFAULT_AVATAR;
        const email = user.email || localStorage.getItem('user_email');
        const userRole = user.role || localStorage.getItem('user_role');

        localStorage.setItem('username', username || '');
        localStorage.setItem('avatar_url', avatarUrl);
        localStorage.setItem('user_email', email || '');
        if (user.role) {
            localStorage.setItem('user_role', user.role);
        }

        // Show dropdown only if role is admin, seller, or user
        // Deliverer users (no role or role !== 'admin' && role !== 'seller' && role !== 'user') get avatar+name only
        const shouldShowDropdown = userRole === 'admin' || userRole === 'seller' || userRole === 'user';
        
        updateHeaderUI(true, username, avatarUrl, email, userRole, shouldShowDropdown);
    } else {
        updateHeaderUI(false);
    }
}

document.addEventListener('DOMContentLoaded', initHeader);
