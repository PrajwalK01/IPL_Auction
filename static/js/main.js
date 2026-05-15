// main.js — IPL Auction Frontend Helpers

// Auto-dismiss flash alerts after 4 seconds
document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 4000);
  });

  // Mobile sidebar toggle (attach to navbar toggler in future)
  const sidebar = document.getElementById("sidebar");
  if (sidebar) {
    document.addEventListener("click", (e) => {
      if (window.innerWidth < 992) {
        if (!sidebar.contains(e.target) && !e.target.closest(".navbar-toggler")) {
          sidebar.classList.remove("open");
        }
      }
    });
  }
});
