/**
 * Tinimeearai (ที่นี่มีอะไร) - Client-side Utilities & Enhancements
 * Pure Solid Black / Luxury Minimalist Theme
 */

function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content.length > 5) return meta.content;
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match && match[1]) return decodeURIComponent(match[1]);
    return '';
}

function initCarousels() {
    document.querySelectorAll('.carousel-container').forEach(container => {
        const slidesContainer = container.querySelector('.carousel-slides');
        const slides = container.querySelectorAll('.carousel-slide');
        const prevBtn = container.querySelector('.carousel-btn-prev');
        const nextBtn = container.querySelector('.carousel-btn-next');
        const dots = container.querySelectorAll('.carousel-dot');
        const counter = container.querySelector('.carousel-counter');
        const total = slides.length;

        if (total <= 1 || !slidesContainer) {
            if (prevBtn) prevBtn.style.display = 'none';
            if (nextBtn) nextBtn.style.display = 'none';
            return;
        }

        let currentIndex = parseInt(container.dataset.currentIndex || '0', 10) || 0;

        function updateCarousel(index, animate = true) {
            currentIndex = Math.max(0, Math.min(index, total - 1));
            container.dataset.currentIndex = currentIndex;

            if (slidesContainer) {
                if (!animate) {
                    slidesContainer.style.transition = 'none';
                } else {
                    slidesContainer.style.transition = 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)';
                }
                slidesContainer.style.transform = `translateX(-${currentIndex * 100}%)`;
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

        container._updateCarousel = updateCarousel;
        container._slidePrev = () => updateCarousel(currentIndex - 1);
        container._slideNext = () => updateCarousel(currentIndex + 1);

        if (!container.dataset.carouselInit) {
            container.dataset.carouselInit = 'true';

            // Touch swipe gesture support
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
                if (!isTouching || e.changedTouches.length !== 1) return;
                isTouching = false;
                const diffX = e.changedTouches[0].clientX - startX;
                const diffY = e.changedTouches[0].clientY - startY;

                if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 25) {
                    if (diffX < 0 && currentIndex < total - 1) {
                        updateCarousel(currentIndex + 1);
                    } else if (diffX > 0 && currentIndex > 0) {
                        updateCarousel(currentIndex - 1);
                    }
                }
            }, { passive: true });
        }

        updateCarousel(currentIndex, false);
    });
}
window.initCarousels = initCarousels;

// Global Carousel Button Click Delegation (single source of truth)
document.addEventListener('click', (e) => {
    const prevBtn = e.target.closest('.carousel-btn-prev');
    if (prevBtn) {
        e.preventDefault();
        e.stopPropagation();
        const container = prevBtn.closest('.carousel-container');
        if (container && typeof container._slidePrev === 'function') {
            container._slidePrev();
        }
        return;
    }

    const nextBtn = e.target.closest('.carousel-btn-next');
    if (nextBtn) {
        e.preventDefault();
        e.stopPropagation();
        const container = nextBtn.closest('.carousel-container');
        if (container && typeof container._slideNext === 'function') {
            container._slideNext();
        }
        return;
    }
});

