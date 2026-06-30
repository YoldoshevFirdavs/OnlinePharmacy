// templates/delivery/auth.js
/* TODO: confirm script include path */

// =============================================================================
// Konfiguratsiya va sozlanadigan o'zgaruvchilar
// =============================================================================

const AUTH_CONFIG = {
    AUTH_ENDPOINTS: {
        password: '/api/v1/admin/login/',
        otp: '/api/v1/admin/login/', // AdminLoginViewSet.login handles both request_otp and verify_otp
        telegram: '/api/v1/admin/login/',
        email_magic_link: '/api/v1/admin/login/', // Gmail magic link through credentials or dedicated email endpoint
        ip_block_notify: '/api/v1/admin/login/', // Notify via main auth action
    },
    TIMER_SETTINGS: {
        default_seconds: 240, // 4 daqiqa
        warning_seconds: 120, // 2 daqiqa qolganda sariq
        danger_seconds: 10,   // 10 soniya qolganda qizil
        colors: {
            green: '#28a745',
            yellow: '#ffc107',
            red: '#dc3545'
        }
    },
    PHONE_PATTERNS: {
        uz: {
            prefixes: ['+998', '998'],
            regex: /^\+?998\d{9}$/,
            placeholder: "+998 XX XXX XX XX",
            mask: "+998 99 999 99 99"
        },
        us: {
            prefixes: ['+1', '1'],
            regex: /^\+?1\d{10}$/,
            placeholder: "+1 (XXX) XXX-XXXX",
            mask: "+1 (999) 999-9999"
        }
    },
    SECURITY: {
        max_attempts_before_block: 5,
        block_duration_seconds: 600, // 10 minut
        max_blocks_before_ban: 5,
        ban_behavior: 'deny_all',
        field_brute_force_attempts: 5,
        field_brute_force_duration: 600, // 10 minut
    },
    DEBUG_AUTH_PAGE: false,
    I18N: {
        en: {
            login_title: "Admin Login",
            phone_label: "Phone Number",
            password_label: "Password",
            otp_request_button: "Request OTP",
            otp_verify_button: "Verify OTP",
            login_button: "Login",
            otp_sent: "OTP sent to your phone. Please enter it below.",
            otp_incorrect: "Incorrect OTP or session expired.",
            credentials_incorrect: "Invalid credentials.",
            account_locked: "Your account is temporarily locked for 10 minutes. Please try again later.",
            account_banned: "Your account has been banned. Contact support.",
            enter_otp: "Enter OTP",
            resend_otp: "Resend OTP",
            timer_prefix: "Resend in: ",
            phone_required: "Phone number is required.",
            password_required: "Password is required.",
            otp_required: "OTP is required.",
            email_required: "Email is required.",
            invalid_phone_format: "Invalid phone number format for selected country.",
            password_strength_weak: "Weak password",
            password_strength_medium: "Medium password",
            password_strength_strong: "Strong password",
            popup_title: "Enter OTP",
            popup_close: "Close",
            redirecting: "Redirecting to dashboard...",
            field_locked: "Too many failed attempts. Field is locked.",
            telegram_phone_required: "Please enter your phone number to link with Telegram.",
            telegram_admin_not_found: "Admin user not found with provided Telegram info.",
            telegram_message: "Telegram verification initiated. Check your Telegram bot.",
            email_magic_link_sent: "Magic link sent to your email.",
        },
        uz: {
            login_title: "Admin Kirish",
            phone_label: "Telefon Raqami",
            password_label: "Parol",
            otp_request_button: "OTP so'rash",
            otp_verify_button: "OTP tasdiqlash",
            login_button: "Kirish",
            otp_sent: "Telefon raqamingizga OTP yuborildi. Iltimos, quyida kiriting.",
            otp_incorrect: "Noto'g'ri OTP yoki sessiya muddati tugagan.",
            credentials_incorrect: "Noto'g'ri foydalanuvchi nomi/email yoki parol.",
            account_locked: "Sizning hisobingiz 10 minutga vaqtincha bloklangan. Keyinroq urinib ko'ring.",
            account_banned: "Sizning hisobingiz bloklangan. Qo'llab-quvvatlash xizmati bilan bog'laning.",
            enter_otp: "OTP kiriting",
            resend_otp: "OTPni qayta yuborish",
            timer_prefix: "Qayta yuborish: ",
            phone_required: "Telefon raqami majburiy.",
            password_required: "Parol majburiy.",
            otp_required: "OTP majburiy.",
            email_required: "Email majburiy.",
            invalid_phone_format: "Tanlangan davlat uchun telefon raqami formati noto'g'ri.",
            password_strength_weak: "Kuchsiz parol",
            password_strength_medium: "O'rtacha parol",
            password_strength_strong: "Kuchli parol",
            popup_title: "OTP kiriting",
            popup_close: "Yopish",
            redirecting: "Dashboardga yo'naltirilmoqda...",
            field_locked: "Bu maydon uchun juda ko'p noto'g'ri urinishlar yuz berdi. Maydon bloklandi.",
            telegram_phone_required: "Telegram bilan bog'lash uchun telefon raqamingizni kiriting.",
            telegram_admin_not_found: "Berilgan Telegram ma'lumotlari bilan admin foydalanuvchisi topilmadi.",
            telegram_message: "Telegram orqali tasdiqlash boshlandi. Telegram botni tekshiring.",
            email_magic_link_sent: "Emailingizga magic link yuborildi.",
        }
    },
    DEFAULT_LANG: 'uz',
    ADMIN_DASHBOARD_URL: '/dashboard/',
    CSRF_COOKIE_NAME: 'csrftoken',
    FINGERPRINT_LIB_URL: 'https://cdnjs.cloudflare.com/ajax/libs/fingerprintjs2/2.1.0/fingerprint2.min.js',
};

