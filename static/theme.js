// Theme Initialization (Prevents FOUC / Theme Flash)
(function () {
    const savedTheme = localStorage.getItem('app-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

// Toggle theme function
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('app-theme', newTheme);
    updateToggleButtons(newTheme);
}

// Update pill capsule switch toggle buttons
function updateToggleButtons(currentTheme) {
    const isDark = currentTheme === 'dark';
    const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
    toggleBtns.forEach(btn => {
        btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.innerHTML = `
            <span class="theme-toggle-switch ${isDark ? 'mode-dark' : 'mode-light'}">
                <span class="switch-icon sun-icon ${!isDark ? 'active' : ''}">☀️</span>
                <span class="switch-icon moon-icon ${isDark ? 'active' : ''}">🌙</span>
            </span>
        `;
    });
}

// Prevent Double Submissions across all forms to stop duplicate data entries
function setupDoubleSubmissionProtection() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function (e) {
            if (form.dataset.submitting === 'true') {
                e.preventDefault();
                return false;
            }
            form.dataset.submitting = 'true';
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                const isAddForm = form.getAttribute('action') === '/add';
                const labelText = isAddForm ? '⏳ Saving...' : '⏳ Processing...';
                if (submitBtn.tagName === 'BUTTON') {
                    submitBtn.innerHTML = labelText;
                } else {
                    submitBtn.value = labelText;
                }
                setTimeout(() => {
                    submitBtn.disabled = true;
                }, 10);
            }
        });
    });
}

// Enhance Flash Messages into a truly centered, screen-level animated toast popup.
function setupToastModal() {
    const container = document.querySelector('.flash-container');
    if (!container) return;

    // Move the overlay to <body> so no transformed/blurred parent can affect its position.
    if (container.parentElement !== document.body) {
        document.body.appendChild(container);
    }

    // Force the overlay geometry inline as a final safeguard against page-specific CSS.
    Object.assign(container.style, {
        position: 'fixed',
        inset: '0',
        width: '100vw',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0',
        padding: '20px',
        zIndex: '2147483647',
        boxSizing: 'border-box'
    });

    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';

    const messages = container.querySelectorAll('.flash-message');
    messages.forEach(msg => {
        const text = msg.innerText.trim();
        const lowerText = text.toLowerCase();
        const isDelete = lowerText.includes('delete');
        const isDanger = msg.classList.contains('danger') || msg.classList.contains('error') || lowerText.includes('invalid') || lowerText.includes('error');
        const isUpdate = lowerText.includes('update') || lowerText.includes('edit') || lowerText.includes('reset');

        let title = 'Success!';
        let svgHtml = '';

        if (isDelete) {
            title = 'Deleted Successfully!';
            msg.classList.add('delete-type');
            svgHtml = `
                <div class="toast-svg-wrapper">
                    <svg class="checkmark-svg delete" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark-circle delete" cx="26" cy="26" r="23" fill="none"/>
                        <path class="checkmark-check delete" fill="none" d="M17 17 L35 35 M35 17 L17 35" stroke-linecap="round"/>
                    </svg>
                </div>
            `;
        } else if (isDanger) {
            title = 'Attention!';
            msg.classList.add('danger-type');
            svgHtml = `
                <div class="toast-svg-wrapper">
                    <svg class="checkmark-svg danger" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark-circle danger" cx="26" cy="26" r="23" fill="none"/>
                        <path class="checkmark-check danger" fill="none" d="M26 15 v14 M26 35 v2" stroke-linecap="round"/>
                    </svg>
                </div>
            `;
        } else if (isUpdate) {
            title = 'Updated Successfully!';
            svgHtml = `
                <div class="toast-svg-wrapper">
                    <svg class="checkmark-svg success" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark-circle success" cx="26" cy="26" r="23" fill="none"/>
                        <path class="checkmark-check success" fill="none" d="M14.5 27.5 L22.5 35.5 L37.5 17.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
            `;
        } else {
            if (lowerText.includes('income')) {
                title = 'Income Added!';
            } else if (lowerText.includes('expense')) {
                title = 'Expense Added!';
            } else if (lowerText.includes('login') || lowerText.includes('welcome')) {
                title = 'Welcome Back!';
            } else if (lowerText.includes('signup')) {
                title = 'Account Created!';
            }
            svgHtml = `
                <div class="toast-svg-wrapper">
                    <svg class="checkmark-svg success" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark-circle success" cx="26" cy="26" r="23" fill="none"/>
                        <path class="checkmark-check success" fill="none" d="M14.5 27.5 L22.5 35.5 L37.5 17.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
            `;
        }

        msg.innerHTML = `
            ${svgHtml}
            <div class="toast-title">${title}</div>
            <div class="toast-body">${text}</div>
            <button type="button" class="toast-close-btn">OK</button>
            <div class="toast-progress-bar"></div>
        `;

        // Keep the card itself centered even if a page-specific stylesheet changes flex behavior.
        Object.assign(msg.style, {
            position: 'relative',
            margin: '0 auto',
            left: 'auto',
            right: 'auto',
            top: 'auto',
            bottom: 'auto',
            transform: 'none'
        });

        const closeBtn = msg.querySelector('.toast-close-btn');
        let dismissed = false;
        const dismissToast = () => {
            if (dismissed) return;
            dismissed = true;
            container.classList.add('toast-hiding');
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
            setTimeout(() => container.remove(), 300);
        };

        if (closeBtn) {
            closeBtn.addEventListener('click', dismissToast);
        }

        setTimeout(dismissToast, 3200);
    });

    container.addEventListener('click', (e) => {
        if (e.target === container) {
            const button = container.querySelector('.toast-close-btn');
            if (button) button.click();
        }
    });
}

