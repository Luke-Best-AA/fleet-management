document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    const alerts = document.querySelectorAll('#flash-messages .alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Theme: localStorage preference > browser preference
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        // Keep any toggle switch in sync
        var toggle = document.getElementById('themeToggle');
        if (toggle) toggle.checked = (theme === 'dark');
    }

    var stored = localStorage.getItem('theme');
    if (stored) {
        applyTheme(stored);
    } else {
        var mq = window.matchMedia('(prefers-color-scheme: dark)');
        applyTheme(mq.matches ? 'dark' : 'light');
        mq.addEventListener('change', function(e) {
            if (!localStorage.getItem('theme')) applyTheme(e.matches ? 'dark' : 'light');
        });
    }

    // Theme toggle on profile page
    var toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.addEventListener('change', function() {
            var theme = this.checked ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
            applyTheme(theme);
        });
    }

    // Reset-to-browser button
    var resetBtn = document.getElementById('themeReset');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            localStorage.removeItem('theme');
            var mq = window.matchMedia('(prefers-color-scheme: dark)');
            applyTheme(mq.matches ? 'dark' : 'light');
        });
    }
});