// Universal Optimistic Post Like Handler
document.addEventListener('click', async (e) => {
    const likeBtn = e.target.closest('.btn-like-post');
    if (!likeBtn) return;
    e.preventDefault();
    e.stopPropagation();

    const url = likeBtn.dataset.url;
    if (!url) return;

    if (likeBtn.dataset.busy === 'true') return;
    likeBtn.dataset.busy = 'true';

    const heartIcon = likeBtn.querySelector('svg, i');
    const countSpan = likeBtn.querySelector('.post-likes-count');

    function checkIsLiked() {
        if (!heartIcon) return false;
        return heartIcon.classList.contains('fill-rose-500') ||
               heartIcon.classList.contains('text-rose-500') ||
               heartIcon.getAttribute('fill') === '#f43f5e' ||
               heartIcon.style.fill === '#f43f5e';
    }

    function setHeartState(isLiked) {
        if (!heartIcon) return;
        if (isLiked) {
            heartIcon.classList.add('text-rose-500', 'fill-rose-500');
            heartIcon.classList.remove('text-zinc-400', 'text-zinc-300');
            heartIcon.style.color = '#f43f5e';
            heartIcon.style.fill = '#f43f5e';
            heartIcon.style.stroke = '#f43f5e';
        } else {
            heartIcon.classList.remove('text-rose-500', 'fill-rose-500');
            heartIcon.classList.add('text-zinc-400');
            heartIcon.style.color = '';
            heartIcon.style.fill = 'none';
            heartIcon.style.stroke = 'currentColor';
        }
    }

    const isCurrentlyLiked = checkIsLiked();
    let currentCount = countSpan ? (parseInt(countSpan.textContent.replace(/[^0-9]/g, '')) || 0) : 0;
    const nextLikedState = !isCurrentlyLiked;

    // Instant optimistic visual toggle
    setHeartState(nextLikedState);
    if (nextLikedState && heartIcon) {
        heartIcon.style.transform = 'scale(1.35)';
        setTimeout(() => { heartIcon.style.transform = 'scale(1)'; }, 180);
    }
    if (countSpan) {
        countSpan.textContent = nextLikedState ? currentCount + 1 : Math.max(0, currentCount - 1);
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

        if (res.status === 401) {
            const data = await res.json().catch(() => ({}));
            if (typeof showSystemToast === 'function') {
                showSystemToast(data.message || 'กรุณาเข้าสู่ระบบก่อนกดถูกใจ', 'error');
            }
            setTimeout(() => {
                window.location.href = data.redirect || '/login/';
            }, 400);
            return;
        }

        if (res.ok) {
            const data = await res.json();
            if (countSpan && typeof data.total_likes !== 'undefined') {
                countSpan.textContent = data.total_likes;
            }
            if (typeof data.liked !== 'undefined') {
                setHeartState(data.liked);
            }
        } else {
            console.error('Like request failed with status:', res.status);
            setHeartState(isCurrentlyLiked);
            if (countSpan) countSpan.textContent = currentCount;
        }
    } catch (err) {
        console.error('Like sync error:', err);
        setHeartState(isCurrentlyLiked);
        if (countSpan) countSpan.textContent = currentCount;
    } finally {
        likeBtn.dataset.busy = 'false';
    }
});

function onDomReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

