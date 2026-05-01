/**
 * Warns users when navigating away from forms with unsaved changes.
 * Auto-initializes on all forms with the "novalidate" attribute.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var forms = document.querySelectorAll('form[novalidate]');
        forms.forEach(function (form) {
            var initial = new FormData(form);
            var initialMap = {};
            initial.forEach(function (value, key) {
                if (key === 'csrf_token') return;
                initialMap[key] = value;
            });

            var submitting = false;
            form.addEventListener('submit', function () { submitting = true; });

            function isDirty() {
                var current = new FormData(form);
                var dirty = false;
                current.forEach(function (value, key) {
                    if (key === 'csrf_token') return;
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
