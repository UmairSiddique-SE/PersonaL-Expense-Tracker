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

// Enhance Flash Messages into Screen-Centered Animated Toast Popups
function setupToastModal() {
    const container = document.querySelector('.flash-container');
    if (!container) return;

    // Attach directly to body so no parent transform or backdrop-filter offsets it
    if (container.parentElement !== document.body) {
        document.body.appendChild(container);
    }

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

        const closeBtn = msg.querySelector('.toast-close-btn');
        const dismissToast = () => {
            container.classList.add('toast-hiding');
            setTimeout(() => container.remove(), 300);
        };

        if (closeBtn) {
            closeBtn.addEventListener('click', dismissToast);
        }

        container.addEventListener('click', (e) => {
            if (e.target === container) {
                dismissToast();
            }
        });

        setTimeout(dismissToast, 3200);
    });
}

// Event listener on page load
document.addEventListener('DOMContentLoaded', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    updateToggleButtons(currentTheme);
    setupDoubleSubmissionProtection();
    setupToastModal();
});