let currentLang = AUTH_CONFIG.DEFAULT_LANG;

function _(key) {
    return AUTH_CONFIG.I18N[currentLang][key] || AUTH_CONFIG.I18N[AUTH_CONFIG.DEFAULT_LANG][key] || key;
}

// =============================================================================
// Helper Functions
// =============================================================================

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function getFingerprint() {
    /* TODO: confirm fingerprint library integration details */
    if (typeof Fingerprint2 === 'undefined') {
        try {
            await loadScript(AUTH_CONFIG.FINGERPRINT_LIB_URL);
        } catch (e) {
            console.error("Fingerprint library loading failed:", e);
            return "fallback-fingerprint-" + navigator.userAgent;
        }
    }
    return new Promise(resolve => {
        try {
            Fingerprint2.get((components) => {
                const values = components.map(component => component.value);
                const hash = Fingerprint2.x64hash128(values.join(''), 31);
                resolve(hash);
            });
        } catch (err) {
            resolve("fallback-fingerprint-eval-" + navigator.userAgent);
        }
    });
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function sendRequest(url, method, data) {
    const csrftoken = getCookie(AUTH_CONFIG.CSRF_COOKIE_NAME);
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    });
}

// =============================================================================
// Security: Block and Ban Mechanisms
// =============================================================================

const BLOCK_KEY_PREFIX = 'auth_block_';
const BAN_KEY_PREFIX = 'auth_ban_';
const FIELD_BRUTE_FORCE_PREFIX = 'field_bf_';

function getBlockInfo(identifier) {
    try {
        const item = localStorage.getItem(BLOCK_KEY_PREFIX + identifier);
        if (item) return JSON.parse(item);
    } catch (e) {
        console.error(e);
    }
    return { attempts: 0, blocked_until: 0, block_count: 0 };
}

function setBlockInfo(identifier, info) {
    try {
        localStorage.setItem(BLOCK_KEY_PREFIX + identifier, JSON.stringify(info));
    } catch (e) {
        console.error(e);
    }
}

function isBlocked(identifier) {
    if (AUTH_CONFIG.DEBUG_AUTH_PAGE) return false;
    const blockInfo = getBlockInfo(identifier);
    if (blockInfo.blocked_until > Date.now()) {
        return true;
    }
    if (blockInfo.block_count >= AUTH_CONFIG.SECURITY.max_blocks_before_ban) {
        return true; // Permanent Ban state
    }
    return false;
}

function recordFailedAttempt(identifier) {
    if (AUTH_CONFIG.DEBUG_AUTH_PAGE) return;
    const blockInfo = getBlockInfo(identifier);
    blockInfo.attempts++;

    if (blockInfo.attempts >= AUTH_CONFIG.SECURITY.max_attempts_before_block) {
        blockInfo.blocked_until = Date.now() + AUTH_CONFIG.SECURITY.block_duration_seconds * 1000;
        blockInfo.attempts = 0;
        blockInfo.block_count++;
        notifyBackendOfBlock(identifier, blockInfo.block_count >= AUTH_CONFIG.SECURITY.max_blocks_before_ban);
    }
    setBlockInfo(identifier, blockInfo);
}

