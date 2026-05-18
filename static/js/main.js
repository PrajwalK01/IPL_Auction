/* main.js — Global JavaScript helpers (v2) */

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss flash alerts after 4 seconds
    setTimeout(function () {
        let alerts = document.querySelectorAll('.alert:not(.alert-important)');
        alerts.forEach(function (alert) {
            let bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 4000);

    // Sidebar toggle (mobile)
    document.addEventListener('click', function(e) {
        const sidebar = document.querySelector('.dashboard-sidebar');
        const toggler = document.querySelector('.navbar-toggler');
        
        if (sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && (!toggler || !toggler.contains(e.target))) {
                sidebar.classList.remove('open');
            }
        }
    });
});

// App Config Caching (Session Storage)
async function getCachedConfig() {
    let cached = sessionStorage.getItem('ipl_app_config');
    if (cached) {
        return JSON.parse(cached);
    }
    return null; // The server will render config directly in templates, this is just for future API usage if needed.
}
