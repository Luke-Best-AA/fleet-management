document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    const alerts = document.querySelectorAll('#flash-messages .alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Dark mode: follow browser preference
    function applyTheme(dark) {
        document.documentElement.setAttribute('data-bs-theme', dark ? 'dark' : 'light');
    }
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    applyTheme(mq.matches);
    mq.addEventListener('change', function(e) { applyTheme(e.matches); });
});