function resetBlock(identifier) {
    localStorage.removeItem(BLOCK_KEY_PREFIX + identifier);
}

function notifyBackendOfBlock(identifier, isPermanentBan) {
    /* TODO: confirm server-side IP block endpoint payload specifications */
    sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.ip_block_notify, 'POST', {
        action: 'notify_block',
        identifier: identifier,
        is_permanent_ban: isPermanentBan
    }).catch(error => console.error("Failed to notify backend of block:", error));
}

// Field level brute force
function getFieldBruteForceInfo(fieldId) {
    try {
        const item = localStorage.getItem(FIELD_BRUTE_FORCE_PREFIX + fieldId);
        if (item) return JSON.parse(item);
    } catch (e) {
        console.error(e);
    }
    return { attempts: 0, locked_until: 0 };
}

function setFieldBruteForceInfo(fieldId, info) {
    try {
        localStorage.setItem(FIELD_BRUTE_FORCE_PREFIX + fieldId, JSON.stringify(info));
    } catch (e) {
        console.error(e);
    }
}

function isFieldLocked(fieldId) {
    if (AUTH_CONFIG.DEBUG_AUTH_PAGE) return false;
    const info = getFieldBruteForceInfo(fieldId);
    return info.locked_until > Date.now();
}

function recordFieldFailedAttempt(fieldId) {
    if (AUTH_CONFIG.DEBUG_AUTH_PAGE) return;
    const info = getFieldBruteForceInfo(fieldId);
    info.attempts++;
    if (info.attempts >= AUTH_CONFIG.SECURITY.field_brute_force_attempts) {
        info.locked_until = Date.now() + AUTH_CONFIG.SECURITY.field_brute_force_duration * 1000;
        info.attempts = 0;
    }
    setFieldBruteForceInfo(fieldId, info);
}

function resetFieldLock(fieldId) {
    localStorage.removeItem(FIELD_BRUTE_FORCE_PREFIX + fieldId);
}

// =============================================================================
// Phone Format Logic
// =============================================================================

let phoneInput;
let selectedCountry = 'uz';

function setupPhoneInput(inputElement) {
    phoneInput = inputElement;
    if (!phoneInput) return;

    phoneInput.addEventListener('input', formatPhoneNumber);
    phoneInput.addEventListener('focus', () => {
        const pattern = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
        if (!phoneInput.value.startsWith(pattern.prefixes[0])) {
            phoneInput.value = pattern.prefixes[0];
        }
    });
}

function formatPhoneNumber() {
    const pattern = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
    let value = phoneInput.value.replace(/\D/g, '');
    const prefixDigits = pattern.prefixes[0].replace(/\D/g, '');

    if (!value.startsWith(prefixDigits)) {
        value = prefixDigits + value;
    }

    let formattedValue = pattern.prefixes[0];
    let digitIndex = prefixDigits.length;

    for (let i = pattern.prefixes[0].length; i < pattern.mask.length && digitIndex < value.length; i++) {
        if (pattern.mask[i] === '9') {
            formattedValue += value[digitIndex++];
        } else {
            formattedValue += pattern.mask[i];
        }
    }
    phoneInput.value = formattedValue;
}

// Validation logic helper
function validatePhoneNumber(phoneNumber) {
    const cleanNum = phoneNumber.replace(/\s+/g, '');
    const pattern = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
    return pattern.regex.test(cleanNum);
}

// =============================================================================
// Countdown Timer
// =============================================================================

let timerInterval;
let timerSeconds = 0;
let timerDisplayElement;
let resendOtpButton;

