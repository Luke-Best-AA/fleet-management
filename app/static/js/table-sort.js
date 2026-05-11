/**
 * Client-side table sorting.
 * Auto-initializes on tables with class "table-sortable".
 * Columns with class "no-sort" are excluded from sorting.
 */
(function () {
    'use strict';

    function parseValue(cell) {
        var text = cell.textContent.trim();
        // Strip currency symbols, commas
        var num = text.replace(/[£$,]/g, '');
        if (num !== '' && !isNaN(num)) return parseFloat(num);
        // Date: try parsing "01 Jan 2024" or ISO
        var d = Date.parse(text);
        if (!isNaN(d)) return d;
        return text.toLowerCase();
    }

    function sortTable(table, colIndex, ascending) {
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.from(tbody.querySelectorAll('tr'));

        rows.sort(function (a, b) {
            var cellA = a.cells[colIndex];
            var cellB = b.cells[colIndex];
            if (!cellA || !cellB) return 0;
            var valA = parseValue(cellA);
            var valB = parseValue(cellB);
            if (valA < valB) return ascending ? -1 : 1;
            if (valA > valB) return ascending ? 1 : -1;
            return 0;
        });

        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    function initTable(table) {
        var headers = table.querySelectorAll('thead th');
        headers.forEach(function (th, index) {
            if (th.classList.contains('no-sort') || th.textContent.trim() === '') return;
            th.classList.add('sortable-header');
            th.setAttribute('role', 'button');
            th.setAttribute('aria-sort', 'none');
            th.addEventListener('click', function () {
                var currentDir = th.getAttribute('aria-sort');
                // Reset all
                headers.forEach(function (h) {
                    h.setAttribute('aria-sort', 'none');
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                var ascending = currentDir !== 'ascending';
                th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
                th.classList.add(ascending ? 'sort-asc' : 'sort-desc');
                sortTable(table, index, ascending);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('table.table-sortable').forEach(initTable);
    });
})();
