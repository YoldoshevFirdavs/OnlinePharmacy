/**
 * OnlinePharmacy Dashboard — Users page module
 * Fetches users list and manages userbar navigation.
 */
(function () {
    'use strict';

    function getApi() {
        return window.Dashboard || {};
    }

    function getTargetContainer() {
        return document.getElementById('usersList') ||
            document.querySelector('#dataTable tbody');
    }

    function roleTag(user, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var label = 'Foydalanuvchi';
        var cls = 'info';

        if (user.is_superuser) {
            label = 'Superadmin';
            cls = 'warning';
        } else if (user.is_staff) {
            label = 'Admin';
            cls = 'primary';
        }

        return '<span class="tag tag--' + cls + '"><i class="fa-solid fa-user-shield"></i> ' + escapeHtml(label) + '</span>';
    }

    function activeTag(isActive, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        if (isActive) {
            return '<span class="tag tag--success"><i class="fa-solid fa-circle-check"></i> Faol</span>';
        }
        return '<span class="tag tag--error"><i class="fa-solid fa-circle-xmark"></i> Nofaol</span>';
    }

    function renderEmptyRow(colspan) {
        return '<tr class="data-table__empty">' +
            '<td colspan="' + colspan + '">' +
            '<i class="fa-solid fa-inbox"></i>' +
            '<span>Foydalanuvchilar topilmadi</span>' +
            '</td></tr>';
    }

    function renderUserRow(user, api) {
        var escapeHtml = api.escapeHtml || function (s) { return s; };
        var formatDate = api.formatDate || function (v) { return v || '—'; };
        var fullName = user.full_name || user.get_full_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || '—';
        var editUrl = user.edit_url || ('/dashboard/users/' + user.id + '/edit/');

        return '<tr data-user-id="' + escapeHtml(String(user.id)) + '">' +
            '<td>' + escapeHtml(String(user.id)) + '</td>' +
            '<td><div class="user-cell"><i class="fa-solid fa-circle-user"></i> ' + escapeHtml(user.username) + '</div></td>' +
            '<td>' + escapeHtml(fullName) + '</td>' +
            '<td>' + escapeHtml(user.email || '—') + '</td>' +
            '<td>' + roleTag(user, api) + '</td>' +
            '<td>' + activeTag(user.is_active !== false, api) + '</td>' +
            '<td>' + escapeHtml(formatDate(user.date_joined)) + '</td>' +
            '<td><div class="table-actions">' +
            '<a href="' + escapeHtml(editUrl) + '" class="btn btn--sm btn--ghost" title="Tahrirlash">' +
            '<i class="fa-solid fa-pen"></i></a></div></td></tr>';
    }

    function initUserbarNavigation() {
        var userbar = document.getElementById('userbar');
        var toggle = document.getElementById('userbarToggle');
        var links = document.getElementById('userbarLinks');

        if (toggle && links) {
            toggle.addEventListener('click', function () {
                links.classList.toggle('userbar-links--open');
                userbar && userbar.classList.toggle('userbar--open');
            });
        }

        document.addEventListener('click', function (event) {
            if (!userbar || !links || !links.classList.contains('userbar-links--open')) {
                return;
            }
            if (!userbar.contains(event.target)) {
                links.classList.remove('userbar-links--open');
                userbar.classList.remove('userbar--open');
            }
        });

        var currentPath = window.location.pathname;
        document.querySelectorAll('#userbarLinks .userbar-link').forEach(function (link) {
            var href = link.getAttribute('href');
            if (href && currentPath.indexOf(href.replace(/\/$/, '')) === 0 && href !== '/') {
                link.classList.add('userbar-link--active');
            }
        });
    }

    function updateTableCount(count) {
        var countEl = document.getElementById('tableCount');
        if (countEl) {
            countEl.textContent = count + ' ta foydalanuvchi';
        }
    }

    function loadUsers() {
        var container = getTargetContainer();
        if (!container) {
            return;
        }

        var api = getApi();
        var fetchFn = api.fetchUsers || (api.apiFetch && function () {
            return api.apiFetch('users/').then(api.extractList);
        });

        if (!fetchFn) {
            return;
        }

        fetchFn()
            .then(function (users) {
                if (!users.length) {
                    container.innerHTML = renderEmptyRow(8);
                    updateTableCount(0);
                    return;
                }

                container.innerHTML = users.map(function (user) {
                    return renderUserRow(user, api);
                }).join('');

                updateTableCount(users.length);
            })
            .catch(function () {
                /* Keep SSR-rendered rows on API failure */
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initUserbarNavigation();

        if (getTargetContainer()) {
            loadUsers();
        }
    });
})();