function startTimer(duration, displayElement, buttonElement) {
    timerSeconds = duration;
    timerDisplayElement = displayElement;
    resendOtpButton = buttonElement;

    if (timerInterval) {
        clearInterval(timerInterval);
    }

    if (resendOtpButton) {
        resendOtpButton.disabled = true;
        resendOtpButton.style.opacity = '0.5';
    }

    function updateTimer() {
        if (timerSeconds <= 0) {
            clearInterval(timerInterval);
            if (resendOtpButton) {
                resendOtpButton.disabled = false;
                resendOtpButton.style.opacity = '1';
            }
            if (timerDisplayElement) {
                timerDisplayElement.textContent = "";
            }
            return;
        }

        let minutes = Math.floor(timerSeconds / 60);
        let seconds = timerSeconds % 60;
        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        if (timerDisplayElement) {
            timerDisplayElement.textContent = `${_('timer_prefix')}${minutes}:${seconds}`;

            if (timerSeconds <= AUTH_CONFIG.TIMER_SETTINGS.danger_seconds) {
                timerDisplayElement.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
            } else if (timerSeconds <= AUTH_CONFIG.TIMER_SETTINGS.warning_seconds) {
                timerDisplayElement.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.yellow;
            } else {
                timerDisplayElement.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.green;
            }
        }
        timerSeconds--;
    }

    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);
}

// =============================================================================
// Popup Logic
// =============================================================================

let otpPopup;
let currentSessionId = null;

function createOtpPopup() {
    let existingPopup = document.getElementById('otp-popup');
    if (existingPopup) {
        otpPopup = existingPopup;
        return;
    }

    otpPopup = document.createElement('div');
    otpPopup.id = 'otp-popup';
    otpPopup.className = 'otp-popup-overlay';
    otpPopup.style.display = 'none';
    otpPopup.innerHTML = `
        <div class="otp-popup-content">
            <span class="otp-popup-close" id="otp-popup-close-btn">&times;</span>
            <h2 class="otp-popup-title">${_('popup_title')}</h2>
            <p id="otp-message" style="margin: 10px 0; font-size: 14px; color: #555;"></p>
            <input type="text" id="otp-popup-input" class="form-control" placeholder="${_('enter_otp')}" maxlength="6" style="text-align: center; font-size: 20px; letter-spacing: 5px; margin: 15px 0;">
            <div class="otp-timer-container" style="margin: 10px 0;">
                <span id="otp-timer-display" style="font-weight: bold;"></span>
                <button id="otp-popup-resend-btn" class="btn btn-link" disabled style="display: block; margin: 10px auto;">${_('resend_otp')}</button>
            </div>
            <button id="otp-popup-verify-btn" class="btn btn-primary mt-3" style="width: 100%; padding: 10px; background: #6a00f4; border: none; border-radius: 5px; color: white;">${_('otp_verify_button')}</button>
        </div>
    `;
    document.body.appendChild(otpPopup);

    document.getElementById('otp-popup-close-btn').addEventListener('click', hideOtpPopup);
    document.getElementById('otp-popup-verify-btn').addEventListener('click', handleOtpVerification);
    document.getElementById('otp-popup-resend-btn').addEventListener('click', handleOtpResend);

    if (localStorage.getItem('showOtpPopup') === 'true' && localStorage.getItem('currentSessionId')) {
        currentSessionId = localStorage.getItem('currentSessionId');
        showOtpPopup(_('otp_sent'), currentSessionId);
    }
}

function showOtpPopup(message, sessionId) {
    document.body.classList.add('no-scroll');
    otpPopup.style.display = 'flex';
    document.getElementById('otp-message').textContent = message;
    currentSessionId = sessionId;
    localStorage.setItem('showOtpPopup', 'true');
    localStorage.setItem('currentSessionId', sessionId);

    const display = document.getElementById('otp-timer-display');
    const resendBtn = document.getElementById('otp-popup-resend-btn');
    startTimer(AUTH_CONFIG.TIMER_SETTINGS.default_seconds, display, resendBtn);
}

function hideOtpPopup() {
    document.body.classList.remove('no-scroll');
    otpPopup.style.display = 'none';
    localStorage.removeItem('showOtpPopup');
    localStorage.removeItem('currentSessionId');
    if (timerInterval) {
        clearInterval(timerInterval);
    }
}

