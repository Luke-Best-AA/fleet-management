/**
 * Client-side table filtering.
 * Supports: text search, select filters, range filters (min/max).
 *
 * Usage: Add data-filter-target="tableId" to a container with filter inputs.
 *   - Text search: <input data-filter="search">
 *   - Select: <select data-filter="select" data-col="3">
 *   - Range: <input data-filter="min" data-col="4"> / <input data-filter="max" data-col="4">
 *   - Date range: <input type="date" data-filter="date-min" data-col="2"> / <input type="date" data-filter="date-max" data-col="2">
 */
(function () {
    'use strict';

    function getCellText(row, col) {
        var cell = row.cells[col];
        return cell ? cell.textContent.trim() : '';
    }

    function getCellNumeric(row, col) {
        var text = getCellText(row, col).replace(/[£$,\s]/g, '');
        var num = parseFloat(text);
        return isNaN(num) ? null : num;
    }

    function getCellDate(row, col) {
        var text = getCellText(row, col);
        var d = Date.parse(text);
        return isNaN(d) ? null : d;
    }

    function applyFilters(container) {
        var tableId = container.getAttribute('data-filter-target');
        var table = document.getElementById(tableId);
        if (!table) return;
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.from(tbody.querySelectorAll('tr'));

        // Gather filter values
        var searchInput = container.querySelector('[data-filter="search"]');
        var searchTerm = searchInput ? searchInput.value.toLowerCase() : '';

        var selects = Array.from(container.querySelectorAll('[data-filter="select"]'));
        var mins = Array.from(container.querySelectorAll('[data-filter="min"]'));
        var maxs = Array.from(container.querySelectorAll('[data-filter="max"]'));
        var dateMins = Array.from(container.querySelectorAll('[data-filter="date-min"]'));
        var dateMaxs = Array.from(container.querySelectorAll('[data-filter="date-max"]'));

        var visibleCount = 0;

        rows.forEach(function (row) {
            // Skip "no results" placeholder rows
            if (row.querySelector('[colspan]')) {
                row.style.display = '';
                return;
            }

            var visible = true;

            // Text search: match any cell
            if (searchTerm) {
                var rowText = row.textContent.toLowerCase();
                visible = rowText.indexOf(searchTerm) !== -1;
            }

            // Select filters
            if (visible) {
                selects.forEach(function (sel) {
                    if (!visible) return;
                    var col = parseInt(sel.getAttribute('data-col'), 10);
                    var val = sel.value;
                    if (val === '') return;
                    var cellText = getCellText(row, col).toLowerCase();
                    visible = cellText.indexOf(val.toLowerCase()) !== -1;
                });
            }

            // Numeric range filters
            if (visible) {
                mins.forEach(function (input) {
                    if (!visible) return;
                    var col = parseInt(input.getAttribute('data-col'), 10);
                    var minVal = parseFloat(input.value);
                    if (isNaN(minVal)) return;
                    var cellVal = getCellNumeric(row, col);
                    if (cellVal === null || cellVal < minVal) visible = false;
                });
                maxs.forEach(function (input) {
                    if (!visible) return;
                    var col = parseInt(input.getAttribute('data-col'), 10);
                    var maxVal = parseFloat(input.value);
                    if (isNaN(maxVal)) return;
                    var cellVal = getCellNumeric(row, col);
                    if (cellVal === null || cellVal > maxVal) visible = false;
                });
            }

            // Date range filters
            if (visible) {
                dateMins.forEach(function (input) {
                    if (!visible) return;
                    var col = parseInt(input.getAttribute('data-col'), 10);
                    var minDate = Date.parse(input.value);
                    if (isNaN(minDate)) return;
                    var cellDate = getCellDate(row, col);
                    if (cellDate === null || cellDate < minDate) visible = false;
                });
                dateMaxs.forEach(function (input) {
                    if (!visible) return;
                    var col = parseInt(input.getAttribute('data-col'), 10);
                    var maxDate = Date.parse(input.value);
                    if (isNaN(maxDate)) return;
                    var cellDate = getCellDate(row, col);
                    if (cellDate === null || cellDate > maxDate) visible = false;
                });
            }

            row.style.display = visible ? '' : 'none';
            if (visible) visibleCount++;
        });

        // Show/hide "no results" row
        var noResults = tbody.querySelector('.no-filter-results');
        if (visibleCount === 0) {
            if (!noResults) {
                noResults = document.createElement('tr');
                noResults.className = 'no-filter-results';
                var td = document.createElement('td');
                td.setAttribute('colspan', '100');
                td.className = 'text-muted text-center py-3';
                td.textContent = 'No matching records found';
                noResults.appendChild(td);
                tbody.appendChild(noResults);
            }
            noResults.style.display = '';
        } else if (noResults) {
            noResults.style.display = 'none';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var containers = document.querySelectorAll('[data-filter-target]');
        containers.forEach(function (container) {
            var tableId = container.getAttribute('data-filter-target');
            var table = document.getElementById(tableId);

            // Auto-populate select filters from table column values
            if (table) {
                var autoSelects = container.querySelectorAll('[data-auto-populate]');
                autoSelects.forEach(function (sel) {
                    var col = parseInt(sel.getAttribute('data-col'), 10);
                    var tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    var values = new Set();
                    Array.from(tbody.querySelectorAll('tr')).forEach(function (row) {
                        var cell = row.cells[col];
                        if (cell && !cell.querySelector('[colspan]')) {
                            var text = cell.textContent.trim();
                            if (text && text !== '-') values.add(text);
                        }
                    });
                    Array.from(values).sort().forEach(function (val) {
                        var opt = document.createElement('option');
                        opt.value = val;
                        opt.textContent = val;
                        sel.appendChild(opt);
                    });
                });
            }

            var inputs = container.querySelectorAll('input, select');
            inputs.forEach(function (input) {
                input.addEventListener('input', function () { applyFilters(container); });
                input.addEventListener('change', function () { applyFilters(container); });
            });

            // Pre-fill filters from URL query params (e.g. ?status=active)
            var params = new URLSearchParams(window.location.search);
            var hasParams = false;
            params.forEach(function (value, key) {
                // Try to find a select with matching options
                var selects = container.querySelectorAll('select[data-filter="select"]');
                selects.forEach(function (sel) {
                    Array.from(sel.options).forEach(function (opt) {
                        if (opt.value.toLowerCase() === value.toLowerCase()) {
                            sel.value = opt.value;
                            hasParams = true;
                        }
                    });
                });
                // Try to find a text search input
                if (key === 'q' || key === 'search') {
                    var searchInput = container.querySelector('[data-filter="search"]');
                    if (searchInput) { searchInput.value = value; hasParams = true; }
                }
            });

            // Apply data-default values when no URL params override them
            if (!hasParams) {
                var defaultSelects = container.querySelectorAll('select[data-default]');
                defaultSelects.forEach(function (sel) {
                    var def = sel.getAttribute('data-default');
                    Array.from(sel.options).forEach(function (opt) {
                        if (opt.value.toLowerCase() === def.toLowerCase()) {
                            sel.value = opt.value;
                            hasParams = true;
                        }
                    });
                });
            }

            if (hasParams) applyFilters(container);

            // Clear filters button
            var clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'btn btn-sm btn-outline-secondary';
            clearBtn.innerHTML = '<i class="bi bi-x-lg me-1"></i>Clear';
            clearBtn.style.display = 'none';
            clearBtn.addEventListener('click', function () {
                container.querySelectorAll('input').forEach(function (i) { i.value = ''; });
                container.querySelectorAll('select').forEach(function (s) { s.selectedIndex = 0; });
                clearBtn.style.display = 'none';
                applyFilters(container);
            });

            // Insert clear button
            var filterRow = container.querySelector('.row');
            if (filterRow) {
                var clearCol = document.createElement('div');
                clearCol.className = 'col-auto';
                clearCol.appendChild(clearBtn);
                filterRow.appendChild(clearCol);
            }

            // Show/hide clear button based on filter state
            function updateClearBtn() {
                var hasValue = false;
                container.querySelectorAll('input').forEach(function (i) { if (i.value) hasValue = true; });
                container.querySelectorAll('select').forEach(function (s) { if (s.selectedIndex > 0) hasValue = true; });
                clearBtn.style.display = hasValue ? '' : 'none';
            }
            inputs.forEach(function (input) {
                input.addEventListener('input', updateClearBtn);
                input.addEventListener('change', updateClearBtn);
            });
            updateClearBtn();

            // Mobile: wrap filter row in a collapsible accordion
            filterRow = container.querySelector('.row');
            if (filterRow) {
                var collapseId = 'filterCollapse-' + tableId;

                // Create toggle button (visible only on small screens)
                var btn = document.createElement('button');
                btn.className = 'btn btn-sm btn-outline-secondary d-md-none w-100';
                btn.type = 'button';
                btn.setAttribute('data-bs-toggle', 'collapse');
                btn.setAttribute('data-bs-target', '#' + collapseId);
                btn.setAttribute('aria-expanded', 'false');
                btn.innerHTML = '<i class="bi bi-funnel me-1"></i>Filters';

                // Wrap the row in a collapse div
                var collapseDiv = document.createElement('div');
                collapseDiv.id = collapseId;
                collapseDiv.className = 'collapse d-md-block mt-2';
                filterRow.parentNode.insertBefore(btn, filterRow);
                filterRow.parentNode.insertBefore(collapseDiv, filterRow);
                collapseDiv.appendChild(filterRow);
            }
        });
    });
})();
