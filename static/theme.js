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

// Keep the theme control compact: one small sun/moon icon instead of a text/capsule switch.
function updateToggleButtons(currentTheme) {
    const isDark = currentTheme === 'dark';
    const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
    toggleBtns.forEach(btn => {
        btn.setAttribute('aria-label', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.innerHTML = `<span class="theme-icon" aria-hidden="true">${isDark ? '🌙' : '☀️'}</span>`;
    });
}

// Replace legacy Settings + Logout navbar controls on authenticated pages with one profile menu.
// Dashboard already has this menu, so it is left untouched there.
function setupGlobalProfileMenu() {
    if (document.querySelector('#profileMenu')) return;

    const userInfo = document.querySelector('.user-info');
    const settingsBtn = document.querySelector('.settings-btn');
    const logoutForm = document.querySelector('.logout-btn')?.closest('form');
    if (!userInfo || !settingsBtn || !logoutForm) return;

    const settingsHref = settingsBtn.getAttribute('href') || '/settings';
    settingsBtn.remove();

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
    trigger.addEventListener('click', (event) => {
        event.stopPropagation();
        const open = profileMenu.classList.toggle('open');
        trigger.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', (event) => {
        if (!profileMenu.contains(event.target)) closeMenu();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeMenu();
    });
}

// Ensure profile-menu styling exists even on older authenticated templates.
function setupProfileMenuStyles() {
    if (document.querySelector('#global-profile-menu-style')) return;
    const style = document.createElement('style');
    style.id = 'global-profile-menu-style';
    style.textContent = `
        .profile-menu{position:relative}
        .profile-trigger{width:36px;height:36px;padding:0;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border-color);border-radius:50%;background:var(--input-bg);color:var(--text-primary);cursor:pointer;font-size:1.05rem;transition:.2s}
        .profile-trigger:hover,.profile-trigger:focus-visible{border-color:var(--accent-primary);transform:translateY(-1px);outline:none}
        .profile-dropdown{position:absolute;top:calc(100% + 10px);right:0;min-width:165px;padding:7px;border:1px solid var(--border-color);border-radius:14px;background:var(--bg-card);box-shadow:var(--shadow-card);backdrop-filter:blur(18px);opacity:0;visibility:hidden;transform:translateY(-6px) scale(.98);transform-origin:top right;transition:.18s ease;z-index:1000}
        .profile-menu.open .profile-dropdown{opacity:1;visibility:visible;transform:translateY(0) scale(1)}
        .profile-item{width:100%;min-height:38px;display:flex;align-items:center;gap:9px;padding:8px 10px;border:0;border-radius:9px;background:transparent;color:var(--text-primary);text-decoration:none;font:inherit;font-size:.84rem;font-weight:750;cursor:pointer;text-align:left}
        .profile-item:hover,.profile-item:focus-visible{background:var(--input-bg);color:var(--accent-primary);outline:none}
        .profile-logout-form{margin:0;padding:0}
        .profile-item.logout-item{color:var(--currency-expense)}
        .profile-item.logout-item:hover,.profile-item.logout-item:focus-visible{color:var(--currency-expense);background:rgba(244,63,94,.1)}
        .theme-toggle-btn{width:34px!important;height:34px!important;padding:0!important;display:inline-flex!important;align-items:center!important;justify-content:center!important}
        .theme-toggle-btn .theme-icon{display:block!important;font-size:.95rem!important;line-height:1!important}
        @media(max-width:600px){.profile-dropdown{right:0;min-width:155px}}
    `;
    document.head.appendChild(style);
}

// Force the dashboard Last Transaction card to remain blue regardless of income/expense type.
function setupLastTransactionBlueCard() {
    const card = document.querySelector('#lastTransactionCard');
    if (!card) return;
    const blueBorder = 'rgba(56,189,248,.58)';
    const blueBackground = 'linear-gradient(135deg,rgba(56,189,248,.22),rgba(56,189,248,.07))';
    card.style.borderColor = blueBorder;
    card.style.background = blueBackground;
    const icon = card.querySelector('.kpi-icon');
    if (icon) icon.style.background = 'rgba(56,189,248,.20)';
    const value = card.querySelector('.kpi-value');
    if (value) value.style.color = 'var(--accent-primary)';
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
    container.addEventListener('click',(e)=>{if(e.target===container){const button=container.querySelector('.toast-close-btn');if(button)button.click();}});
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
        @keyframes premiumFadeUp { from { opacity:0;transform:translateY(18px) scale(.985); } to { opacity:1;transform:translateY(0) scale(1); } }
        @keyframes premiumGlow { 0%,100% { opacity:.45;transform:scale(1); } 50% { opacity:.8;transform:scale(1.04); } }
        @keyframes premiumShimmer { 0% { transform:translateX(-120%); } 100% { transform:translateX(120%); } }
        .premium-stagger { animation:premiumFadeUp .55s cubic-bezier(.22,1,.36,1) both; }
        .hero-card,.kpi-card,.module-card,.panel,.control-panel,.kpi,.category-card,.record { will-change:transform; }
        ${isDashboard ? `
        .hero-card { background:linear-gradient(135deg,rgba(56,189,248,.10),rgba(99,102,241,.08) 52%,var(--bg-card));border-color:rgba(129,140,248,.28);box-shadow:0 22px 55px rgba(15,23,42,.18),0 0 0 1px rgba(255,255,255,.025) inset; }
        .hero-card::before { animation:premiumGlow 5s ease-in-out infinite; }
        .kpi-card { box-shadow:0 16px 38px rgba(15,23,42,.15),0 1px 0 rgba(255,255,255,.035) inset; }
        .module-card { min-height:220px;justify-content:center;box-shadow:0 16px 38px rgba(15,23,42,.14),0 1px 0 rgba(255,255,255,.04) inset; }
        .add-record-card { background:linear-gradient(145deg,rgba(16,185,129,.13),rgba(16,185,129,.035) 55%,var(--bg-card)); }
        .view-card { background:linear-gradient(145deg,rgba(56,189,248,.13),rgba(56,189,248,.035) 55%,var(--bg-card)); }
        .summary-mod-card { background:linear-gradient(145deg,rgba(129,140,248,.15),rgba(99,102,241,.035) 55%,var(--bg-card)); }
        .module-card::before { content:'';position:absolute;inset:0;pointer-events:none;border-radius:inherit;background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.08) 50%,transparent 65%);transform:translateX(-120%);opacity:0; }
        .module-card:hover::before { opacity:1;animation:premiumShimmer .8s ease; }
        ` : ''}
        ${isSummary ? `
        .panel { background:linear-gradient(145deg,rgba(56,189,248,.045),rgba(99,102,241,.035) 45%,var(--bg-card));box-shadow:0 24px 60px rgba(15,23,42,.16),0 1px 0 rgba(255,255,255,.035) inset; }
        .control-panel { box-shadow:0 12px 30px rgba(15,23,42,.10),0 1px 0 rgba(255,255,255,.035) inset; }
        .kpi { box-shadow:0 14px 32px rgba(15,23,42,.12),0 1px 0 rgba(255,255,255,.035) inset;transition:transform .28s ease,box-shadow .28s ease,border-color .28s ease; }
        .kpi:hover { transform:translateY(-4px);box-shadow:0 20px 42px rgba(15,23,42,.18); }
        .kpi.inc { background:linear-gradient(145deg,rgba(16,185,129,.12),rgba(16,185,129,.035) 58%,var(--input-bg)); }
        .kpi.exp { background:linear-gradient(145deg,rgba(244,63,94,.12),rgba(244,63,94,.035) 58%,var(--input-bg)); }
        .kpi.net { background:linear-gradient(145deg,rgba(99,102,241,.13),rgba(99,102,241,.035) 58%,var(--input-bg)); }
        .category-card,.record { box-shadow:0 10px 26px rgba(15,23,42,.09),0 1px 0 rgba(255,255,255,.025) inset; }
        .category-card { transition:transform .28s ease,box-shadow .28s ease,border-color .28s ease; }
        .category-card:hover { transform:translateY(-5px) scale(1.008); }
        ` : ''}
        @media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important; } }
    `;
    document.head.appendChild(style);
    const selectors = isDashboard ? ['.hero-card','.kpi-card','.module-card','.page-footer'] : ['.panel','.control-panel','.kpis','.category-card','.record'];
    let delay=0;
    selectors.forEach(selector=>document.querySelectorAll(selector).forEach(el=>{el.classList.add('premium-stagger');el.style.animationDelay=`${delay}ms`;delay+=65;}));
}

function setupDashboardEnhancements() {
    if (window.location.pathname !== '/dashboard' && window.location.pathname !== '/index') return;
    const hero=document.querySelector('.hero-card');
    const balance=document.querySelector('.balance-value');
    if(!hero||!balance)return;
    hero.addEventListener('pointermove',(event)=>{const rect=hero.getBoundingClientRect();const x=((event.clientX-rect.left)/rect.width)*100;const y=((event.clientY-rect.top)/rect.height)*100;hero.style.setProperty('--pointer-x',`${x}%`);hero.style.setProperty('--pointer-y',`${y}%`);});
    const enhancementStyle=document.createElement('style');enhancementStyle.id='dashboard-fintech-enhancements';enhancementStyle.textContent=`
        .hero-card::after{background:radial-gradient(circle at var(--pointer-x,80%) var(--pointer-y,20%),rgba(255,255,255,.09),transparent 30%),linear-gradient(135deg,rgba(16,185,129,.10),rgba(99,102,241,.10));transition:background-position .2s ease;}
        .balance-value{text-shadow:0 8px 28px rgba(56,189,248,.12)}
        .snapshot-row{transition:transform .22s ease,border-color .22s ease,background .22s ease}.snapshot-row:hover{transform:translateX(3px);border-color:rgba(129,140,248,.32)}
        .kpi-card:focus-within,.module-card:focus-visible{outline:2px solid rgba(56,189,248,.45);outline-offset:3px}
        @media(max-width:680px){.hero-card::after{display:none}}
    `;document.head.appendChild(enhancementStyle);
    const savingsKpi=document.querySelector('.savings-kpi');
    if(savingsKpi){const value=savingsKpi.querySelector('.kpi-value');const meta=savingsKpi.querySelector('.kpi-meta');if(value&&meta&&!savingsKpi.querySelector('.savings-meter')){const caption=meta.textContent.trim();const match=caption.match(/(\d[\d,]*)\s*total/i);const meter=document.createElement('div');meter.className='savings-meter';meter.setAttribute('aria-hidden','true');meter.innerHTML='<span class="savings-meter-fill"></span>';savingsKpi.appendChild(meter);const fill=meter.querySelector('.savings-meter-fill');if(fill){const records=match?Number(match[1].replace(/,/g,'')):1;fill.style.width=`${Math.min(100,Math.max(12,records>0?72:12))}%`;}}}
    document.querySelectorAll('.kpi-value,.balance-value').forEach(el=>{const raw=el.textContent.trim();const match=raw.match(/^(.*?)([\d,]+)(.*?)$/);if(!match||el.dataset.animated==='true')return;const target=Number(match[2].replace(/,/g,''));if(!Number.isFinite(target))return;el.dataset.animated='true';const prefix=match[1],suffix=match[3],duration=650,start=performance.now();const tick=(now)=>{const progress=Math.min(1,(now-start)/duration),eased=1-Math.pow(1-progress,3),current=Math.round(target*eased).toLocaleString('en-US');el.textContent=`${prefix}${current}${suffix}`;if(progress<1)requestAnimationFrame(tick)};requestAnimationFrame(tick);});
}

// Event listener on page load
document.addEventListener('DOMContentLoaded',()=>{
    const currentTheme=document.documentElement.getAttribute('data-theme')||'dark';
    updateToggleButtons(currentTheme);
    setupProfileMenuStyles();
    setupGlobalProfileMenu();
    setupLastTransactionBlueCard();
    setupDoubleSubmissionProtection();
    setupToastModal();
    setupPremiumPageMotion();
    setupDashboardEnhancements();
});