async function handleOtpVerification() {
    const otpInputVal = document.getElementById('otp-popup-input').value.trim();
    const phoneVal = phoneInput ? phoneInput.value.replace(/\s+/g, '') : '';

    if (!otpInputVal) {
        alert(_('otp_required'));
        return;
    }

    if (isFieldLocked('otp_input')) {
        alert(_('field_locked'));
        return;
    }

    try {
        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.otp, 'POST', {
            action: 'verify_otp',
            phone_number: phoneVal,
            otp: otpInputVal,
            session_id: currentSessionId,
            fingerprint: await getFingerprint()
        });

        if (response.success || response.redirect) {
            hideOtpPopup();
            resetBlock(phoneVal);
            resetFieldLock('otp_input');
            showSuccessAnimationAndRedirect();
        } else {
            alert(response.message || _('otp_incorrect'));
            recordFailedAttempt(phoneVal);
            recordFieldFailedAttempt('otp_input');
        }
    } catch (error) {
        alert(error.message || _('otp_incorrect'));
        recordFailedAttempt(phoneVal);
        recordFieldFailedAttempt('otp_input');
    }
}

async function handleOtpResend() {
    const phoneVal = phoneInput ? phoneInput.value.replace(/\s+/g, '') : '';
    if (!phoneVal) {
        alert(_('phone_required'));
        return;
    }

    if (isBlocked(phoneVal)) {
        alert(_('account_locked'));
        return;
    }

    try {
        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.otp, 'POST', {
            action: 'request_otp',
            phone_number: phoneVal,
            fingerprint: await getFingerprint()
        });
        if (response.session_id) {
            currentSessionId = response.session_id;
            localStorage.setItem('currentSessionId', currentSessionId);
            showOtpPopup(_('otp_sent'), currentSessionId);
        } else {
            alert(response.message || "Error requesting OTP.");
            recordFailedAttempt(phoneVal);
        }
    } catch (e) {
        alert(e.message || "Error requesting OTP.");
        recordFailedAttempt(phoneVal);
    }
}

// =============================================================================
// Gmail & Telegram Frontend Flows
// =============================================================================

/* TODO: confirm email magic link endpoint functionality */
async function handleGmailLogin(emailVal) {
    if (!emailVal) {
        alert(_('email_required'));
        return;
    }

    if (isBlocked(emailVal) || isFieldLocked('email_input')) {
        alert(_('account_locked'));
        return;
    }

    try {
        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.email_magic_link, 'POST', {
            action: 'email_magic_link',
            email: emailVal,
            fingerprint: await getFingerprint()
        });
        alert(response.message || _('email_magic_link_sent'));
    } catch (error) {
        alert(error.message || "Gmail error");
        recordFailedAttempt(emailVal);
        recordFieldFailedAttempt('email_input');
    }
}

async function handleTelegramLogin(phoneVal) {
    if (!phoneVal) {
        alert(_('phone_required'));
        return;
    }

    if (isBlocked(phoneVal) || isFieldLocked('phone_input')) {
        alert(_('account_locked'));
        return;
    }

    try {
        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.telegram, 'POST', {
            action: 'telegram',
            phone_number: phoneVal,
            fingerprint: await getFingerprint()
        });

        if (response.require_phone) {
            alert(_('telegram_phone_required'));
        } else if (response.deeplink) {
            window.open(response.deeplink, '_blank');
            if (response.session_id) {
                showOtpPopup(_('telegram_message'), response.session_id);
            }
        } else {
            alert(response.message || _('telegram_admin_not_found'));
        }
    } catch (error) {
        alert(error.message || "Telegram error");
        recordFailedAttempt(phoneVal);
        recordFieldFailedAttempt('phone_input');
    }
}

// Handle Telegram URL callback redirect /check?session_id=...&otp=...
async function handleTelegramCallback() {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const otpCode = params.get('otp');

    if (sessionId && otpCode) {
        const fingerprintVal = await getFingerprint();
        try {
            const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.otp, 'POST', {
                action: 'verify_otp',
                session_id: sessionId,
                otp: otpCode,
                fingerprint: fingerprintVal
            });
            if (response.success || response.redirect) {
                showSuccessAnimationAndRedirect();
            }
        } catch (e) {
            console.error("Telegram callback verification failed:", e);
        }
    }
}

// =============================================================================
// Success Animation and Redirection
// =============================================================================

