// templates/delivery/header.js

// =============================================================================
// Header Configuration
// =============================================================================

// Check if HEADER_CONFIG is already declared to prevent duplicate declaration errors
if (typeof HEADER_CONFIG === 'undefined') {
    window.HEADER_CONFIG = {
        LOGIN_STATUS_ELEMENT_ID: 'header-login-status',
        QUICK_LINKS_CONTAINER_ID: 'header-quick-links',
        COUNTRY_SELECTOR_HEADER_ID: 'header-country-selector',
        AUTH_PAGE_URL: '/auth/',
        DASHBOARD_URL: '/dashboard/',
        LOGOUT_URL: '/api/v1/users/logout/',
        I18N: {
            en: {
                login: "Login",
                logout: "Logout",
                dashboard: "Dashboard",
                welcome: "Welcome, ",
                profile: "Profile",
                settings: "Settings",
            },
            uz: {
                login: "Kirish",
                logout: "Chiqish",
                dashboard: "Dashboard",
                welcome: "Xush kelibsiz, ",
                profile: "Profil",
                settings: "Sozlamalar",
            }
        },
        DEFAULT_LANG: 'uz',
    };
}

let headerCurrentLang = HEADER_CONFIG.DEFAULT_LANG;

function _h(key) {
    return HEADER_CONFIG.I18N[headerCurrentLang][key] || HEADER_CONFIG.I18N[HEADER_CONFIG.DEFAULT_LANG][key] || key;
}

// =============================================================================
// Helper Functions
// =============================================================================

function getHeaderCookie(name) {
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

function sendHeaderLogoutRequest(url) {
    const csrftoken = getHeaderCookie('csrftoken');
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    });
}

// =============================================================================
// Login Status & DOM Binding
// =============================================================================

function updateLoginStatus(isLoggedIn, username = null) {
    const loginStatusElement = document.getElementById(HEADER_CONFIG.LOGIN_STATUS_ELEMENT_ID);
    
    // Safely update templates/components/header.html structure as well if the main target elements don't exist
    const headerLoginBtn = document.getElementById('header-login-btn');
    const headerUserBlock = document.getElementById('header-user-block');
    const headerUserName = document.getElementById('header-user-name');
    const logoutForm = document.getElementById('logout-form-header');

    if (isLoggedIn) {
        if (headerLoginBtn) headerLoginBtn.style.display = 'none';
        if (headerUserBlock) headerUserBlock.style.display = 'inline-block';
        if (headerUserName && username) headerUserName.textContent = username;
        if (logoutForm) logoutForm.style.display = 'block';
    } else {
        if (headerLoginBtn) headerLoginBtn.style.display = 'inline-block';
        if (headerUserBlock) headerUserBlock.style.display = 'none';
        if (logoutForm) logoutForm.style.display = 'none';
    }

    if (!loginStatusElement) {
        // Safe fallback: Log to console rather than breaking execution
        console.log(`[Header] Custom status element '${HEADER_CONFIG.LOGIN_STATUS_ELEMENT_ID}' not found, falling back to standard template buttons.`);
        return;
    }

    loginStatusElement.innerHTML = '';

    if (isLoggedIn) {
        const welcomeText = document.createElement('span');
        welcomeText.textContent = _h('welcome') + (username || 'Admin') + '! ';
        loginStatusElement.appendChild(welcomeText);

        const dashboardLink = document.createElement('a');
        dashboardLink.href = HEADER_CONFIG.DASHBOARD_URL;
        dashboardLink.textContent = _h('dashboard');
        dashboardLink.className = 'btn btn-link';
        loginStatusElement.appendChild(dashboardLink);

        const logoutButton = document.createElement('button');
        logoutButton.textContent = _h('logout');
        logoutButton.className = 'btn btn-outline-secondary btn-sm ms-2';
        logoutButton.addEventListener('click', handleHeaderLogout);
        loginStatusElement.appendChild(logoutButton);
    } else {
        const loginLink = document.createElement('a');
        loginLink.href = HEADER_CONFIG.AUTH_PAGE_URL;
        loginLink.textContent = _h('login');
        loginLink.className = 'btn btn-primary btn-sm';
        loginStatusElement.appendChild(loginLink);
    }
}

async function handleHeaderLogout(e) {
    if (e) e.preventDefault();
    try {
        await sendHeaderLogoutRequest(HEADER_CONFIG.LOGOUT_URL);
        updateLoginStatus(false);
        localStorage.removeItem('access_token');
        window.location.reload();
    } catch (error) {
        console.error("Logout error:", error);
        alert("Logout qilishda xato yuz berdi.");
    }
}

// =============================================================================
// Quick Links Setup
// =============================================================================

function setupQuickLinks() {
    const quickLinksContainer = document.getElementById(HEADER_CONFIG.QUICK_LINKS_CONTAINER_ID);
    if (!quickLinksContainer) {
        console.log(`[Header] Container '${HEADER_CONFIG.QUICK_LINKS_CONTAINER_ID}' not found.`);
        return;
    }

    quickLinksContainer.innerHTML = '';
    const links = [
        { text: _h('profile'), url: '/account/' },
        { text: _h('settings'), url: '/dashboard/' },
    ];

    links.forEach(linkData => {
        const link = document.createElement('a');
        link.href = linkData.url;
        link.textContent = linkData.text;
        link.className = 'dropdown-item';
        quickLinksContainer.appendChild(link);
    });
}

// =============================================================================
// Country Selector
// =============================================================================

function setupHeaderCountrySelector() {
    const headerCountrySelector = document.getElementById(HEADER_CONFIG.COUNTRY_SELECTOR_HEADER_ID);
    if (!headerCountrySelector) {
        console.log(`[Header] Selector '${HEADER_CONFIG.COUNTRY_SELECTOR_HEADER_ID}' not found.`);
        return;
    }

    headerCountrySelector.innerHTML = '';
    
    if (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.PHONE_PATTERNS) {
        for (const countryCode in AUTH_CONFIG.PHONE_PATTERNS) {
            const option = document.createElement('option');
            option.value = countryCode;
            option.textContent = `${countryCode.toUpperCase()} (${AUTH_CONFIG.PHONE_PATTERNS[countryCode].prefixes[0]})`;
            headerCountrySelector.appendChild(option);
        }
        headerCountrySelector.value = AUTH_CONFIG.DEFAULT_LANG;
    } else {
        const defaultOption = document.createElement('option');
        defaultOption.value = 'uz';
        defaultOption.textContent = 'UZ (+998)';
        headerCountrySelector.appendChild(defaultOption);
    }

    headerCountrySelector.addEventListener('change', (event) => {
        headerCurrentLang = event.target.value;
        if (typeof AUTH_CONFIG !== 'undefined') {
            AUTH_CONFIG.DEFAULT_LANG = headerCurrentLang;
        }
        console.log("Til o'zgardi:", headerCurrentLang);
    });
}

// =============================================================================
// Init Header
// =============================================================================

function initHeader() {
    if (typeof window.searchAnalyzer === 'undefined') {
        window.searchAnalyzer = {
            analyze: function() { return null; },
            init: function() { return true; }
        };
    }

    const accessToken = localStorage.getItem('access_token');
    const isLoggedIn = !!accessToken;

    updateLoginStatus(isLoggedIn, "Admin");
    setupQuickLinks();
    setupHeaderCountrySelector();

    // Bind templates/components/header.html logout form submit event
    const logoutForm = document.getElementById('logout-form-header');
    if (logoutForm) {
        logoutForm.addEventListener('submit', handleHeaderLogout);
    }
}

document.addEventListener('DOMContentLoaded', initHeader);
