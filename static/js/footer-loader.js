// Load footer component
async function loadFooter() {
    try {
        // Django static yo'li orqali yuklaymiz
        // Use the compiled static components path used elsewhere
        const response = await fetch('/static/components/footer.html');
        if (!response.ok) throw new Error('Footer fayli topilmadi');
        
        const footerHTML = await response.text();
        const placeholder = document.getElementById('footer-placeholder');
        if (placeholder) {
            placeholder.innerHTML = footerHTML;
        }
    } catch (error) {
        console.error('Footer yuklashda xatolik:', error);
    }
}

// Load footer when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadFooter);
} else {
    loadFooter();
}