function showSuccessAnimationAndRedirect() {
    const successOverlay = document.createElement('div');
    successOverlay.className = 'auth-success-overlay';
    successOverlay.style.position = 'fixed';
    successOverlay.style.top = '0';
    successOverlay.style.left = '0';
    successOverlay.style.width = '100%';
    successOverlay.style.height = '100%';
    successOverlay.style.background = 'rgba(0, 0, 0, 0.8)';
    successOverlay.style.display = 'flex';
    successOverlay.style.alignItems = 'center';
    successOverlay.style.justifyContent = 'center';
    successOverlay.style.zIndex = '9999';

    successOverlay.innerHTML = `
        <div class="auth-success-content" style="text-align: center; color: white;">
            <div class="auth-success-animation">
                <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52" style="width: 80px; height: 80px; margin: 0 auto 20px;">
                    <circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none" stroke="#28a745" stroke-width="4"/>
                    <path class="checkmark__check" fill="none" stroke="#28a745" stroke-width="4" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                </svg>
                <div class="arrow-animation" style="position: relative; width: 40px; height: 40px; margin: 10px auto; border-right: 4px solid #b084f4; border-top: 4px solid #b084f4; border-radius: 0 50% 0 0; transform: rotate(45deg); animation: curve-arrow-spin 1.5s ease-in-out infinite;"></div>
            </div>
            <p style="font-size: 18px; font-weight: bold;">${_('redirecting')}</p>
        </div>
    `;

    // Append animation keyframes dynamically
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes curve-arrow-spin {
            0% { transform: rotate(0deg) scale(0.8); opacity: 0.3; }
            50% { transform: rotate(180deg) scale(1.2); opacity: 1; }
            100% { transform: rotate(360deg) scale(0.8); opacity: 0.3; }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(successOverlay);
    document.body.classList.add('no-scroll');

    setTimeout(() => {
        window.location.href = AUTH_CONFIG.ADMIN_DASHBOARD_URL;
    }, 2000);
}

// =============================================================================
// DOM Elements Setup and Events Initialization
// =============================================================================

function initAuthPage() {
    createOtpPopup();

    const authForm = document.getElementById('auth-form') || document.getElementById('admin-login-form');
    const phoneInputEl = document.getElementById('phone') || document.getElementById('phone-number-input');
    const countrySelectorWrapper = document.getElementById('selected-country') || document.getElementById('country-selector');

    // Load admin fields if present (Admin login change fields support)
    const emailInputEl = document.getElementById('email') || document.getElementById('email-input');
    const passwordInputEl = document.getElementById('password') || document.getElementById('password-input');
    const currentPassEl = document.getElementById('current-password');
    const newPassEl = document.getElementById('new-password');
    const confirmNewPassEl = document.getElementById('confirm-new-password');

    if (phoneInputEl) {
        setupPhoneInput(phoneInputEl);
    }

    // Country Selector rendering flag + prefix only, larger elements
    if (countrySelectorWrapper) {
        const countryDropdown = document.getElementById('country-dropdown');
        const countryList = document.getElementById('country-list');

        // Styles for larger elements
        const flagStyle = 'font-size: 24px; margin-right: 8px; vertical-align: middle;';
        const prefixStyle = 'font-size: 18px; font-weight: bold; vertical-align: middle;';

        countrySelectorWrapper.style.padding = '8px 12px';
        countrySelectorWrapper.style.cursor = 'pointer';

        if (countryDropdown && countryList) {
            countryList.innerHTML = '';
            for (const countryCode in AUTH_CONFIG.PHONE_PATTERNS) {
                const pattern = AUTH_CONFIG.PHONE_PATTERNS[countryCode];
                const countryItem = document.createElement('div');
                countryItem.className = 'country-item';
                countryItem.style.padding = '10px';
                countryItem.style.cursor = 'pointer';
                countryItem.style.display = 'flex';
                countryItem.style.alignItems = 'center';

                // Uzbek flag fi-uz, US flag fi-us
                const flagClass = countryCode === 'uz' ? 'uz' : 'us';
                countryItem.innerHTML = `
                    <span class="flag-icon fi fi-${flagClass}" style="${flagStyle}"></span>
                    <span class="dial-code" style="${prefixStyle}">${pattern.prefixes[0]}</span>
                `;
                countryItem.addEventListener('click', () => {
                    selectedCountry = countryCode;
                    const flagEl = countrySelectorWrapper.querySelector('.flag-icon');
                    if (flagEl) {
                        flagEl.className = `flag-icon fi fi-${flagClass}`;
                    }
                    const codeEl = countrySelectorWrapper.querySelector('.dial-code');
                    if (codeEl) {
                        codeEl.textContent = pattern.prefixes[0];
                    }
                    countryDropdown.classList.add('hidden');
                    if (phoneInputEl) {
                        phoneInputEl.value = pattern.prefixes[0];
                        phoneInputEl.placeholder = pattern.placeholder;
                        phoneInputEl.maxLength = countryCode === 'uz' ? 9 : 14;
                    }
                });
                countryList.appendChild(countryItem);
            }

            countrySelectorWrapper.addEventListener('click', (e) => {
                e.stopPropagation();
                countryDropdown.classList.toggle('hidden');
            });

            document.addEventListener('click', () => {
                countryDropdown.classList.add('hidden');
            });
        }
    }

    // Intercept Code Retrieval / Get Code Button Event (Prevent page refresh)
    const getCodeBtn = document.getElementById('get-code-btn') || document.getElementById('request-otp-button');
    if (getCodeBtn) {
        getCodeBtn.addEventListener('click', async (event) => {
            event.preventDefault();
            const phoneVal = phoneInputEl ? phoneInputEl.value.replace(/\s+/g, '') : '';

            if (!phoneVal) {
                alert(_('phone_required'));
                return;
            }

            if (isBlocked(phoneVal)) {
                alert(_('account_locked'));
                return;
            }

            if (isFieldLocked('phone')) {
                alert(_('field_locked'));
                return;
            }

            if (!validatePhoneNumber(phoneVal)) {
                alert(_('invalid_phone_format'));
                recordFieldFailedAttempt('phone');
                return;
            }

            try {
                const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.otp, 'POST', {
                    action: 'request_otp',
                    phone_number: phoneVal,
                    fingerprint: await getFingerprint()
                });

                if (response.session_id) {
                    resetFieldLock('phone');
                    showOtpPopup(_('otp_sent'), response.session_id);
                } else {
                    alert(response.message || "Error requesting code.");
                    recordFailedAttempt(phoneVal);
                    recordFieldFailedAttempt('phone');
                }
            } catch (err) {
                alert(err.message || "Error requesting code.");
                recordFailedAttempt(phoneVal);
                recordFieldFailedAttempt('phone');
            }
        });
    }

    // Form submission for credentials login (Password flow)
    if (authForm) {
        authForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const emailVal = emailInputEl ? emailInputEl.value.trim() : '';
            const phoneVal = phoneInputEl ? phoneInputEl.value.replace(/\s+/g, '') : '';
            const passwordVal = passwordInputEl ? passwordInputEl.value.trim() : '';
            const currentPassword = currentPassEl ? currentPassEl.value.trim() : '';
            const newPassword = newPassEl ? newPassEl.value.trim() : '';
            const confirmNewPassword = confirmNewPassEl ? confirmNewPassEl.value.trim() : '';

            const identifier = phoneVal || emailVal;

            if (!identifier) {
                alert(_('phone_required'));
                return;
            }

            if (isBlocked(identifier)) {
                alert(_('account_locked'));
                return;
            }

            const payload = {
                action: 'credentials',
                phone_number: phoneVal,
                email: emailVal,
                password: passwordVal,
                fingerprint: await getFingerprint()
            };

            // Support fields if new password update is included
            if (currentPassword && newPassword && confirmNewPassword) {
                payload.current_password = currentPassword;
                payload.new_password = newPassword;
                payload.confirm_new_password = confirmNewPassword;
            }

            try {
                const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.password, 'POST', payload);
                if (response.success || response.redirect) {
                    resetBlock(identifier);
                    showSuccessAnimationAndRedirect();
                } else {
                    alert(response.message || _('credentials_incorrect'));
                    recordFailedAttempt(identifier);
                }
            } catch (e) {
                alert(e.message || _('credentials_incorrect'));
                recordFailedAttempt(identifier);
            }
        });
    }

    // Gmail & Telegram buttons binding
    const gmailBtn = document.getElementById('gmail-login-btn');
    if (gmailBtn) {
        gmailBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const emailVal = emailInputEl ? emailInputEl.value.trim() : '';
            handleGmailLogin(emailVal);
        });
    }

    const telegramBtn = document.getElementById('telegram-login-btn');
    if (telegramBtn) {
        telegramBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const phoneVal = phoneInputEl ? phoneInputEl.value.replace(/\s+/g, '') : '';
            handleTelegramLogin(phoneVal);
        });
    }

    handleTelegramCallback();
}

document.addEventListener('DOMContentLoaded', initAuthPage);