onDomReady(() => {
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

    // 7. Tag Friends & Co-Travelers Component
    initUserTagPickers();

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
        initUserTagPickers();
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
    const threshold = 70;
    
    let ptr = document.getElementById('pull-to-refresh-indicator');
    if (!ptr) {
        ptr = document.createElement('div');
        ptr.id = 'pull-to-refresh-indicator';
        ptr.className = 'fixed top-3 left-1/2 -translate-x-1/2 z-50 pointer-events-none opacity-0 transition-opacity duration-200';
        ptr.innerHTML = `
            <div class="px-3.5 py-2 rounded-full bg-zinc-900/90 border border-zinc-700/80 backdrop-blur-md text-white text-xs font-semibold shadow-2xl flex items-center gap-2">
                <i data-lucide="rotate-cw" class="w-3.5 h-3.5 text-zinc-300"></i>
                <span class="ptr-text">ดึงเพื่อรีเฟรช</span>
            </div>
        `;
        document.body.appendChild(ptr);
        if (window.lucide) lucide.createIcons();
    }

    const icon = ptr.querySelector('i[data-lucide="rotate-cw"]');

    window.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0 && e.touches.length === 1) {
            startY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
        if (!isPulling || isRefreshing) return;
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;

        if (diff > 0 && window.scrollY === 0) {
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

/**
 * Saved Collections & Optimistic Bookmark Handler
 */
function showSystemToast(message, type = 'success') {
    let container = document.getElementById('system-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'system-toast-container';
        container.className = 'fixed bottom-24 sm:bottom-8 left-1/2 -translate-x-1/2 z-50 pointer-events-none flex flex-col items-center gap-2 max-w-sm px-4';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const isError = type === 'error';
    toast.className = `app-toast-alert pointer-events-auto px-4 py-2.5 rounded-full text-xs font-semibold shadow-2xl backdrop-blur-xl border flex items-center gap-2 transition-all duration-300 ${
        isError ? 'bg-zinc-950/95 border-rose-500/40 text-rose-200 shadow-rose-950/50' : 'bg-zinc-950/95 border-white/20 text-white shadow-black/80'
    }`;
    
    toast.innerHTML = `
        <i data-lucide="${isError ? 'alert-circle' : 'check-circle-2'}" class="w-4 h-4 shrink-0 ${isError ? 'text-rose-400' : 'text-amber-400'}"></i>
        <span class="truncate max-w-[260px]">${message}</span>
    `;
    container.appendChild(toast);
    if (window.lucide) lucide.createIcons();

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}
window.showSystemToast = showSystemToast;

function updateBookmarkIconState(button, isBookmarked) {
    button.dataset.bookmarked = isBookmarked ? 'true' : 'false';
    const icon = button.querySelector('i[data-lucide="bookmark"]') || button.querySelector('svg');
    if (icon) {
        if (isBookmarked) {
            icon.classList.remove('text-white');
            icon.classList.add('text-amber-400', 'fill-amber-400');
            icon.setAttribute('fill', '#fbbf24');
            icon.setAttribute('stroke', '#fbbf24');
            icon.style.fill = '#fbbf24';
            icon.style.stroke = '#fbbf24';
        } else {
            icon.classList.remove('text-amber-400', 'fill-amber-400');
            icon.classList.add('text-white');
            icon.setAttribute('fill', 'none');
            icon.setAttribute('stroke', 'currentColor');
            icon.style.fill = 'none';
            icon.style.stroke = 'currentColor';
        }
    }
}

let activeBookmarkPostId = null;

function initBookmarkButtons() {
    document.querySelectorAll('.btn-bookmark-ribbon').forEach(btn => {
        // Sync icon state on load if bookmarked
        if (btn.dataset.bookmarked === 'true') {
            updateBookmarkIconState(btn, true);
        }

        if (btn.dataset.bookmarkInit) return;
        btn.dataset.bookmarkInit = 'true';

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const postId = this.dataset.postId;
            openBookmarkModal(postId);
        });
    });
}
window.initPullToRefresh = initPullToRefresh;
window.initBookmarkButtons = initBookmarkButtons;
window.initCarousels = initCarousels;

/**
 * Interactive @username Co-Travelers Tag Picker & Autocomplete Handler
 */
function initUserTagPickers() {
    const box = document.getElementById('tag-friends-box');
    if (!box || box.dataset.tagPickerInit) return;
    box.dataset.tagPickerInit = 'true';

    const input = document.getElementById('tag-user-input');
    const dropdown = document.getElementById('user-autocomplete-dropdown');
    const chipsContainer = document.getElementById('tagged-users-chips');
    const hiddenContainer = document.getElementById('tagged-user-inputs-hidden');
    const countBadge = document.getElementById('tagged-users-count');

    if (!input || !dropdown || !chipsContainer || !hiddenContainer) return;

    let selectedUsers = new Map(); // id -> { id, username, display_name, avatar_url }
    let debounceTimer = null;

    function updateChipsDisplay() {
        chipsContainer.innerHTML = '';
        hiddenContainer.innerHTML = '';

        const count = selectedUsers.size;
        if (countBadge) {
            countBadge.textContent = `${count}/10 คน`;
            if (count >= 10) {
                countBadge.classList.add('text-amber-400');
            } else {
                countBadge.classList.remove('text-amber-400');
            }
        }

        selectedUsers.forEach((user, id) => {
            const chip = document.createElement('div');
            chip.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-semibold text-white shadow-sm';

            const avatarHtml = user.avatar_url
                ? `<img src="${user.avatar_url}" class="w-4 h-4 rounded-full object-cover">`
                : `<div class="w-4 h-4 rounded-full bg-zinc-800 text-[9px] font-bold flex items-center justify-center text-amber-400">${(user.username || 'U')[0].toUpperCase()}</div>`;

            chip.innerHTML = `
                ${avatarHtml}
                <span class="text-amber-400">@${user.username}</span>
                <button type="button" class="text-zinc-500 hover:text-white transition font-bold text-xs ml-0.5" data-remove-id="${id}">&times;</button>
            `;

            chip.querySelector('button').addEventListener('click', (e) => {
                e.preventDefault();
                selectedUsers.delete(id);
                updateChipsDisplay();
            });

            chipsContainer.appendChild(chip);

            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = 'tagged_user_ids';
            hidden.value = id;
            hiddenContainer.appendChild(hidden);
        });
    }

    // Preload initial hidden inputs (from edit_post)
    hiddenContainer.querySelectorAll('input[data-user-id]').forEach(inputEl => {
        const id = parseInt(inputEl.dataset.userId);
        const username = inputEl.dataset.username || inputEl.value;
        if (id) {
            selectedUsers.set(id, { id, username, display_name: username, avatar_url: null });
        }
    });
    updateChipsDisplay();

    async function performSearch() {
        const query = input.value.trim();
        try {
            const res = await fetch(`/api/users/search/?q=${encodeURIComponent(query)}`);
            const data = await res.json();

            if (data.status === 'ok' && data.users && data.users.length > 0) {
                dropdown.innerHTML = '';
                let addedCount = 0;
                data.users.forEach(u => {
                    if (selectedUsers.has(u.id)) return;
                    addedCount++;

                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'w-full flex items-center justify-between p-2 rounded-xl hover:bg-zinc-900 transition text-left text-xs';

                    const avatarHtml = u.avatar_url
                        ? `<img src="${u.avatar_url}" class="w-6 h-6 rounded-lg object-cover bg-zinc-800">`
                        : `<div class="w-6 h-6 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-xs font-bold text-amber-400">${u.username[0].toUpperCase()}</div>`;

                    item.innerHTML = `
                        <div class="flex items-center gap-2 min-w-0">
                            ${avatarHtml}
                            <div class="min-w-0">
                                <span class="block font-bold text-white truncate">${u.display_name}</span>
                                <span class="block text-[10px] text-amber-400 font-mono">@${u.username}</span>
                            </div>
                        </div>
                        ${u.is_followed ? '<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">กำลังติดตาม</span>' : ''}
                    `;

                    item.addEventListener('click', (e) => {
                        e.preventDefault();
                        if (selectedUsers.size >= 10) {
                            if (typeof showSystemToast === 'function') {
                                showSystemToast('แท็กผู้ร่วมทริปได้สูงสุด 10 คนเท่านั้น', 'error');
                            }
                            return;
                        }
                        selectedUsers.set(u.id, u);
                        updateChipsDisplay();
                        input.value = '';
                        dropdown.classList.add('hidden');
                    });

                    dropdown.appendChild(item);
                });

                if (addedCount > 0) {
                    dropdown.classList.remove('hidden');
                } else {
                    dropdown.innerHTML = '<div class="p-3 text-center text-xs text-zinc-500 font-mono">เลือกผู้ใช้ครบถ้วนแล้ว</div>';
                    dropdown.classList.remove('hidden');
                }
            } else {
                dropdown.innerHTML = '<div class="p-3 text-center text-xs text-zinc-500 font-mono">ไม่พบผู้ใช้ที่ตรงกัน</div>';
                dropdown.classList.remove('hidden');
            }
        } catch (err) {
            console.error(err);
        }
    }

    input.addEventListener('focus', function () {
        performSearch();
    });

    input.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            performSearch();
        }, 200);
    });

    document.addEventListener('click', (e) => {
        if (!box.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}
window.initUserTagPickers = initUserTagPickers;

/**
 * Universal Map Tile Provider based on user preference
 * Defaults to Carto Dark Matter
 */
window.getMapTileLayer = function () {
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
window.initBookmarkButtons = initBookmarkButtons;

async function openBookmarkModal(postId) {
    activeBookmarkPostId = postId;
    const modal = document.getElementById('global-bookmark-modal');
    const container = document.getElementById('bookmark-collections-list');
    if (!modal || !container) return;

    // Reset inline form state
    const inlineForm = document.getElementById('inline-create-collection-form');
    const inlineArrow = document.getElementById('inline-create-arrow');
    if (inlineForm) inlineForm.classList.add('hidden');
    if (inlineArrow) inlineArrow.style.transform = 'rotate(0deg)';

    modal.classList.remove('hidden');
    container.innerHTML = '<div class="text-center py-4 text-xs text-zinc-500 font-mono">กำลังโหลดคอลเลกชัน...</div>';

    try {
        const response = await fetch(`/api/collections/?post_id=${postId}`);
        const data = await response.json();

        if (data.status === 'ok') {
            let html = `
                <label class="flex items-center justify-between p-3 rounded-2xl bg-zinc-900/90 border border-zinc-800 hover:border-zinc-700 cursor-pointer transition">
                    <div class="flex items-center gap-2.5">
                        <i data-lucide="bookmark" class="w-4 h-4 text-amber-400"></i>
                        <span class="text-xs font-bold text-white">บันทึกทั่วไป</span>
                    </div>
                    <input type="checkbox" ${data.is_general_saved ? 'checked' : ''} onchange="toggleBookmarkCollection(${postId}, null, this)" class="w-4 h-4 rounded border-zinc-700 text-amber-400 focus:ring-0 bg-zinc-950">
                </label>
            `;

            if (data.collections && data.collections.length > 0) {
                data.collections.forEach(col => {
                    html += `
                        <label class="flex items-center justify-between p-3 rounded-2xl bg-zinc-900/90 border border-zinc-800 hover:border-zinc-700 cursor-pointer transition">
                            <div class="flex items-center gap-2.5">
                                <i data-lucide="folder" class="w-4 h-4 text-zinc-300"></i>
                                <div class="space-y-0.5">
                                    <span class="text-xs font-bold text-white block">${col.title}</span>
                                    <span class="text-[10px] text-zinc-400 font-mono block">${col.posts_count} โพสต์ในทริปนี้</span>
                                </div>
                            </div>
                            <input type="checkbox" ${col.is_saved ? 'checked' : ''} onchange="toggleBookmarkCollection(${postId}, ${col.id}, this)" class="w-4 h-4 rounded border-zinc-700 text-amber-400 focus:ring-0 bg-zinc-950">
                        </label>
                    `;
                });
            } else {
                html += `
                    <div class="p-3 text-center rounded-2xl bg-zinc-900/50 border border-dashed border-zinc-800 text-xs text-zinc-400">
                        ยังไม่มีคอลเลกชันทริป คุณสามารถกดสร้างใหม่ได้ด้านล่าง
                    </div>
                `;
            }
            container.innerHTML = html;
            if (window.lucide) lucide.createIcons();
        }
    } catch (err) {
        console.error('Error fetching collections:', err);
        container.innerHTML = '<div class="text-center py-4 text-xs text-rose-400">ไม่สามารถโหลดคอลเลกชันได้</div>';
    }
}
window.openBookmarkModal = openBookmarkModal;

function closeBookmarkModal() {
    const modal = document.getElementById('global-bookmark-modal');
    if (modal) modal.classList.add('hidden');
    activeBookmarkPostId = null;
}
window.closeBookmarkModal = closeBookmarkModal;

function toggleModalInlineCreateForm() {
    const form = document.getElementById('inline-create-collection-form');
    const arrow = document.getElementById('inline-create-arrow');
    if (form) {
        form.classList.toggle('hidden');
        if (!form.classList.contains('hidden')) {
            document.getElementById('inline-col-title').focus();
            if (arrow) arrow.style.transform = 'rotate(180deg)';
        } else {
            if (arrow) arrow.style.transform = 'rotate(0deg)';
        }
    }
}
window.toggleModalInlineCreateForm = toggleModalInlineCreateForm;

async function toggleBookmarkCollection(postId, collectionId, checkbox) {
    try {
        const response = await fetch('/api/bookmarks/toggle/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ post_id: postId, collection_id: collectionId })
        });
        const data = await response.json();
        if (data.status === 'ok') {
            showSystemToast(data.bookmarked ? 'บันทึกเข้าคอลเลกชันเรียบร้อย' : 'เอาออกจากคอลเลกชันแล้ว', 'success');
            // Update all ribbon buttons on page for this post
            document.querySelectorAll(`.btn-bookmark-ribbon[data-post-id="${postId}"]`).forEach(btn => {
                updateBookmarkIconState(btn, data.is_bookmarked_any);
            });
        } else {
            checkbox.checked = !checkbox.checked;
            showSystemToast(data.message || 'ไม่สามารถบันทึกได้', 'error');
        }
    } catch (err) {
        checkbox.checked = !checkbox.checked;
        showSystemToast('เกิดข้อผิดพลาดในการเชื่อมต่อ', 'error');
    }
}
window.toggleBookmarkCollection = toggleBookmarkCollection;

document.addEventListener('DOMContentLoaded', () => {
    initCarousels();
    initPullToRefresh();
    initBookmarkButtons();

    // Attach submit event listener to inline collection creation form in bookmark modal
    const inlineForm = document.getElementById('inline-create-collection-form');
    if (inlineForm) {
        inlineForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const submitBtn = document.getElementById('btn-submit-inline-col');
            const titleInput = document.getElementById('inline-col-title');
            const isPublicInput = document.getElementById('inline-col-is-public');

            const title = titleInput.value.trim();
            const is_public = isPublicInput.checked;
            const postId = activeBookmarkPostId;

            if (!title || !postId) return;

            submitBtn.disabled = true;
            submitBtn.innerText = 'กำลังสร้าง...';

            try {
                // 1. Create collection
                const createRes = await fetch('/api/collections/create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ title, is_public })
                });

                const createData = await createRes.json();
                if (createData.status === 'success' && createData.collection) {
                    const colId = createData.collection.id;

                    // 2. Automatically bookmark active post into this newly created collection
                    const toggleRes = await fetch('/api/bookmarks/toggle/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ post_id: postId, collection_id: colId })
                    });
                    const toggleData = await toggleRes.json();

                    showSystemToast(`สร้างคอลเลกชัน "${title}" และบันทึกโพสต์สำเร็จแล้ว`, 'success');
                    
                    // Update ribbon buttons state
                    document.querySelectorAll(`.btn-bookmark-ribbon[data-post-id="${postId}"]`).forEach(btn => {
                        updateBookmarkIconState(btn, toggleData.is_bookmarked_any);
                    });

                    // Refresh modal collections list
                    titleInput.value = '';
                    inlineForm.classList.add('hidden');
                    openBookmarkModal(postId);
                } else {
                    showSystemToast(createData.message || 'ไม่สามารถสร้างคอลเลกชันได้', 'error');
                }
            } catch (err) {
                console.error(err);
                showSystemToast('เกิดข้อผิดพลาดในการเชื่อมต่อ', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = 'สร้างและบันทึก';
            }
        });
    }

    initUserTagPickers();
});

