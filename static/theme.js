// Theme Initialization (Prevents FOUC / Theme Flash)
(function () {
    const savedTheme = localStorage.getItem('app-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('app-theme', newTheme);
    updateToggleButtons(newTheme);
}

function updateToggleButtons(currentTheme) {
    const isDark = currentTheme === 'dark';
    document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
        btn.type = 'button';
        btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.innerHTML = `<span class="theme-icon" aria-hidden="true">${isDark ? '☀️' : '🌙'}</span>`;
    });
}

function setupGlobalThemeControl() {
    // Remove duplicate theme controls while keeping the first one.
    const themeButtons = document.querySelectorAll('.theme-toggle-btn');
    themeButtons.forEach((btn, index) => {
        if (index > 0) btn.remove();
    });

    const themeButton = document.querySelector('.theme-toggle-btn');
    if (themeButton) {
        themeButton.onclick = toggleTheme;
    }
    updateToggleButtons(document.documentElement.getAttribute('data-theme') || 'dark');
}

function setupGlobalProfileMenu() {
    if (document.querySelector('#profileMenu')) return;

    const userInfo = document.querySelector('.user-info');
    const settingsBtn = document.querySelector('.settings-btn');
    const logoutForm = document.querySelector('.logout-btn')?.closest('form');
    if (!userInfo || !logoutForm) return;

    const settingsHref = settingsBtn?.getAttribute('href') || '/settings';
    if (settingsBtn) settingsBtn.remove();

    const profileMenu = document.createElement('div');
    profileMenu.className = 'profile-menu';
    profileMenu.id = 'profileMenu';
    profileMenu.innerHTML = `
        <button class="profile-trigger" id="profileTrigger" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Open profile menu" title="Profile">👤</button>
        <div class="profile-dropdown" id="profileDropdown" role="menu">
            <a href="${settingsHref}" class="profile-item" role="menuitem">⚙️ Settings</a>
        </div>
    `;

    const dropdown = profileMenu.querySelector('.profile-dropdown');
    dropdown.appendChild(logoutForm);
    logoutForm.className = 'profile-logout-form';
    const logoutBtn = logoutForm.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.className = 'profile-item logout-item';
        logoutBtn.setAttribute('role', 'menuitem');
        logoutBtn.innerHTML = '🚪 Logout';
        logoutBtn.style.cssText = '';
    }

    userInfo.appendChild(profileMenu);

    const trigger = profileMenu.querySelector('#profileTrigger');
    const closeMenu = () => {
        profileMenu.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
    };
    trigger.addEventListener('click', event => {
        event.stopPropagation();
        const open = profileMenu.classList.toggle('open');
        trigger.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', event => {
        if (!profileMenu.contains(event.target)) closeMenu();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeMenu();
    });
}

function setupProfileMenuStyles() {
    if (document.querySelector('#global-profile-menu-style')) return;
    const style = document.createElement('style');
    style.id = 'global-profile-menu-style';
    style.textContent = `
        .user-info{display:flex;align-items:center;gap:8px}
        .profile-menu{position:relative;display:flex;align-items:center}
        .profile-trigger{width:36px;height:36px;padding:0;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border-color);border-radius:50%;background:var(--input-bg);color:var(--text-primary);cursor:pointer;font-size:1.05rem;transition:.2s}
        .profile-trigger:hover,.profile-trigger:focus-visible{border-color:var(--accent-primary);transform:translateY(-1px);outline:none}
        .profile-dropdown{position:absolute;top:calc(100% + 10px);right:0;min-width:165px;padding:7px;border:1px solid var(--border-color);border-radius:14px;background:var(--bg-card);box-shadow:var(--shadow-card);backdrop-filter:blur(18px);opacity:0;visibility:hidden;transform:translateY(-6px) scale(.98);transform-origin:top right;transition:.18s ease;z-index:1000}
        .profile-menu.open .profile-dropdown{opacity:1;visibility:visible;transform:translateY(0) scale(1)}
        .profile-item{width:100%;min-height:38px;display:flex;align-items:center;gap:9px;padding:8px 10px;border:0;border-radius:9px;background:transparent;color:var(--text-primary);text-decoration:none;font:inherit;font-size:.84rem;font-weight:750;cursor:pointer;text-align:left;box-sizing:border-box}
        .profile-item:hover,.profile-item:focus-visible{background:var(--input-bg);color:var(--accent-primary);outline:none}
        .profile-logout-form{margin:0;padding:0;width:100%}
        .profile-item.logout-item{color:var(--currency-expense)}
        .profile-item.logout-item:hover,.profile-item.logout-item:focus-visible{color:var(--currency-expense);background:rgba(244,63,94,.1)}
        .theme-toggle-btn{width:34px!important;height:34px!important;min-width:34px!important;padding:0!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;border-radius:10px!important}
        .theme-toggle-btn .theme-icon{display:block!important;font-size:.95rem!important;line-height:1!important}
        @media(max-width:600px){.profile-dropdown{right:0;min-width:155px}}
    `;
    document.head.appendChild(style);
}

