// ============================================
// main.js - Authentication & UI Logic
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initBuyButtons();
    initFooterLoader();
});

// ============================================
// AUTH & NAVBAR UPDATE
// ============================================

async function initAuth() {
    // Tokenni olish (Electron API yoki localStorage orqali)
    const token = (window.api && typeof window.api.isAuthenticated === 'function')
        ? window.api.isAuthenticated()
        : Boolean(localStorage.getItem('access_token'));

    const navbarLoginItem = document.getElementById('navbar-login-item');
    const navbarUserSection = document.getElementById('navbar-user-section');
    const navbarAvatar = document.getElementById('navbar-avatar');
    const navbarName = document.getElementById('navbar-name');

    if (!token) {
        navbarLoginItem.style.display = 'block';
        navbarUserSection.style.display = 'none';
        return;
    }

    try {
        // Markaziy API wrapper orqali foydalanuvchi ma'lumotlarini olish
        const user = window.api ? await window.api.getProfile() : null;

        if (!user) {
            localStorage.removeItem('access_token');
            location.reload();
            return;
        }

        if (user && user.id) {
            navbarLoginItem.style.display = 'none';
            navbarUserSection.style.display = 'flex';
            navbarName.textContent = user.full_name || 'Profil';
            navbarAvatar.src = user.avatar || user.avatar_url || 'images/default_avatar.png';
        }
    } catch (e) {
        console.error('Auth error:', e);
        navbarLoginItem.style.display = 'block';
        navbarUserSection.style.display = 'none';
    }
}

// ============================================
// BUY BUTTON HANDLERS
// ============================================

function initBuyButtons() {
    document.querySelectorAll('.btn-buy-mini').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();

            const token = localStorage.getItem('access_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const card = e.target.closest('.product-card');
            const productName = card
                ? card.querySelector('h3').textContent.trim()
                : 'Mahsulot';

            if (confirm(`${productName} savatga qo'shilsinmi?`)) {
                alert('✅ Mahsulot savatga qo\'shildi!');
                // Kelajakda: savatga qo'shish logikasi qo'shiladi
            }
        });
    });
}

// ============================================
// FOOTER LOADER
// ============================================

function initFooterLoader() {
    const footerPlaceholder = document.getElementById('footer-placeholder');
    if (!footerPlaceholder) return;

    fetch('/static/components/footer.html')
        .then(response => {
            if (!response.ok) throw new Error('Footer yuklanmadi');
            return response.text();
        })
        .then(html => {
            footerPlaceholder.innerHTML = html;
        })
        .catch(() => {
            // Fallback footer (internet yo'q yoki xatolik bo'lsa)
            footerPlaceholder.innerHTML = `
                <footer>
                    <div class="footer-content">
                        <div class="footer-column">
                            <h4>OnlinePharmacy</h4>
                            <p>Sog'liq — eng katta boylik.</p>
                        </div>
                        <div class="footer-column">
                            <h4>Havolalar</h4>
                            <a href="/">Bosh sahifa</a>
                            <a href="/shop/products/">Mahsulotlar</a>
                            <a href="/about/">Biz haqimizda</a>
                        </div>
                        <div class="footer-column">
                            <h4>Xizmatlar</h4>
                            <a href="/contact/">Aloqa</a>
                            <a href="/faq/">FAQ</a>
                        </div>
                        <div class="footer-column">
                            <h4>Obuna</h4>
                            <div class="footer-subscribe">
                                <input type="email" placeholder="Email..." />
                                <button onclick="alert('✅ Obuna qabul qilindi!')">OK</button>
                            </div>
                        </div>
                    </div>
                    <div class="footer-bottom">
                        © 2026 OnlinePharmacy. Barcha huquqlar himoyalangan.
                    </div>
                </footer>
            `;
        });
}