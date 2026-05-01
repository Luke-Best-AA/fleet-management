document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds (pause while hovering)
    var flashContainer = document.getElementById('flash-messages');
    if (flashContainer) {
        var paused = false;
        flashContainer.addEventListener('mouseenter', function() { paused = true; });
        flashContainer.addEventListener('mouseleave', function() { paused = false; });

        var alerts = flashContainer.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var remaining = 5000;
            var last = Date.now();

            function tick() {
                if (paused) {
                    requestAnimationFrame(tick);
                    return;
                }
                var now = Date.now();
                remaining -= (now - last);
                last = now;
                if (remaining <= 0) {
                    var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                } else {
                    requestAnimationFrame(tick);
                }
            }
            requestAnimationFrame(tick);
        });
    }

    // Theme management
    var browserPref = window.matchMedia('(prefers-color-scheme: dark)');
    var settingToggle = false; // guard against re-entrant change events

    function getEffectiveTheme() {
        var stored = localStorage.getItem('theme');
        if (stored) return stored;
        return browserPref.matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        var toggle = document.getElementById('themeToggle');
        if (toggle) {
            settingToggle = true;
            toggle.checked = (theme === 'dark');
            settingToggle = false;
        }
    }

    // Sync toggle with theme already applied by <head> script
    applyTheme(getEffectiveTheme());

    // Follow browser changes when no manual override
    browserPref.addEventListener('change', function() {
        if (!localStorage.getItem('theme')) {
            applyTheme(getEffectiveTheme());
            updateBrowserInfo();
        }
    });

    // Theme toggle on profile page
    var toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.addEventListener('change', function() {
            if (settingToggle) return;
            var theme = this.checked ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
            applyTheme(theme);
            updateBrowserInfo();
        });
    }

    // Reset-to-browser button
    var resetBtn = document.getElementById('themeReset');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            localStorage.removeItem('theme');
            applyTheme(getEffectiveTheme());
            updateBrowserInfo();
        });
    }

    // Show browser default on profile page
    function updateBrowserInfo() {
        var info = document.getElementById('browserThemeInfo');
        if (info) {
            var stored = localStorage.getItem('theme');
            var browserLabel = browserPref.matches ? 'dark' : 'light';
            if (stored) {
                info.textContent = 'Using manual override (' + stored + '). Browser default is ' + browserLabel + '.';
            } else {
                info.textContent = 'Following browser default (' + browserLabel + ').';
            }
        }
    }
    updateBrowserInfo();
});