/**
 * Interactive Star Rating Picker Component Handler
 */
function initStarPickers() {
    document.querySelectorAll('.star-picker-group').forEach(group => {
        const targetId = group.dataset.target;
        const targetInput = document.getElementById(targetId);
        const labelSpan = group.querySelector('.star-picker-label');
        const starBtns = group.querySelectorAll('.star-btn');
        let selectedValue = parseInt(group.dataset.selected) || 0;

        function updateStarsDisplay(val) {
            starBtns.forEach(btn => {
                const btnVal = parseInt(btn.dataset.value);
                const icon = btn.querySelector('i') || btn.querySelector('svg');
                if (btnVal <= val) {
                    btn.classList.remove('text-zinc-600');
                    btn.classList.add('text-amber-400');
                    if (icon) {
                        icon.setAttribute('fill', '#fbbf24');
                        icon.setAttribute('stroke', '#fbbf24');
                        icon.style.fill = '#fbbf24';
                        icon.style.stroke = '#fbbf24';
                    }
                } else {
                    btn.classList.remove('text-amber-400');
                    btn.classList.add('text-zinc-600');
                    if (icon) {
                        icon.setAttribute('fill', 'none');
                        icon.setAttribute('stroke', 'currentColor');
                        icon.style.fill = 'none';
                        icon.style.stroke = 'currentColor';
                    }
                }
            });
        }

        // Initialize state
        updateStarsDisplay(selectedValue);

        starBtns.forEach(btn => {
            const btnVal = parseInt(btn.dataset.value);

            // Hover preview
            btn.addEventListener('mouseenter', () => updateStarsDisplay(btnVal));
            group.addEventListener('mouseleave', () => updateStarsDisplay(selectedValue));

            // Click select
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                selectedValue = btnVal;
                group.dataset.selected = selectedValue;
                if (targetInput) targetInput.value = selectedValue;
                updateStarsDisplay(selectedValue);
                if (labelSpan) {
                    labelSpan.textContent = selectedValue ? `${selectedValue}/5 ดาว` : 'ไม่ระบุ';
                }
            });
        });
    });
}
window.initStarPickers = initStarPickers;

