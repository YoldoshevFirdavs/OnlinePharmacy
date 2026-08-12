class Settings {
    constructor() {
        this.settings = this.loadSettings();
        this.init();
    }

    loadSettings() {
        const stored = localStorage.getItem('user_settings');
        return stored ? JSON.parse(stored) : {
            language: 'uz',
            darkMode: false,
            timezone: 'Asia/Tashkent',
            marketing: true
        };
    }

    saveSettings() {
        localStorage.setItem('user_settings', JSON.stringify(this.settings));
        console.log('Settings saved:', this.settings);
    }

    init() {
        this.setupTabNavigation();
        this.loadSettingsUI();
    }

    setupTabNavigation() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabId = btn.dataset.tab;
                this.showTab(tabId);
            });
        });
    }

    showTab(tabId) {
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

        document.getElementById(tabId).classList.add('active');
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    }

    loadSettingsUI() {
        document.getElementById('language').value = this.settings.language;
        document.getElementById('timezone').value = this.settings.timezone;

        if (this.settings.darkMode) {
            document.getElementById('dark-mode').classList.add('active');
        }
    }
}

function toggleSetting(id) {
    const btn = document.getElementById(id);
    btn.classList.toggle('active');
}

function toggleDarkMode() {
    document.getElementById('dark-mode').classList.toggle('active');
    const isDark = document.getElementById('dark-mode').classList.contains('active');
    document.body.style.background = isDark ? '#1f2937' : 'var(--gray-100)';
}

function saveSetting(key, value) {
    const settings = JSON.parse(localStorage.getItem('user_settings') || '{}');
    settings[key] = value;
    localStorage.setItem('user_settings', JSON.stringify(settings));
    console.log('Setting saved:', key, value);
}

function saveAll() {
    const settings = {
        language: document.getElementById('language').value,
        timezone: document.getElementById('timezone').value,
        darkMode: document.getElementById('dark-mode').classList.contains('active'),
        marketingEmails: document.getElementById('marketing-emails').classList.contains('active'),
        orderEmails: document.getElementById('order-email').classList.contains('active'),
        newProducts: document.getElementById('new-products-email').classList.contains('active'),
        specialOffers: document.getElementById('special-offers-email').classList.contains('active'),
        orderPush: document.getElementById('order-push').classList.contains('active'),
        messagePush: document.getElementById('message-push').classList.contains('active'),
        smsNotifications: document.getElementById('sms-notifications').classList.contains('active'),
        twoFactor: document.getElementById('two-factor').classList.contains('active')
    };

    localStorage.setItem('user_settings', JSON.stringify(settings));
    document.getElementById('success-msg').classList.add('show');
    document.getElementById('success-msg2').classList.add('show');

    setTimeout(() => {
        document.getElementById('success-msg').classList.remove('show');
        document.getElementById('success-msg2').classList.remove('show');
    }, 2000);

    console.log('All settings saved:', settings);
}

function resetPassword() {
    if (confirm('Parolni yangilashni tasdiqlaysizmi?')) {
        alert('Parol yangilash linki email orqali yuborildi!');
    }
}

function deleteAccount() {
    if (confirm('Akkauntni o\'chirilsinmi? Bu amalni qaytarib bo\'lmaydi!')) {
        if (confirm('Rostdan ham o\'chirilsinmi?')) {
            localStorage.clear();
            alert('Akkaunt o\'chirildi!');
            window.location.href = '/auth/';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Settings();
});