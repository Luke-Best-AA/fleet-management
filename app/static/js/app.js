document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds (pause on hover)
    const alerts = document.querySelectorAll('#flash-messages .alert');
    alerts.forEach(function(alert) {
        var remaining = 5000;
        var start = Date.now();
        var timer = setTimeout(function dismiss() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, remaining);

        alert.addEventListener('mouseenter', function() {
            clearTimeout(timer);
            remaining -= (Date.now() - start);
        });
        alert.addEventListener('mouseleave', function() {
            start = Date.now();
            timer = setTimeout(function() {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, remaining);
        });
    });

    // Theme management
    var browserPref = window.matchMedia('(prefers-color-scheme: dark)');

    function getEffectiveTheme() {
        var stored = localStorage.getItem('theme');
        if (stored) return stored;
        return browserPref.matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        var toggle = document.getElementById('themeToggle');
        if (toggle) toggle.checked = (theme === 'dark');
    }

    // Sync toggle with theme already applied by <head> script
    applyTheme(getEffectiveTheme());

    // Follow browser changes when no manual override
    browserPref.addEventListener('change', function() {
        if (!localStorage.getItem('theme')) applyTheme(getEffectiveTheme());
    });

    // Theme toggle on profile page
    var toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.addEventListener('change', function() {
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