function initPlaceReviewForm() {
    const reviewForm = document.getElementById('place-review-form');
    if (!reviewForm || reviewForm.dataset.reviewInit) return;
    reviewForm.dataset.reviewInit = 'true';

    reviewForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('btn-submit-review');
        const formData = new FormData(this);
        const dataObj = {};
        formData.forEach((val, key) => dataObj[key] = val);

        if (!dataObj.score) {
            showSystemToast('กรุณาระบุคะแนนรวม (1-5 ดาว)', 'error');
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerText = 'กำลังบันทึก...';
        }

        try {
            const res = await fetch('/api/reviews/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': typeof getCsrfToken === 'function' ? getCsrfToken() : ''
                },
                body: JSON.stringify(dataObj)
            });

            const data = await res.json();
            if (data.status === 'success') {
                showSystemToast(data.message, 'success');
                const avgSpan = document.getElementById('detail-avg-rating');
                const countSpan = document.getElementById('detail-review-count');
                if (avgSpan) avgSpan.textContent = parseFloat(data.avg_rating).toFixed(1);
                if (countSpan) countSpan.textContent = `${data.review_count} รีวิว`;

                setTimeout(() => window.location.reload(), 500);
            } else {
                showSystemToast(data.message || 'ไม่สามารถบันทึกรีวิวได้', 'error');
            }
        } catch (err) {
            console.error(err);
            showSystemToast('เกิดข้อผิดพลาดในการส่งข้อมูล', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerText = 'บันทึกรีวิว';
            }
        }
    });
}
window.initPlaceReviewForm = initPlaceReviewForm;

