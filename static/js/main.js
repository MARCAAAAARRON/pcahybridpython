/* PCA Hybridization Portal — Main JS */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add fade-in animation to stat cards
    document.querySelectorAll('.stat-card, .card').forEach((el, i) => {
        el.classList.add('animate-in');
        el.style.animationDelay = `${i * 0.08}s`;
    });
});
