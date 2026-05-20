/**
 * Warns users when navigating away from forms with unsaved changes.
 * Auto-saves form data to sessionStorage so it can be restored after
 * a login redirect (session expiry).  Data is ONLY restored when the
 * login page sets a _form_restore flag matching the current path.
 * Auto-initializes on all forms with the "novalidate" attribute.
 */
(function () {
    'use strict';

    var SKIP_FIELDS = { csrf_token: 1, next: 1 };
    var STORE_KEY = '_form_data:' + location.pathname;

    function shouldSkip(name, type) {
        return SKIP_FIELDS[name] || type === 'password' || type === 'file';
    }

    document.addEventListener('DOMContentLoaded', function () {
        var forms = document.querySelectorAll('form[novalidate]');
        forms.forEach(function (form) {
            var initial = new FormData(form);
            var initialMap = {};
            initial.forEach(function (value, key) {
                if (SKIP_FIELDS[key]) return;
                initialMap[key] = value;
            });

            var submitting = false;

            // --- Restore saved data only after a login redirect ---
            var restorePath = sessionStorage.getItem('_form_restore');
            if (restorePath === location.pathname) {
                try {
                    var saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || '{}');
                    var fields = form.elements;
                    for (var i = 0; i < fields.length; i++) {
                        var el = fields[i];
                        if (!el.name || shouldSkip(el.name, el.type)) continue;
                        if (saved.hasOwnProperty(el.name)) {
                            el.value = saved[el.name];
                        }
                    }
                } catch (_) { /* corrupt data — ignore */ }
                sessionStorage.removeItem('_form_restore');
                sessionStorage.removeItem(STORE_KEY);
            }

            // --- Auto-save on every change ---
            function saveFields() {
                var data = {};
                var fd = new FormData(form);
                fd.forEach(function (value, key) {
                    if (shouldSkip(key, (form.elements[key] || {}).type)) return;
                    data[key] = value;
                });
                sessionStorage.setItem(STORE_KEY, JSON.stringify(data));
            }

            form.addEventListener('input', saveFields);
            form.addEventListener('change', saveFields);

            // --- Clear saved data on successful submit ---
            form.addEventListener('submit', function () {
                submitting = true;
                sessionStorage.removeItem(STORE_KEY);
            });

            // --- Unsaved-changes warning ---
            function isDirty() {
                var current = new FormData(form);
                var dirty = false;
                current.forEach(function (value, key) {
                    if (SKIP_FIELDS[key]) return;
                    if (initialMap[key] !== value) dirty = true;
                });
                return dirty;
            }

            window.addEventListener('beforeunload', function (e) {
                if (submitting || !isDirty()) return;
                e.preventDefault();
            });
        });
    });
})();
