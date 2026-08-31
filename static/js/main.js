/**
 * Tinimeearai (ที่นี่มีอะไร) - Client-side Utilities & Enhancements
 * Pure Solid Black / Luxury Minimalist Theme
 */

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input && input.value) return input.value;
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

function initCarousels() {
    document.querySelectorAll('.carousel-container').forEach(container => {
        if (container.dataset.carouselInit) return;
        container.dataset.carouselInit = 'true';

        const slidesContainer = container.querySelector('.carousel-slides');
        const slides = container.querySelectorAll('.carousel-slide');
        const prevBtn = container.querySelector('.carousel-btn-prev');
        const nextBtn = container.querySelector('.carousel-btn-next');
        const dots = container.querySelectorAll('.carousel-dot');
        const counter = container.querySelector('.carousel-counter');
        const total = slides.length;

        if (total <= 1 || !slidesContainer) return;

        let currentIndex = 0;

        function updateCarousel(index, animate = true) {
            currentIndex = Math.max(0, Math.min(index, total - 1));
            
            if (slidesContainer) {
                const containerWidth = container.offsetWidth || container.getBoundingClientRect().width;
                if (!animate) {
                    slidesContainer.style.transition = 'none';
                } else {
                    slidesContainer.style.transition = 'transform 0.32s cubic-bezier(0.16, 1, 0.3, 1)';
                }
                slidesContainer.style.transform = `translate3d(-${currentIndex * containerWidth}px, 0, 0)`;
            }

            if (counter) {
                counter.textContent = `${currentIndex + 1}/${total}`;
            }

            dots.forEach((dot, i) => {
                if (i === currentIndex) {
                    dot.className = 'carousel-dot h-1.5 rounded-full transition-all duration-300 w-4 bg-white shadow-sm';
                } else {
                    dot.className = 'carousel-dot h-1.5 rounded-full transition-all duration-300 w-1.5 bg-white/40';
                }
            });

            if (prevBtn) {
                prevBtn.disabled = currentIndex === 0;
                prevBtn.style.opacity = currentIndex === 0 ? '0' : '0.9';
                prevBtn.style.pointerEvents = currentIndex === 0 ? 'none' : 'auto';
            }
            if (nextBtn) {
                nextBtn.disabled = currentIndex === total - 1;
                nextBtn.style.opacity = currentIndex === total - 1 ? '0' : '0.9';
                nextBtn.style.pointerEvents = currentIndex === total - 1 ? 'none' : 'auto';
            }
        }

        updateCarousel(0, false);

        // Recalculate on window resize
        window.addEventListener('resize', () => {
            updateCarousel(currentIndex, false);
        }, { passive: true });

        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                updateCarousel(currentIndex - 1);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                updateCarousel(currentIndex + 1);
            });
        }

        // Touch swipe gestures
        let startX = 0;
        let startY = 0;
        let isTouching = false;

        container.addEventListener('touchstart', (e) => {
            if (e.touches.length !== 1) return;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isTouching = true;
        }, { passive: true });

        container.addEventListener('touchend', (e) => {
            if (!isTouching) return;
            isTouching = false;
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const deltaX = endX - startX;
            const deltaY = endY - startY;

            if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY)) {
                if (deltaX < 0 && currentIndex < total - 1) {
                    updateCarousel(currentIndex + 1);
                } else if (deltaX > 0 && currentIndex > 0) {
                    updateCarousel(currentIndex - 1);
                }
            }
        }, { passive: true });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Carousels
    initCarousels();

    // 2. Auto-dismiss Toast Notification Pill at bottom
    const toastContainer = document.getElementById('system-toast-container');
    if (toastContainer) {
        setTimeout(() => {
            toastContainer.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
            toastContainer.style.opacity = '0';
            toastContainer.style.transform = 'translate(-50%, 12px)';
            setTimeout(() => {
                if (toastContainer && toastContainer.parentNode) {
                    toastContainer.remove();
                }
            }, 350);
        }, 2400);
    }

    // 3. Initialize Lucide icons if available
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }

    // 4. Universal Optimistic Post Like Handler
    document.addEventListener('click', async (e) => {
        const likeBtn = e.target.closest('.btn-like-post');
        if (!likeBtn) return;
        e.preventDefault();
        e.stopPropagation();

        const url = likeBtn.dataset.url;
        if (!url) return;

        const heartIcon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
        const countSpan = likeBtn.querySelector('.post-likes-count');

        const isCurrentlyLiked = heartIcon ? (heartIcon.classList.contains('fill-rose-500') || heartIcon.classList.contains('text-rose-500')) : false;
        let currentCount = countSpan ? (parseInt(countSpan.textContent.replace(/[^0-9]/g, '')) || 0) : 0;

        if (isCurrentlyLiked) {
            if (heartIcon) {
                heartIcon.classList.remove('text-rose-500', 'fill-rose-500');
                heartIcon.classList.add('text-zinc-400');
            }
            if (countSpan) {
                currentCount = Math.max(0, currentCount - 1);
                countSpan.textContent = currentCount;
            }
        } else {
            if (heartIcon) {
                heartIcon.classList.add('text-rose-500', 'fill-rose-500');
                heartIcon.classList.remove('text-zinc-400');
                heartIcon.style.transform = 'scale(1.35)';
                setTimeout(() => { heartIcon.style.transform = 'scale(1)'; }, 180);
            }
            if (countSpan) {
                currentCount = currentCount + 1;
                countSpan.textContent = currentCount;
            }
        }

        const csrfToken = getCsrfToken();
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });
            if (res.ok) {
                const data = await res.json();
                if (countSpan && typeof data.total_likes !== 'undefined') {
                    countSpan.textContent = data.total_likes;
                }
                if (heartIcon && typeof data.liked !== 'undefined') {
                    if (data.liked) {
                        heartIcon.classList.add('text-rose-500', 'fill-rose-500');
                        heartIcon.classList.remove('text-zinc-400');
                    } else {
                        heartIcon.classList.remove('text-rose-500', 'fill-rose-500');
                        heartIcon.classList.add('text-zinc-400');
                    }
                }
            } else {
                console.error('Like request failed with status:', res.status);
            }
        } catch (err) {
            console.error('Like sync error:', err);
        }
    });

    // 5. Smooth Page Navigation Loading Indicator
    let loadingBar = document.getElementById('top-loading-bar');
    if (!loadingBar) {
        loadingBar = document.createElement('div');
        loadingBar.id = 'top-loading-bar';
        document.body.appendChild(loadingBar);
    }

    const mainContent = document.getElementById('app-main-content');

    document.querySelectorAll('a[href]').forEach(link => {
        const href = link.getAttribute('href');
        if (
            href &&
            !href.startsWith('#') &&
            !href.startsWith('javascript:') &&
            !href.startsWith('tel:') &&
            !href.startsWith('mailto:') &&
            !link.target &&
            !link.hasAttribute('download')
        ) {
            link.addEventListener('click', (e) => {
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                
                const currentUrl = window.location.pathname + window.location.search;
                if (href === currentUrl) return;

                loadingBar.style.width = '35%';
                loadingBar.style.opacity = '1';
                setTimeout(() => {
                    if (loadingBar.style.opacity !== '0') {
                        loadingBar.style.width = '75%';
                    }
                }, 100);

                if (mainContent) {
                    mainContent.classList.remove('page-transition-enter', 'swipe-exit-left', 'swipe-exit-right');
                    mainContent.classList.add('page-transition-exit');
                }
            });
        }
    });

    // 6. Pull-to-Refresh Gesture for Mobile
    initPullToRefresh();

    window.addEventListener('pageshow', () => {
        if (mainContent) {
            mainContent.classList.remove('page-transition-exit', 'swipe-exit-left', 'swipe-exit-right');
            mainContent.classList.add('page-transition-enter');
        }
        if (loadingBar) {
            loadingBar.style.width = '100%';
            setTimeout(() => {
                loadingBar.style.opacity = '0';
                setTimeout(() => { loadingBar.style.width = '0%'; }, 300);
            }, 150);
        }
        initCarousels();
    });
});

