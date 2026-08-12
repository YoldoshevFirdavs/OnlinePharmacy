/**
 * OnlinePharmacy Dashboard — Search Analyzer JS
 * Provides search input filters and search analysis guards.
 */
(function () {
    'use strict';

    function initSearchAnalyzer() {
        var searchInput = document.getElementById('globalSearch') || document.getElementById('tableSearch');
        if (!searchInput) {
            // Guard against null search element
            return;
        }

        searchInput.addEventListener('input', function () {
            var query = (searchInput.value || '').trim().toLowerCase();
            if (!query) return;

            var rows = document.querySelectorAll('table tbody tr');
            rows.forEach(function (row) {
                if (row.classList.contains('data-table__empty')) return;
                var text = (row.textContent || '').toLowerCase();
                if (text.indexOf(query) !== -1) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initSearchAnalyzer();
    });

    window.SearchAnalyzer = {
        initSearchAnalyzer: initSearchAnalyzer
    };
})();