// High-end visual polish shared by Dashboard and Summary pages.
function setupPremiumPageMotion() {
    const path = window.location.pathname;
    const isDashboard = path === '/dashboard' || path === '/index';
    const isSummary = path === '/summary';
    if (!isDashboard && !isSummary) return;

    const style = document.createElement('style');
    style.id = 'premium-page-motion';
    style.textContent = `
        @keyframes premiumFadeUp {
            from { opacity: 0; transform: translateY(18px) scale(.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes premiumGlow {
            0%,100% { opacity:.45; transform:scale(1); }
            50% { opacity:.8; transform:scale(1.04); }
        }
        @keyframes premiumShimmer {
            0% { transform:translateX(-120%); }
            100% { transform:translateX(120%); }
        }
        .premium-stagger {
            animation: premiumFadeUp .55s cubic-bezier(.22,1,.36,1) both;
        }
        .hero-card, .kpi-card, .module-card, .panel, .control-panel, .kpi, .category-card, .record {
            will-change: transform;
        }
        ${isDashboard ? `
        .hero-card {
            background:linear-gradient(135deg,rgba(56,189,248,.10),rgba(99,102,241,.08) 52%,var(--bg-card));
            border-color:rgba(129,140,248,.28);
            box-shadow:0 22px 55px rgba(15,23,42,.18),0 0 0 1px rgba(255,255,255,.025) inset;
        }
        .hero-card::before { animation:premiumGlow 5s ease-in-out infinite; }
        .kpi-card {
            box-shadow:0 16px 38px rgba(15,23,42,.15),0 1px 0 rgba(255,255,255,.035) inset;
        }
        .module-card {
            min-height:220px;
            justify-content:center;
            box-shadow:0 16px 38px rgba(15,23,42,.14),0 1px 0 rgba(255,255,255,.04) inset;
        }
        .add-record-card { background:linear-gradient(145deg,rgba(16,185,129,.13),rgba(16,185,129,.035) 55%,var(--bg-card)); }
        .view-card { background:linear-gradient(145deg,rgba(56,189,248,.13),rgba(56,189,248,.035) 55%,var(--bg-card)); }
        .summary-mod-card { background:linear-gradient(145deg,rgba(129,140,248,.15),rgba(99,102,241,.035) 55%,var(--bg-card)); }
        .module-card::before {
            content:''; position:absolute; inset:0; pointer-events:none; border-radius:inherit;
            background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.08) 50%,transparent 65%);
            transform:translateX(-120%); opacity:0;
        }
        .module-card:hover::before { opacity:1; animation:premiumShimmer .8s ease; }
        ` : ''}
        ${isSummary ? `
        .panel {
            background:linear-gradient(145deg,rgba(56,189,248,.045),rgba(99,102,241,.035) 45%,var(--bg-card));
            box-shadow:0 24px 60px rgba(15,23,42,.16),0 1px 0 rgba(255,255,255,.035) inset;
        }
        .control-panel {
            box-shadow:0 12px 30px rgba(15,23,42,.10),0 1px 0 rgba(255,255,255,.035) inset;
        }
        .kpi {
            box-shadow:0 14px 32px rgba(15,23,42,.12),0 1px 0 rgba(255,255,255,.035) inset;
            transition:transform .28s ease, box-shadow .28s ease, border-color .28s ease;
        }
        .kpi:hover { transform:translateY(-4px); box-shadow:0 20px 42px rgba(15,23,42,.18); }
        .kpi.inc { background:linear-gradient(145deg,rgba(16,185,129,.12),rgba(16,185,129,.035) 58%,var(--input-bg)); }
        .kpi.exp { background:linear-gradient(145deg,rgba(244,63,94,.12),rgba(244,63,94,.035) 58%,var(--input-bg)); }
        .kpi.net { background:linear-gradient(145deg,rgba(99,102,241,.13),rgba(99,102,241,.035) 58%,var(--input-bg)); }
        .category-card, .record {
            box-shadow:0 10px 26px rgba(15,23,42,.09),0 1px 0 rgba(255,255,255,.025) inset;
        }
        .category-card { transition:transform .28s ease, box-shadow .28s ease, border-color .28s ease; }
        .category-card:hover { transform:translateY(-5px) scale(1.008); }
        ` : ''}
        @media (prefers-reduced-motion: reduce) {
            *,*::before,*::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; }
        }
    `;
    document.head.appendChild(style);

    const selectors = isDashboard
        ? ['.hero-card', '.kpi-card', '.module-card', '.page-footer']
        : ['.panel', '.control-panel', '.kpis', '.category-card', '.record'];
    let delay = 0;
    selectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            el.classList.add('premium-stagger');
            el.style.animationDelay = `${delay}ms`;
            delay += 65;
        });
    });
}

// Event listener on page load
document.addEventListener('DOMContentLoaded', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    updateToggleButtons(currentTheme);
    setupDoubleSubmissionProtection();
    setupToastModal();
    setupPremiumPageMotion();
});