function setupLastTransactionBlueCard() {
    const card = document.querySelector('#lastTransactionCard');
    if (!card) return;
    card.style.borderColor = 'rgba(56,189,248,.58)';
    card.style.background = 'linear-gradient(135deg,rgba(56,189,248,.22),rgba(56,189,248,.07))';
    const icon = card.querySelector('.kpi-icon');
    if (icon) icon.style.background = 'rgba(56,189,248,.20)';
    const value = card.querySelector('.kpi-value');
    if (value) value.style.color = 'var(--accent-primary)';
}

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
                if (submitBtn.tagName === 'BUTTON') submitBtn.innerHTML = labelText;
                else submitBtn.value = labelText;
                setTimeout(() => { submitBtn.disabled = true; }, 10);
            }
        });
    });
}

function setupToastModal() {
    const container = document.querySelector('.flash-container');
    if (!container) return;
    if (container.parentElement !== document.body) document.body.appendChild(container);
    Object.assign(container.style, {position:'fixed',inset:'0',width:'100vw',height:'100vh',display:'flex',alignItems:'center',justifyContent:'center',margin:'0',padding:'20px',zIndex:'2147483647',boxSizing:'border-box'});
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
            title = 'Deleted Successfully!'; msg.classList.add('delete-type');
            svgHtml = `<div class="toast-svg-wrapper"><svg class="checkmark-svg delete" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark-circle delete" cx="26" cy="26" r="23" fill="none"/><path class="checkmark-check delete" fill="none" d="M17 17 L35 35 M35 17 L17 35" stroke-linecap="round"/></svg></div>`;
        } else if (isDanger) {
            title = 'Attention!'; msg.classList.add('danger-type');
            svgHtml = `<div class="toast-svg-wrapper"><svg class="checkmark-svg danger" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark-circle danger" cx="26" cy="26" r="23" fill="none"/><path class="checkmark-check danger" fill="none" d="M26 15 v14 M26 35 v2" stroke-linecap="round"/></svg></div>`;
        } else if (isUpdate) {
            title = 'Updated Successfully!';
            svgHtml = `<div class="toast-svg-wrapper"><svg class="checkmark-svg success" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark-circle success" cx="26" cy="26" r="23" fill="none"/><path class="checkmark-check success" fill="none" d="M14.5 27.5 L22.5 35.5 L37.5 17.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`;
        } else {
            if (lowerText.includes('income')) title = 'Income Added!';
            else if (lowerText.includes('expense')) title = 'Expense Added!';
            else if (lowerText.includes('login') || lowerText.includes('welcome')) title = 'Welcome Back!';
            else if (lowerText.includes('signup')) title = 'Account Created!';
            svgHtml = `<div class="toast-svg-wrapper"><svg class="checkmark-svg success" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark-circle success" cx="26" cy="26" r="23" fill="none"/><path class="checkmark-check success" fill="none" d="M14.5 27.5 L22.5 35.5 L37.5 17.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`;
        }
        msg.innerHTML = `${svgHtml}<div class="toast-title">${title}</div><div class="toast-body">${text}</div><button type="button" class="toast-close-btn">OK</button><div class="toast-progress-bar"></div>`;
        Object.assign(msg.style,{position:'relative',margin:'0 auto',left:'auto',right:'auto',top:'auto',bottom:'auto',transform:'none'});
        const closeBtn = msg.querySelector('.toast-close-btn');
        let dismissed = false;
        const dismissToast = () => { if (dismissed) return; dismissed = true; container.classList.add('toast-hiding'); document.documentElement.style.overflow=''; document.body.style.overflow=''; setTimeout(()=>container.remove(),300); };
        if (closeBtn) closeBtn.addEventListener('click',dismissToast);
        setTimeout(dismissToast,3200);
    });
    container.addEventListener('click',e=>{if(e.target===container){const button=container.querySelector('.toast-close-btn');if(button)button.click();}});
}

