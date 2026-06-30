// footer.js - Footer Component Logic
// Newsletter validation and loading

async function loadFooter() {
    // If not using Django templates, we might need to fetch it.
    // But the requirement says use {% include %}, which means Django renders it.
    // So this script will only handle logic.
    initFooterLogic();
}

function initFooterLogic() {
    const form = document.getElementById('newsletter-form');
    const message = document.getElementById('newsletter-message');
    
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('newsletter-email');
            const email = emailInput.value.trim();
            
            // Simple validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            if (!emailRegex.test(email)) {
                showMessage('Iltimos, to\'g\'ri email manzili kiriting.', 'error');
                return;
            }
            
            // Success simulation
            showMessage('Rahmat! Siz muvaffaqiyatli obuna bo\'ldingiz ✅', 'success');
            emailInput.value = '';
            
            // Here you would normally send data to API
            // fetch('/api/v1/newsletter/subscribe/', { method: 'POST', ... })
        });
    }
}

function showMessage(text, type) {
    const message = document.getElementById('newsletter-message');
    if (!message) return;
    
    message.textContent = text;
    message.style.display = 'block';
    message.style.color = type === 'success' ? '#48bb78' : '#f56565';
    
    setTimeout(() => {
        message.style.display = 'none';
    }, 5000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFooterLogic);
} else {
    initFooterLogic();
}