async function deleteReview(reviewId) {
    if (!confirm('คุณต้องการลบรีวิวนี้ใช่หรือไม่?')) return;

    try {
        const res = await fetch(`/api/reviews/${reviewId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': typeof getCsrfToken === 'function' ? getCsrfToken() : ''
            }
        });
        const data = await res.json();
        if (data.status === 'success') {
            showSystemToast('ลบรีวิวเรียบร้อยแล้ว', 'success');
            const card = document.getElementById(`review-card-${reviewId}`);
            if (card) card.remove();
            
            const avgSpan = document.getElementById('detail-avg-rating');
            const countSpan = document.getElementById('detail-review-count');
            if (avgSpan) avgSpan.textContent = parseFloat(data.avg_rating).toFixed(1);
            if (countSpan) countSpan.textContent = `${data.review_count} รีวิว`;

            setTimeout(() => window.location.reload(), 400);
        } else {
            showSystemToast(data.message || 'ไม่สามารถลบรีวิวได้', 'error');
        }
    } catch (err) {
        console.error(err);
        showSystemToast('เกิดข้อผิดพลาดในการสื่อสาร', 'error');
    }
}
window.deleteReview = deleteReview;

// -----------------------------------------------------------------------------
// Global System Toast Notification Helper
// -----------------------------------------------------------------------------
function showSystemToast(message, type = 'info') {
    let container = document.getElementById('dynamic-system-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'dynamic-system-toast-container';
        container.className = 'fixed top-5 left-1/2 -translate-x-1/2 z-[300] flex flex-col items-center gap-2 pointer-events-none w-full max-w-sm px-4';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200' :
                    type === 'error' ? 'bg-rose-950/90 border-rose-500/40 text-rose-200' :
                    type === 'warning' ? 'bg-amber-950/90 border-amber-500/40 text-amber-200' :
                    'bg-zinc-900/90 border-white/10 text-white';

    const iconHtml = type === 'success' ? '✓' :
                     type === 'error' ? '✕' :
                     type === 'warning' ? '⚠' : 'ℹ';

    toast.className = `pointer-events-auto px-4 py-2.5 rounded-2xl border text-xs font-bold shadow-2xl backdrop-blur-xl flex items-center gap-2.5 transition-all duration-300 transform -translate-y-4 opacity-0 ${bgClass}`;
    toast.innerHTML = `<span class="w-5 h-5 rounded-full bg-black/40 flex items-center justify-center text-[10px] shrink-0 font-mono">${iconHtml}</span><span class="leading-tight">${message}</span>`;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('-translate-y-4', 'opacity-0');
        toast.classList.add('translate-y-0', 'opacity-100');
    });

    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('-translate-y-4', 'opacity-0');
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 300);
    }, 3200);
}
window.showSystemToast = showSystemToast;

// -----------------------------------------------------------------------------
// Global Report Form AJAX Submission Handler
// -----------------------------------------------------------------------------
onDomReady(() => {
    const reportForm = document.getElementById('global-report-form');
    if (reportForm) {
        reportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('btn-submit-report');
            const originalText = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="animate-spin text-xs">⏳</span> กำลังส่ง...';
            }

            try {
                const formData = new FormData(reportForm);
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const res = await fetch(reportForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrf,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await res.json().catch(() => ({}));
                if (res.ok && data.success) {
                    showSystemToast(data.message || 'ส่งรายงานเรียบร้อยแล้ว', 'success');
                    if (typeof closeUserReportModal === 'function') {
                        closeUserReportModal();
                    }
                } else {
                    showSystemToast(data.message || 'เกิดข้อผิดพลาดในการส่งรายงาน', 'error');
                }
            } catch (err) {
                console.error('Report submission error:', err);
                showSystemToast('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์', 'error');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    }
});

// -----------------------------------------------------------------------------
// Client-Side Image Compression Utility (Prevents HTTP 413 Payload Too Large)
// -----------------------------------------------------------------------------
/**
 * บีบอัดและปรับขนาดรูปภาพฝั่งไคลเอนต์ก่อนอัปโหลด ป้องกันปัญหา Payload Too Large (413) บน Vercel Serverless
 * @param {File} file - ไฟล์รูปภาพต้นฉบับ
 * @param {Object} options - ตัวเลือกการบีบอัด { maxWidth, maxHeight, quality, skipThreshold }
 * @returns {Promise<File>} - ไฟล์รูปภาพที่ถูกบีบอัดแล้ว
 */
async function compressImageFile(file, options = {}) {
    if (!file || !file.type || !file.type.startsWith('image/')) {
        return file;
    }

    const {
        maxWidth = 1920,
        maxHeight = 1920,
        quality = 0.82,
        skipThreshold = 600 * 1024 // 600 KB
    } = options;

    // ถ้าเป็นรูปขนาดเล็กมากอยู่แล้ว และเป็น format ปกติ ให้ข้ามเพื่อความรวดเร็ว
    if (file.size <= skipThreshold && (file.type === 'image/jpeg' || file.type === 'image/webp' || file.type === 'image/png')) {
        return file;
    }

    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onerror = () => resolve(file);
        reader.onload = (e) => {
            const img = new Image();
            img.onerror = () => resolve(file);
            img.onload = () => {
                let { width, height } = img;
                if (!width || !height) {
                    return resolve(file);
                }

                // คำนวณอัตราส่วนการย่อภาพ
                if (width > maxWidth || height > maxHeight) {
                    if (width / height > maxWidth / maxHeight) {
                        height = Math.round((height * maxWidth) / width);
                        width = maxWidth;
                    } else {
                        width = Math.round((width * maxHeight) / height);
                        height = maxHeight;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                if (!ctx) return resolve(file);

                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                ctx.drawImage(img, 0, 0, width, height);

                const outputFormat = 'image/jpeg';
                canvas.toBlob((blob) => {
                    if (!blob) {
                        return resolve(file);
                    }
                    if (blob.size >= file.size && file.type === 'image/jpeg') {
                        return resolve(file);
                    }

                    const originalName = file.name || 'image.jpg';
                    const newName = originalName.replace(/\.[^/.]+$/, "") + ".jpg";
                    const compressedFile = new File([blob], newName, {
                        type: outputFormat,
                        lastModified: Date.now()
                    });

                    resolve(compressedFile);
                }, outputFormat, quality);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

/**
 * บีบอัดรูปภาพหลายรูปพร้อมกัน
 * @param {FileList|File[]} files - รายการไฟล์รูปภาพ
 * @param {Object} options - ตัวเลือกการบีบอัด
 * @returns {Promise<File[]>} - อาร์เรย์ของไฟล์รูปภาพที่บีบอัดแล้ว
 */
async function compressImageFiles(files, options = {}) {
    if (!files || files.length === 0) return [];
    const fileArr = Array.from(files);
    const compressedList = [];
    for (const f of fileArr) {
        if (f && f.type && f.type.startsWith('image/')) {
            const comp = await compressImageFile(f, options);
            compressedList.push(comp);
        } else if (f) {
            compressedList.push(f);
        }
    }
    return compressedList;
}

window.compressImageFile = compressImageFile;
window.compressImageFiles = compressImageFiles;

