/**
 * OnlinePharmacy Dashboard — Auth helpers
 * Session check, logout redirect, 401 handling companion.
 */
(function () {
    'use strict';

    var AUTH_REDIRECT = '/auth/';
    var LOGOUT_URL = '/api/v1/users/logout/';
    var SESSION_CHECK_URL = '/api/v1/dashboard/session/';

    /**
     * Redirect unauthenticated users to the auth page.
     */
    function redirectToAuth() {
        if (window.location.pathname !== AUTH_REDIRECT) {
            window.location.replace(AUTH_REDIRECT);
        }
    }

    /**
     * Handle 401 Unauthorized responses globally.
     * @param {Response} response
     * @returns {boolean} true if redirected
     */
    function handleUnauthorized(response) {
        if (response && response.status === 401) {
            redirectToAuth();
            return true;
        }
        return false;
    }

    /**
     * Read CSRF token from cookie or meta tag.
     * @returns {string|null}
     */
    function getCSRFToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.getAttribute('content')) {
            return meta.getAttribute('content');
        }
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    /**
     * Lightweight session check via dashboard API.
     * @returns {Promise<boolean>}
     */
    function checkSession() {
        var headers = { Accept: 'application/json' };
        var csrf = getCSRFToken();
        if (csrf) {
            headers['X-CSRFToken'] = csrf;
        }

        return fetch(SESSION_CHECK_URL, {
            method: 'GET',
            credentials: 'same-origin',
            headers: headers
        })
            .then(function (response) {
                if (handleUnauthorized(response)) {
                    return false;
                }
                return response.ok;
            })
            .catch(function () {
                return false;
            });
    }

    /**
     * Log out via API and redirect to auth page.
     * @returns {Promise<void>}
     */
    function logout() {
        var headers = {
            Accept: 'application/json',
            'Content-Type': 'application/json'
        };
        var csrf = getCSRFToken();
        if (csrf) {
            headers['X-CSRFToken'] = csrf;
        }

        return fetch(LOGOUT_URL, {
            method: 'POST',
            credentials: 'same-origin',
            headers: headers,
            body: JSON.stringify({})
        })
            .finally(function () {
                redirectToAuth();
            });
    }

    /**
     * Bind logout links/buttons with data-logout attribute.
     */
    function bindLogoutHandlers() {
        document.querySelectorAll('[data-logout]').forEach(function (el) {
            el.addEventListener('click', function (event) {
                event.preventDefault();
                logout();
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindLogoutHandlers();
    });

    window.DashboardAuth = {
        AUTH_REDIRECT: AUTH_REDIRECT,
        redirectToAuth: redirectToAuth,
        handleUnauthorized: handleUnauthorized,
        getCSRFToken: getCSRFToken,
        checkSession: checkSession,
        logout: logout
    };
})();