/**
 * Modern 60fps Pull-to-Refresh Gesture
 */
function initPullToRefresh() {
    let startY = 0;
    let currentY = 0;
    let isPulling = false;
    let isRefreshing = false;
    const threshold = 65;

    let ptr = document.getElementById('pull-to-refresh-indicator');
    if (!ptr) {
        ptr = document.createElement('div');
        ptr.id = 'pull-to-refresh-indicator';
        ptr.className = 'fixed top-3 left-1/2 -translate-x-1/2 z-50 flex items-center justify-center w-10 h-10 rounded-full bg-zinc-900/95 border border-zinc-700/80 text-white shadow-2xl backdrop-blur-xl pointer-events-none transition-all duration-200 opacity-0 -translate-y-12';
        ptr.innerHTML = `
            <svg id="ptr-icon" class="w-5 h-5 text-white transition-transform duration-150" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
                <path d="M21 3v5h-5"/>
            </svg>
        `;
        document.body.appendChild(ptr);
    }

    const icon = ptr.querySelector('#ptr-icon');

    window.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0 && e.touches.length === 1 && !isRefreshing) {
            startY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
        if (!isPulling || isRefreshing || window.scrollY > 0) return;
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;

        if (diff > 0) {
            const pullDistance = Math.min(diff * 0.45, 90);
            const progress = Math.min(pullDistance / threshold, 1);
            
            ptr.style.opacity = progress.toString();
            ptr.style.transform = `translate(-50%, ${pullDistance - 10}px) scale(${0.75 + progress * 0.25})`;
            if (icon) {
                icon.style.transform = `rotate(${progress * 360}deg)`;
            }
        }
    }, { passive: true });

    window.addEventListener('touchend', () => {
        if (!isPulling || isRefreshing) return;
        isPulling = false;
        const diff = currentY - startY;
        const pullDistance = Math.min(diff * 0.45, 90);

        if (pullDistance >= threshold && window.scrollY === 0) {
            isRefreshing = true;
            ptr.style.transform = `translate(-50%, ${threshold - 10}px) scale(1)`;
            ptr.style.opacity = '1';
            if (icon) {
                icon.classList.add('animate-spin');
            }
            
            if (navigator.vibrate) {
                navigator.vibrate(15);
            }

            setTimeout(() => {
                window.location.reload();
            }, 400);
        } else {
            ptr.style.transition = 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)';
            ptr.style.opacity = '0';
            ptr.style.transform = 'translate(-50%, -48px) scale(0.7)';
            setTimeout(() => {
                ptr.style.transition = '';
            }, 250);
        }
    }, { passive: true });
}

window.initPullToRefresh = initPullToRefresh;

window.initCarousels = initCarousels;

/**
 * Universal Map Tile Provider based on user preference
 * Defaults to Carto Dark Matter
 */
window.getMapTileLayer = function() {
    const style = localStorage.getItem('map_style') || 'dark';
    if (style === 'satellite') {
        return L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri',
            maxZoom: 18
        });
    } else if (style === 'standard') {
        return L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap &copy; Contributors',
            maxZoom: 19
        });
    } else {
        return L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            className: 'dark-map-tiles',
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
        });
    }
};