function setupPremiumPageMotion() {
    const path = window.location.pathname;
    const isDashboard = path === '/dashboard' || path === '/index';
    const isSummary = path === '/summary';
    if (!isDashboard && !isSummary) return;
    const style = document.createElement('style');
    style.id = 'premium-page-motion';
    style.textContent = `
        @keyframes premiumFadeUp { from { opacity:0;transform:translateY(18px) scale(.985); } to { opacity:1;transform:translateY(0) scale(1); } }
        @keyframes premiumGlow { 0%,100% { opacity:.45;transform:scale(1); } 50% { opacity:.8;transform:scale(1.04); } }
        @keyframes premiumShimmer { 0% { transform:translateX(-120%); } 100% { transform:translateX(120%); } }
        .premium-stagger { animation:premiumFadeUp .55s cubic-bezier(.22,1,.36,1) both; }
        .hero-card,.kpi-card,.module-card,.panel,.control-panel,.kpi,.category-card,.record { will-change:transform; }
        .hero-card { background:linear-gradient(135deg,rgba(56,189,248,.10),rgba(99,102,241,.08) 52%,var(--bg-card));border-color:rgba(129,140,248,.28);box-shadow:0 22px 55px rgba(15,23,42,.18),0 0 0 1px rgba(255,255,255,.025) inset; }
        .hero-card::before { animation:premiumGlow 5s ease-in-out infinite; }
        .kpi-card { box-shadow:0 16px 38px rgba(15,23,42,.15),0 1px 0 rgba(255,255,255,.035) inset; }
        .module-card { min-height:220px;justify-content:center;box-shadow:0 16px 38px rgba(15,23,42,.14),0 1px 0 rgba(255,255,255,.04) inset; }
        .add-record-card { background:linear-gradient(145deg,rgba(16,185,129,.13),rgba(16,185,129,.035) 55%,var(--bg-card)); }
        .view-card { background:linear-gradient(145deg,rgba(56,189,248,.13),rgba(56,189,248,.035) 55%,var(--bg-card)); }
        .summary-mod-card { background:linear-gradient(145deg,rgba(129,140,248,.15),rgba(99,102,241,.035) 55%,var(--bg-card)); }
        .module-card::before { content:'';position:absolute;inset:0;pointer-events:none;border-radius:inherit;background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.08) 50%,transparent 65%);transform:translateX(-120%);opacity:0; }
        .module-card:hover::before { opacity:1;animation:premiumShimmer .8s ease; }
        .panel { background:linear-gradient(145deg,rgba(56,189,248,.045),rgba(99,102,241,.035) 45%,var(--bg-card));box-shadow:0 24px 60px rgba(15,23,42,.16),0 1px 0 rgba(255,255,255,.035) inset; }
        .control-panel { box-shadow:0 12px 30px rgba(15,23,42,.10),0 1px 0 rgba(255,255,255,.035) inset; }
        .kpi { box-shadow:0 14px 32px rgba(15,23,42,.12),0 1px 0 rgba(255,255,255,.035) inset;transition:transform .28s ease,box-shadow .28s ease,border-color .28s ease; }
        .kpi:hover { transform:translateY(-4px);box-shadow:0 20px 42px rgba(15,23,42,.18); }
        .premium-stagger:nth-child(1){animation-delay:.04s}.premium-stagger:nth-child(2){animation-delay:.09s}.premium-stagger:nth-child(3){animation-delay:.14s}.premium-stagger:nth-child(4){animation-delay:.19s}.premium-stagger:nth-child(5){animation-delay:.24s}.premium-stagger:nth-child(6){animation-delay:.29s}
        @media (prefers-reduced-motion: reduce){.premium-stagger{animation:none!important}.hero-card::before,.module-card:hover::before{animation:none!important}}
    `;
    document.head.appendChild(style);
    document.querySelectorAll('.hero-card,.kpi-card,.module-card,.panel,.control-panel,.kpi,.category-card,.record').forEach((el,index)=>{el.classList.add('premium-stagger');el.style.animationDelay=`${Math.min(index*0.06,0.42)}s`;});
}

function setupDashboardEnhancements() {
    const dashboard = document.querySelector('.dashboard-page');
    if (!dashboard) return;
    const cards = dashboard.querySelectorAll('.kpi-card,.module-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width - .5) * 2;
            const y = ((e.clientY - rect.top) / rect.height - .5) * 2;
            card.style.transform = `perspective(900px) rotateX(${(-y*2).toFixed(2)}deg) rotateY(${(x*2).toFixed(2)}deg) translateY(-3px)`;
        });
        card.addEventListener('mouseleave', () => { card.style.transform = ''; });
    });
}

function setupLastTransactionData() {
    const card = document.querySelector('#lastTransactionCard');
    if (!card) return;
    fetch('/view?type=all', {headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(response => response.ok ? response.text() : '')
        .then(html => {
            if (!html) return;
            const doc = new DOMParser().parseFromString(html,'text/html');
            const firstRow = doc.querySelector('tbody tr');
            if (!firstRow) return;
            const cells = firstRow.querySelectorAll('td');
            const date = cells[0]?.textContent.trim() || '—';
            const description = cells[1]?.textContent.trim() || '—';
            const amount = cells[3]?.textContent.trim() || '—';
            const type = (firstRow.getAttribute('data-record-type') || cells[2]?.textContent || '').toLowerCase();
            const label = card.querySelector('.kpi-label');
            const value = card.querySelector('.kpi-value');
            const meta = card.querySelector('.kpi-meta');
            if (label) label.textContent = 'Last Transaction';
            if (value) value.textContent = amount;
            if (meta) meta.innerHTML = `${description} · ${date}`;
            card.classList.remove('income','expense');
            card.classList.add(type.includes('income') ? 'income' : 'expense');
        })
        .catch(() => {});
}

function setupPage() {
    setupGlobalThemeControl();
    setupProfileMenuStyles();
    setupGlobalProfileMenu();
    setupProfileMenuStyles();
    updateToggleButtons(document.documentElement.getAttribute('data-theme') || 'dark');
    setupDoubleSubmissionProtection();
    setupToastModal();
    setupPremiumPageMotion();
    setupDashboardEnhancements();
    setupLastTransactionData();
    setupLastTransactionBlueCard();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupPage);
else setupPage();
