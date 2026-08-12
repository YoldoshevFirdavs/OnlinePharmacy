(function(){
    'use strict';

    function getCSRFToken(){
        var meta = document.querySelector('meta[name="csrf-token"]');
        if(meta && meta.getAttribute('content')) return meta.getAttribute('content');
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function getAuthToken(){
        try{ return localStorage.getItem('access_token') || localStorage.getItem('auth_token') || null; }catch(e){ return null; }
    }

    function getRefreshToken(){
        try{ return localStorage.getItem('refresh_token') || null; }catch(e){ return null; }
    }

    async function refreshToken() {
        const refresh = getRefreshToken();
        if (!refresh) {
            return null;
        }
        try {
            const res = await fetch('/api/v1/users/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ refresh: refresh })
            });
            if (!res.ok) {
                return null;
            }
            const data = await res.json();
            if (data.access) {
                localStorage.setItem('access_token', data.access);
                return data.access;
            }
            return null;
        } catch (e) {
            return null;
        }
    }

    function safeText(s){ return (s||'').toString(); }

    function updateTopbarUser(user){
        try{
            var avatarImg = document.querySelector('.topbar-avatar');
            var usernameSpan = document.querySelector('.topbar-username');
            var brandName = document.getElementById('dashboardBrandName');
            var brandSticker = document.getElementById('dashboardBrandSticker');

            var displayName = safeText(user.full_name || user.email || user.username || 'User');
            
            if(usernameSpan){ usernameSpan.textContent = displayName; }
            if(avatarImg){
                var avatar = user.avatar_url || (user.avatar && user.avatar.url) || avatarImg.getAttribute('src');
                if(avatar) avatarImg.src = avatar;
                avatarImg.alt = displayName;
            }
            if(brandName && user.dashboard_name) brandName.textContent = user.dashboard_name;
            if(brandSticker && user.dashboard_sticker) brandSticker.textContent = user.dashboard_sticker;
        }catch(e){ /* silent */ }
    }

    async function fetchCurrentUser(isRetry) {
        isRetry = isRetry || false;
        var headers = { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
        var token = getAuthToken();
        if (token) headers['Authorization'] = 'Bearer ' + token;
        var csrf = getCSRFToken();
        if (csrf) headers['X-CSRFToken'] = csrf;

        try {
            var res = await fetch('/api/v1/users/me/', { method: 'GET', credentials: 'include', headers: headers });
            // 401 on dashboard = JWT token missing/expired, but Django session is valid.
            // Do NOT redirect — dashboard uses session auth, not JWT.
            if (res.status === 401) {
                if (!isRetry) {
                    var newToken = await refreshToken();
                    if (newToken) return await fetchCurrentUser(true);
                }
                // Silent fail — dashboard session auth handles access control
                return null;
            }
            if (!res.ok) return null;
            var data = await res.json();
            window.__CURRENT_USER = data;
            updateTopbarUser(data);
            return data;
        } catch (e) {
            return null;
        }
    }

    function applySavedTheme(){
        try{
            var saved = localStorage.getItem('dashboard-theme') || localStorage.getItem('dashboard_theme');
            var theme = saved || 'light';
            if(saved === 'auto'){
                theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
            document.documentElement.setAttribute('data-theme', theme);
            var toggleBtn = document.getElementById('themeToggle');
            if(toggleBtn) toggleBtn.setAttribute('aria-pressed', String(theme === 'dark'));
            var icon = document.getElementById('themeIcon');
            if(icon) icon.textContent = theme === 'dark' ? '🌙' : '🌞';
        }catch(e){}
    }

    function initThemeToggle(){
        var btn = document.getElementById('themeToggle');
        if(!btn) return;
        btn.addEventListener('click', function(){
            var current = document.documentElement.getAttribute('data-theme') || 'light';
            var next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            btn.setAttribute('aria-pressed', String(next === 'dark'));
            var icon = document.getElementById('themeIcon');
            if(icon) icon.textContent = next === 'dark' ? '🌙' : '🌞';
            try{ localStorage.setItem('dashboard-theme', next); }catch(e){}
        });
    }

    function initBrandSettings(){
        var savedBrand = localStorage.getItem('dashboard-brand-name') || localStorage.getItem('dashboard_brand_name');
        var savedSticker = localStorage.getItem('dashboard-brand-sticker') || localStorage.getItem('dashboard_brand_sticker');

        // Sidebar brand elements (new structure: text + sticker spans)
        var sidebarBrandText = document.querySelector('#sidebarBrand .sidebar-brand-text');
        var sidebarBrandSticker = document.querySelector('#sidebarBrand .sidebar-brand-sticker');

        var liveName = document.getElementById('livePreviewName');
        var liveSticker = document.getElementById('livePreviewSticker');
        var inputBrand = document.getElementById('inputBrandName');

        if (savedBrand) {
            if (sidebarBrandText) sidebarBrandText.textContent = savedBrand;
            if (liveName) liveName.textContent = savedBrand;
            if (inputBrand) inputBrand.value = savedBrand;
        }
        if (savedSticker) {
            if (sidebarBrandSticker) sidebarBrandSticker.textContent = savedSticker;
            if (liveSticker) liveSticker.textContent = savedSticker;
            // Mark active sticker button
            document.querySelectorAll('.sticker-btn').forEach(function(b) {
                b.classList.toggle('sticker-btn--active', b.dataset.sticker === savedSticker);
            });
        }
    }

    function syncHeaderHeight() {
        const header = document.querySelector('header.navbar') || document.getElementById('dashboardTopbar') || document.querySelector('header.dashboard-topbar');
        if (!header) return;

        const setHeaderHeight = () => {
            const h = header.offsetHeight || 80; // Fallback to 80px
            document.documentElement.style.setProperty('--header-height', h + 'px');
        };

        setHeaderHeight();
        window.addEventListener('resize', setHeaderHeight);
        window.addEventListener('scroll', () => {
            header.classList.toggle('is-scrolled', window.scrollY > 10);
        });
    }

    function initGlobalSearch(){
        var searchInput = document.getElementById('globalSearch');
        if (!searchInput) return;

        var timeout = null;
        searchInput.addEventListener('input', function () {
            clearTimeout(timeout);
            var query = searchInput.value.toLowerCase().trim();

            timeout = setTimeout(function () {
                var tableRows = document.querySelectorAll('.data-table tbody tr');
                tableRows.forEach(function (row) {
                    if (row.classList.contains('data-table__empty')) return;
                    var text = row.textContent.toLowerCase();
                    row.style.display = text.indexOf(query) !== -1 ? '' : 'none';
                });
            }, 200);
        });
    }

    document.addEventListener('DOMContentLoaded', function(){
        applySavedTheme();
        initThemeToggle();
        initBrandSettings();
        initGlobalSearch();
        syncHeaderHeight();
        // Ensure meta csrf exists for other scripts (theme.js, etc.)
        if(!document.querySelector('meta[name="csrf-token"]')){
            var meta = document.createElement('meta');
            meta.name = 'csrf-token';
            meta.content = getCSRFToken() || '';
            document.head.appendChild(meta);
        }
        fetchCurrentUser().catch(function(){});
    });

    window.DashboardAuth = {
        fetchCurrentUser: fetchCurrentUser,
        getAuthToken: getAuthToken
    };

})();