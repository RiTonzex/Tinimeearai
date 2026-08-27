/**
 * Tinimeearai (ที่นี่มีอะไร) - Client-side Utilities & Enhancements
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-dismiss Toast Messages after 4 seconds
    const toastElements = document.querySelectorAll('.animate-fade-in');
    if (toastElements.length > 0) {
        setTimeout(() => {
            toastElements.forEach(el => {
                el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                el.style.opacity = '0';
                el.style.transform = 'translateY(-10px)';
                setTimeout(() => el.remove(), 500);
            });
        }, 4000);
    }

    // 2. Initialize Lucide icons if available
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }
});
