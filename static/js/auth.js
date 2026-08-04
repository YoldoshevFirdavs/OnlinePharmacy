// static/js/auth.js
import { getCookie, sendRequest, getFingerprint } from './utils.js';

// =============================================================================
// Konfiguratsiya va sozlanadigan o'zgaruvchilar
// =============================================================================

const AUTH_CONFIG = {
    AUTH_ENDPOINTS: {
        admin_login:          '/api/v1/users/admin/login/',      // AdminLoginViewSet — action: credentials/request_otp/verify_otp/telegram
        user_email_login:     '/api/v1/users/login/email/',      // EmailLoginView
        user_telegram_login:  '/api/v1/users/login/telegram/',   // TelegramLoginView
        user_verify_otp:      '/api/v1/users/login/verify-otp/', // VerifyOtpView
        admin_verify_otp:     '/api/v1/users/admin/login/verify-otp/', // AdminLoginViewSet - verify_otp action (new endpoint)
        determine_role:       '/api/v1/users/determine_role/',   // DetermineRoleView
        logout:               '/api/v1/users/logout/',           // LogoutView
        logout_jwt:           '/api/v1/users/logout/jwt/'        // LogoutJWTView
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
        // These will be dynamically loaded from countries.json
    },
    ENABLE_BLOCKING: true, // AUTH_BLOCK_USER=True/False ga mos keladi. Backend tomonidan o'rnatilishi kerak.
    SECURITY: {
        max_attempts_before_block: 5,
        block_duration_seconds: 600, // 10 minut
        field_brute_force_attempts: 5,
        field_brute_force_duration: 600, // 10 minut
    },
    DEBUG_AUTH_PAGE: true, // Set to true for debugging, false for production
    I18N: {
        en: {
            login_title: "Admin Login",
            phone_label: "Phone Number",
            otp_request_button: "Request OTP",
            otp_verify_button: "Verify OTP",
            login_button: "Login",
            otp_sent: "OTP sent. Please enter it below.",
            otp_incorrect: "Incorrect OTP or session expired.",
            credentials_incorrect: "Invalid credentials.",
            account_locked: "Your account is temporarily locked for 10 minutes. Please try again later.",
            enter_otp: "Enter OTP",
            resend_otp: "Resend OTP",
            timer_prefix: "Resend in: ",
            phone_required: "Phone number is required.",
            otp_required: "OTP is required.",
            email_required: "Email is required.",
            invalid_phone_format: "Invalid phone number format.",
            popup_title: "Enter OTP",
            popup_close: "Close",
            redirecting: "Redirecting to dashboard...",
            field_locked: "Too many failed attempts. Field is locked.",
            telegram_phone_required: "Please enter your phone number to link with Telegram.",
            telegram_admin_not_found: "Admin user not found with provided Telegram info.",
            telegram_message: "Telegram verification initiated. Check your Telegram bot.",
            email_magic_link_sent: "Magic link sent to your email.",
            invalid_prefix: "Invalid country code. Please enter a valid prefix like +998 or +1.",
            phone_number_not_found: "Phone number not found or invalid.",
            gmail_login_error: "Problem with Gmail login.",
            telegram_login_error: "Problem with Telegram login.",
            error_requesting_otp: "Error requesting OTP.",
            no_such_number: "Bunday raqam topilmadi.",
            name_required: "Ismni kiriting.",
            password_required: "Parol majburiy.",
            login_with_password: "Parol bilan kirish",
            login_with_otp: "OTP bilan kirish",
            login_failed_try_again: "Login failed, please try again.",
            otp_session_expired: "OTP session has expired. Please request a new one."
        },
        uz: {
            login_title: "Admin Kirish",
            phone_label: "Telefon Raqami",
            otp_request_button: "OTP so'rash",
            otp_verify_button: "OTP tasdiqlash",
            login_button: "Kirish",
            otp_sent: "OTP yuborildi. Iltimos, quyida kiriting.",
            otp_incorrect: "Noto'g'ri OTP yoki sessiya muddati tugagan.",
            credentials_incorrect: "Noto'g'ri foydalanuvchi nomi/email yoki parol.",
            account_locked: "Sizning hisobingiz 10 minutga vaqtincha bloklangan. Keyinroq urinib ko'ring.",
            enter_otp: "OTP kiriting",
            resend_otp: "OTPni qayta yuborish",
            timer_prefix: "Qayta yuborish: ",
            phone_required: "Telefon raqami majburiy.",
            otp_required: "OTP majburiy.",
            email_required: "Email majburiy.",
            invalid_phone_format: "Telefon raqami formati noto'g'ri.",
            popup_title: "OTP kiriting",
            popup_close: "Yopish",
            redirecting: "Dashboardga yo'naltirilmoqda...",
            field_locked: "Bu maydon uchun juda ko'p noto'g'ri urinishlar yuz berdi. Maydon bloklandi.",
            telegram_phone_required: "Telegram bilan bog'lash uchun telefon raqamingizni kiriting.",
            telegram_admin_not_found: "Berilgan Telegram ma'lumotlari bilan admin foydalanuvchisi topilmadi.",
            telegram_message: "Telegram orqali tasdiqlash boshlandi. Telegram botni tekshiring.",
            email_magic_link_sent: "Emailingizga magic link yuborildi.",
            invalid_prefix: "Bunday davlat raqami mavjud emas. Iltimos, +998 yoki +1 kabi to'g'ri prefiks kiriting.",
            phone_number_not_found: "Telefon raqami topilmadi yoki noto'g'ri.",
            gmail_login_error: "Gmail orqali ro'yxatdan o'tishda muammo bor.",
            telegram_login_error: "Telegram orqali ro'yxatdan o'tishda muammo bor.",
            error_requesting_otp: "OTP so'rashda xato yuz berdi.",
            no_such_number: "Bunday raqam topilmadi.",
            name_required: "Ismni kiriting.",
            password_required: "Parol majburiy.",
            login_with_password: "Parol bilan kirish",
            login_with_otp: "OTP bilan kirish",
            login_failed_try_again: "Kirish amalga oshmadi, iltimos qayta urinib ko'ring.",
            otp_session_expired: "OTP sessiyasi muddati tugadi. Iltimos, yangi OTP so‘rang."
        }
    },
    DEFAULT_LANG: 'uz',
    ADMIN_DASHBOARD_URL: '/dashboard/admin/',
    AUTH_PAGE_URL: '/auth/',
    TELEGRAM_BOT_USERNAME: 'authversabot' // Telegram bot username here
};

let currentLang = localStorage.getItem('user_lang') || AUTH_CONFIG.DEFAULT_LANG;

function _(key) {
    return AUTH_CONFIG.I18N[currentLang][key] || AUTH_CONFIG.I18N[AUTH_CONFIG.DEFAULT_LANG][key] || key;
}

// =============================================================================
// Error Handling
// =============================================================================

function showErrorBanner(message) {
    const errorBanner = document.getElementById('auth-error-banner');
    if (errorBanner) { // Always show error banner if it exists
        errorBanner.textContent = message;
        errorBanner.style.display = 'block';
        setTimeout(() => {
            errorBanner.style.display = 'none';
        }, 5000);
    } else {
        console.error("Authentication Error:", message);
    }
}

// =============================================================================
// Security: Block and Ban Mechanisms
// =============================================================================

const BLOCK_KEY_PREFIX = 'auth_block_';
const FIELD_BRUTE_FORCE_PREFIX = 'field_bf_';

function getBlockInfo(identifier) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return { attempts: 0, blocked_until: 0, block_count: 0 };
    try {
        const item = localStorage.getItem(BLOCK_KEY_PREFIX + identifier);
        if (item) return JSON.parse(item);
    } catch (e) {
        console.error(e);
    }
    return { attempts: 0, blocked_until: 0, block_count: 0 };
}

function setBlockInfo(identifier, info) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return;
    try {
        localStorage.setItem(BLOCK_KEY_PREFIX + identifier, JSON.stringify(info));
    }  catch (e) {
        console.error(e);
    }
}

function isBlocked(identifier) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING || AUTH_CONFIG.DEBUG_AUTH_PAGE) return false;
    const blockInfo = getBlockInfo(identifier);
    return blockInfo.blocked_until > Date.now();
}

function recordFailedAttempt(identifier) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING || AUTH_CONFIG.DEBUG_AUTH_PAGE) return;
    const blockInfo = getBlockInfo(identifier);
    blockInfo.attempts++;

    if (blockInfo.attempts >= AUTH_CONFIG.SECURITY.max_attempts_before_block) {
        blockInfo.blocked_until = Date.now() + AUTH_CONFIG.SECURITY.block_duration_seconds * 1000;
        blockInfo.attempts = 0;
    }
    setBlockInfo(identifier, blockInfo);
}

function resetBlock(identifier) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return;
    localStorage.removeItem(BLOCK_KEY_PREFIX + identifier);
}

function getFieldBruteForceInfo(fieldId) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return { attempts: 0, locked_until: 0 };
    try {
        const item = localStorage.getItem(FIELD_BRUTE_FORCE_PREFIX + fieldId);
        if (item) return JSON.parse(item);
    } catch (e) {
        console.error(e);
    }
    return { attempts: 0, locked_until: 0 };
}

function setFieldBruteForceInfo(fieldId, info) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return;
    try {
        localStorage.setItem(FIELD_BRUTE_FORCE_PREFIX + fieldId, JSON.stringify(info));
    } catch (e) {
        console.error(e);
    }
}

function isFieldLocked(fieldId) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING || AUTH_CONFIG.DEBUG_AUTH_PAGE) return false;
    const info = getFieldBruteForceInfo(fieldId);
    return info.locked_until > Date.now();
}

function recordFieldFailedAttempt(fieldId) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING || AUTH_CONFIG.DEBUG_AUTH_PAGE) return;
    const info = getFieldBruteForceInfo(fieldId);
    info.attempts++;
    if (info.attempts >= AUTH_CONFIG.SECURITY.field_brute_force_attempts) {
        info.locked_until = Date.now() + AUTH_CONFIG.SECURITY.block_duration_seconds * 1000;
        info.attempts = 0;
    }
    setFieldBruteForceInfo(fieldId, info);
}

function resetFieldLock(fieldId) {
    if (!AUTH_CONFIG.ENABLE_BLOCKING) return;
    localStorage.removeItem(FIELD_BRUTE_FORCE_PREFIX + fieldId);
}

// =============================================================================
// Phone Format Logic & Country Selector
// =============================================================================

let phoneInput;
let countryPrefixInput;
let selectedCountry = 'uz'; // Default country
let phoneErrorMessage;
let countryDropdown;
let countryList;

// Updated SUPPORTED_COUNTRIES to match the new country.json structure
const SUPPORTED_COUNTRIES = [
    "uz", "us", "ru", "uk", "de", "fr", "tr", "in", "cn", "jp", "kr", "ae", "sa", "eg", "br", "ca", "au", "it", "es", "pl", "nl", "se", "no", "dk", "fi", "kz", "ua", "by", "az", "kg", "tj", "tm"
];

// Function to load countries data
async function loadCountriesData() {
    try {
        const response = await fetch('/static/data/country.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const countriesArray = await response.json();
        AUTH_CONFIG.PHONE_PATTERNS = {}; // Clear existing patterns
        countriesArray.forEach(countryData => {
            const countryCode = countryData.code.toLowerCase();
            if (SUPPORTED_COUNTRIES.includes(countryCode)) {
                AUTH_CONFIG.PHONE_PATTERNS[countryCode] = {
                    prefixes: [countryData.dial_code],
                    // Assuming a default mask if not provided, or derive from dial_code length
                    regex: new RegExp(`^\\${countryData.dial_code}\\d{${countryData.phone_format.replace(/[^#]/g, '').length}}$`),
                    placeholder: countryData.phone_format,
                    mask: countryData.phone_format,
                    flag: countryCode
                };
            }
        });
    } catch (error) {
        console.error("Failed to load countries data:", error);
    }
}

function updateCountryDisplay(countryCode) {
    const flagImg = document.querySelector('#country-selector .flag-icon');
    if (flagImg) {
        flagImg.src = `/static/flags/1x1/${countryCode}.svg`;
        flagImg.alt = `${countryCode.toUpperCase()} Flag`;
    }
    const countryData = AUTH_CONFIG.PHONE_PATTERNS[countryCode];
    if (countryPrefixInput && countryData) {
        countryPrefixInput.value = countryData.prefixes[0];
    }
    if (phoneInput && countryData) {
        phoneInput.placeholder = countryData.phone_format;
        // MaxLengthni maskdagi raqamlar soniga qarab belgilash
        phoneInput.maxLength = countryData.mask.replace(/[^#]/g, '').length + (countryData.mask.length - countryData.mask.replace(/[^#]/g, '').length);
    }
    formatPhoneNumber(); // Yangi mamlakat tanlanganda raqamni qayta formatlash
}

function clearPhoneError() {
    if (phoneErrorMessage) {
        phoneErrorMessage.textContent = '';
    }
}

function handlePrefixChange() {
    let prefix = countryPrefixInput.value.trim();
    let matchedCountry = null;

    // Prefixni to'g'ri formatlash (faqat raqamlar va '+' belgisi)
    prefix = '+' + prefix.replace(/\D/g, '');
    countryPrefixInput.value = prefix;

    for (const countryCode in AUTH_CONFIG.PHONE_PATTERNS) {
        const pattern = AUTH_CONFIG.PHONE_PATTERNS[countryCode];
        if (pattern.prefixes.includes(prefix)) {
            matchedCountry = countryCode;
            break;
        }
    }

    if (matchedCountry) {
        selectedCountry = matchedCountry;
        updateCountryDisplay(selectedCountry);
        clearPhoneError();
    } else {
        let partialMatch = false;
        for (const countryCode in AUTH_CONFIG.PHONE_PATTERNS) {
            const pattern = AUTH_CONFIG.PHONE_PATTERNS[countryCode];
            if (pattern.prefixes.some(p => p.startsWith(prefix))) {
                partialMatch = true;
                break;
            }
        }

        if (!partialMatch && prefix.length > 1) {
            if (phoneErrorMessage) phoneErrorMessage.textContent = _('invalid_prefix');
        } else {
            clearPhoneError();
        }
        // Agar prefix to'liq mos kelmasa, lekin qisman mos kelsa, bayroqni o'zgartirmaymiz
        // Agar umuman mos kelmasa, defaultga qaytaramiz yoki hozirgi holatni saqlaymiz
        // Hozircha, agar to'liq mos kelmasa, bayroqni o'zgartirmaymiz
    }
}

function formatPhoneNumber() {
    const pattern = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
    if (!pattern) return;

    let value = phoneInput.value.replace(/\D/g, ''); // Faqat raqamlarni olamiz

    let formattedValue = '';
    let digitIndex = 0;

    const mask = pattern.mask;
    for (let i = 0; i < mask.length && digitIndex < value.length; i++) {
        if (mask[i] === '#') { // '#' raqam uchun joy belgilaydi
            formattedValue += value[digitIndex++];
        } else if (/\d/.test(mask[i])) { // Agar maskdagi belgi raqam bo'lsa (masalan, 800-555-1234 dagi 800)
            formattedValue += mask[i];
        } else { // Boshqa belgilar (bo'sh joy, defis, qavs)
            formattedValue += mask[i];
        }
    }
    phoneInput.value = formattedValue;
}

function validatePhoneNumber(phoneNumber) {
    const countryData = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
    if (!countryData || !countryData.regex) {
        console.warn(`No regex found for country ${selectedCountry}`);
        return false;
    }
    const cleanNum = countryPrefixInput.value + phoneNumber.replace(/\s+/g, '');
    return countryData.regex.test(cleanNum);
}

function setupPhoneInputAndCountrySelector() {
    phoneInput = document.getElementById('phone');
    countryPrefixInput = document.getElementById('country-prefix-input');
    phoneErrorMessage = document.getElementById('phone-error-message');
    const countrySelectorWrapper = document.getElementById('country-selector');
    countryDropdown = document.getElementById('country-dropdown');
    countryList = document.getElementById('country-list');

    if (!phoneInput || !countryPrefixInput || !countrySelectorWrapper || !countryDropdown || !countryList) return;

    phoneInput.addEventListener('input', formatPhoneNumber);
    countryPrefixInput.addEventListener('input', handlePrefixChange);
    countryPrefixInput.addEventListener('focus', clearPhoneError);
    phoneInput.addEventListener('focus', clearPhoneError);

    // Populate country dropdown
    countryList.innerHTML = '';
    SUPPORTED_COUNTRIES.forEach(countryCode => {
        const countryData = AUTH_CONFIG.PHONE_PATTERNS[countryCode];
        if (countryData) {
            const countryItem = document.createElement('div');
            countryItem.className = 'country-item';
            countryItem.innerHTML = `
                <img src="/static/flags/1x1/${countryData.flag}.svg" alt="${countryCode.toUpperCase()} Flag" class="flag-icon" style="width: 24px; height: 24px; vertical-align: middle; border-radius: 3px;">
                <span class="dial-code" style="font-size: 18px; font-weight: bold; vertical-align: middle;">${countryData.prefixes[0]}</span>
            `;
            countryItem.addEventListener('click', () => {
                selectedCountry = countryCode;
                updateCountryDisplay(selectedCountry);
                countryDropdown.classList.remove('show');
            });
            countryList.appendChild(countryItem);
        }
    });

    countrySelectorWrapper.addEventListener('click', (e) => {
        e.stopPropagation();
        countryDropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
        if (!countrySelectorWrapper.contains(e.target) && !countryDropdown.contains(e.target)) {
            countryDropdown.classList.remove('show');
        }
    });

    updateCountryDisplay(selectedCountry); // Initial display
}

// =============================================================================
// Countdown Timer
// =============================================================================

let timerInterval;
let timerSeconds = 0;
let timerDisplayElement;
let resendOtpButton;

function startTimer(duration) {
    timerSeconds = duration;
    timerDisplayElement = document.getElementById('otp-timer-display');
    resendOtpButton = document.getElementById('otp-popup-resend-btn');

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
// OTP Popup Logic
// =============================================================================

let otpPopup;
let otpPopupInput; // Global reference for OTP input
let currentSessionId = null;
let currentIdentifier = null; // Stores phone_number or email for OTP requests
let currentAuthMethod = 'gmail'; // 'gmail' or 'telegram'
let currentLoginMode = 'otp'; // 'otp' or 'password'
let currentUserRole = 'user'; // 'user', 'admin', 'deliverer'

function createOtpPopup() {
    otpPopup = document.getElementById('otp-popup');
    otpPopupInput = document.getElementById('otp-popup-input'); // Initialize global reference
    if (!otpPopup) {
        console.error("OTP popup element with ID 'otp-popup' not found in HTML.");
        return;
    }
    otpPopup.style.display = 'none';

    const closeBtn = document.getElementById('otp-popup-close-btn');
    const verifyBtn = document.getElementById('otp-popup-verify-btn');
    const resendBtn = document.getElementById('otp-popup-resend-btn');


    if (closeBtn) closeBtn.addEventListener('click', hideOtpPopup);
    if (verifyBtn) verifyBtn.addEventListener('click', handleOtpVerification);
    if (resendBtn) resendBtn.addEventListener('click', handleOtpResend);
    if (otpPopupInput) {
        otpPopupInput.addEventListener('input', () => {
            otpPopupInput.style.borderColor = '#ddd'; // Reset border on input
        });
    }

    // Check if popup should be shown on page load (e.g., after refresh during OTP flow)
    if (localStorage.getItem('showOtpPopup') === 'true' && localStorage.getItem('currentSessionId') && localStorage.getItem('currentIdentifier')) {
        currentSessionId = localStorage.getItem('currentSessionId');
        currentIdentifier = localStorage.getItem('currentIdentifier');
        currentAuthMethod = localStorage.getItem('currentAuthMethod') || 'gmail'; // Restore auth method
        currentUserRole = localStorage.getItem('user_role') || 'user'; // Restore user role
        if (otpPopupInput) {
            otpPopupInput.maxLength = currentAuthMethod === 'gmail' ? 6 : 4; // Assuming 6 for email OTP, 4 for Telegram
            otpPopupInput.placeholder = currentAuthMethod === 'gmail' ? 'XXXXXX' : 'XXXX';
        }
        showOtpPopup(_('otp_sent'));
    }
}

function showOtpPopup(message) {
    if (!otpPopup) {
        console.error("OTP popup is not initialized.");
        return;
    }
    document.body.classList.add('no-scroll');
    otpPopup.style.display = 'flex';
    const otpMessageElement = document.getElementById('otp-message');
    if (otpMessageElement) otpMessageElement.textContent = message;

    localStorage.setItem('showOtpPopup', 'true');
    if (currentSessionId) localStorage.setItem('currentSessionId', currentSessionId);
    if (currentIdentifier) localStorage.setItem('currentIdentifier', currentIdentifier);
    localStorage.setItem('currentAuthMethod', currentAuthMethod); // Store auth method
    localStorage.setItem('user_role', currentUserRole); // Store user role

    startTimer(AUTH_CONFIG.TIMER_SETTINGS.default_seconds);
}

function hideOtpPopup() {
    if (!otpPopup) return;
    document.body.classList.remove('no-scroll');
    otpPopup.style.display = 'none';
    localStorage.removeItem('showOtpPopup');
    localStorage.removeItem('currentSessionId');
    localStorage.removeItem('currentIdentifier');
    localStorage.removeItem('currentAuthMethod');
    localStorage.removeItem('user_role');
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    if (otpPopupInput) {
        otpPopupInput.value = '';
        otpPopupInput.style.borderColor = '#ddd';
    }
}

async function handleOtpVerification() {
    const otpInputVal = otpPopupInput ? otpPopupInput.value.trim() : '';

    if (!otpInputVal) {
        showErrorBanner(_('otp_required'));
        if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
        return;
    }

    if (isFieldLocked('otp_input')) {
        showErrorBanner(_('field_locked'));
        if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
        return;
    }

    if (!currentSessionId || !currentIdentifier) {
        showErrorBanner("Session or identifier missing. Please request a new OTP.");
        hideOtpPopup();
        return;
    }

    try {
        const payload = {
            code: otpInputVal,
            session_id: currentSessionId,
            identifier: currentIdentifier,
            fingerprint: await getFingerprint(),
        };
        
        const endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_verify_otp;

        const response = await sendRequest(endpoint, 'POST', payload);

        if (response.ok) {
            if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.green;
            hideOtpPopup();
            resetBlock(currentIdentifier);
            resetFieldLock('otp_input');
            
            if (response.token) localStorage.setItem('access_token', response.token);
            if (response.refresh) localStorage.setItem('refresh_token', response.refresh);
            if (response.full_name) localStorage.setItem('username', response.full_name);
            if (response.role) localStorage.setItem('user_role', response.role);
            
            console.log("OTP Verification successful. Response role:", response.role); // Added log
            const redirectUrl = getRedirectUrlByRole(response.role);
            console.log("Redirecting to:", redirectUrl); // Added log
            showSuccessAnimationAndRedirect(redirectUrl);
        } else {
            const errorMessage = response.error || response.detail || _('otp_incorrect');
            showErrorBanner(errorMessage);
            if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
            recordFailedAttempt(currentIdentifier);
            recordFieldFailedAttempt('otp_input');
        }
    } catch (error) {
        showErrorBanner(error.message || _('otp_session_expired'));
        if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
        recordFailedAttempt(currentIdentifier);
        recordFieldFailedAttempt('otp_input');
    }
}

async function handleOtpResend() {
    if (!currentIdentifier) {
        showErrorBanner("No identifier found to resend OTP. Please start a new login process.");
        hideOtpPopup();
        return;
    }

    if (isBlocked(currentIdentifier)) {
        showErrorBanner(_('account_locked'));
        return;
    }

    try {
        const payload = {
            fingerprint: await getFingerprint()
        };

        if (currentIdentifier.includes('@')) {
            payload.email = currentIdentifier;
        } else {
            payload.phone_number = currentIdentifier;
        }

        let endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_email_login; // Default to email
        if (currentAuthMethod === 'telegram') {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_telegram_login;
        }

        if (currentUserRole === 'admin') {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.admin_login;
            payload.action = 'request_otp';
        }

        const response = await sendRequest(endpoint, 'POST', payload);
        if (response.session_id) {
            currentSessionId = response.session_id;
            localStorage.setItem('currentSessionId', currentSessionId);
            showOtpPopup(_('otp_sent'));
        } else {
            showErrorBanner(response.message || _('error_requesting_otp'));
            recordFailedAttempt(currentIdentifier);
        }
    } catch (e) {
        showErrorBanner(e.message || _('error_requesting_otp'));
        recordFailedAttempt(currentIdentifier);
    }
}

// =============================================================================
// Role Determination and Login Flows (Gmail, Telegram, Phone, Admin)
// =============================================================================

async function determineUserRole(identifier) {
    try {
        const payload = {};
        if (identifier.includes('@')) {
            payload.email = identifier;
        } else {
            payload.phone_number = identifier;
        }
        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.determine_role, 'POST', payload);
        if (response.role) {
            currentUserRole = response.role;
            localStorage.setItem('user_role', response.role);
            return response.role;
        }
        currentUserRole = 'user';
        localStorage.setItem('user_role', 'user');
        return 'user';
    } catch (error) {
        console.error("Failed to determine user role:", error);
        throw new Error(error.message || _('login_failed_try_again'));
    }
}

let pollingInterval = null;

function startSessionPolling(sessionId) {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/v1/users/login/check-session/?session_id=${sessionId}`);
            const data = await response.json();
            if (data.success && data.verified) {
                clearInterval(pollingInterval);
                hideOtpPopup();
                if (data.access) localStorage.setItem('access_token', data.access);
                if (data.refresh) localStorage.setItem('refresh_token', data.refresh);
                if (data.username) localStorage.setItem('username', data.username);
                if (data.role) localStorage.setItem('user_role', data.role);
                const redirectUrl = getRedirectUrlByRole(data.role);
                showSuccessAnimationAndRedirect(redirectUrl);
            }
        } catch (error) {
            console.error("Polling error:", error);
        }
    }, 2000);
}

async function handleAdminTelegramOtpRequest() {
    const fullPhoneNumber = countryPrefixInput.value.replace(/\s+/g, '') + phoneInput.value.replace(/\s+/g, '');
    const fieldId = 'phone_input';

    if (!fullPhoneNumber) {
        phoneErrorMessage.textContent = _('phone_required');
        return;
    }
    if (!validatePhoneNumber(phoneInput.value)) {
        phoneErrorMessage.textContent = _('no_such_number');
        recordFieldFailedAttempt(fieldId);
        return;
    }
    if (isBlocked(fullPhoneNumber) || isFieldLocked(fieldId)) {
        showErrorBanner(_('account_locked'));
        return;
    }

    try {
        const payload = {
            action: 'telegram',
            phone_number: fullPhoneNumber,
            fingerprint: await getFingerprint()
        };

        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.admin_login, 'POST', payload);

        if (response.session_id) {
            resetFieldLock(fieldId);
            currentSessionId = response.session_id;
            currentIdentifier = fullPhoneNumber;
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);
            if (response.deeplink) {
                window.open(response.deeplink, '_blank');
            }
            showOtpPopup("Telegram orqali tasdiqlash kutilmoqda...");
            startSessionPolling(currentSessionId);
        } else {
            showErrorBanner(response.message || _('error_requesting_otp'));
            recordFailedAttempt(fullPhoneNumber);
            recordFieldFailedAttempt(fieldId);
        }
    } catch (err) {
        showErrorBanner(err.message || _('error_requesting_otp'));
        recordFailedAttempt(fullPhoneNumber);
        recordFieldFailedAttempt(fieldId);
    }
}

async function handleAdminEmailOtpRequest() {
    const emailInputEl = document.getElementById('email');
    const emailVal = emailInputEl ? emailInputEl.value.trim() : '';
    const fieldId = 'email_input';

    if (!emailVal) {
        showErrorBanner(_('email_required'));
        return;
    }
    if (isBlocked(emailVal) || isFieldLocked(fieldId)) {
        showErrorBanner(_('account_locked'));
        return;
    }

    try {
        const payload = {
            email: emailVal,
            action: 'request_otp',
            fingerprint: await getFingerprint()
        };

        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.admin_login, 'POST', payload);

        if (response.session_id) {
            resetFieldLock(fieldId);
            currentSessionId = response.session_id;
            currentIdentifier = emailVal;
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);
            showOtpPopup(_('otp_sent'));
        } else {
            showErrorBanner(response.message || _('error_requesting_otp'));
            recordFailedAttempt(emailVal);
            recordFieldFailedAttempt(fieldId);
        }
    } catch (err) {
        showErrorBanner(err.message || _('error_requesting_otp'));
        recordFailedAttempt(emailVal);
        recordFieldFailedAttempt(fieldId);
    }
}

async function handleAdminPasswordLogin() {
    const emailInputEl = document.getElementById('email');
    const passwordInputEl = document.getElementById('password');
    const emailVal = emailInputEl ? emailInputEl.value.trim() : '';
    const passwordVal = passwordInputEl ? passwordInputEl.value : '';
    const fieldId = 'admin_password_login';

    if (!emailVal) {
        showErrorBanner(_('email_required'));
        return;
    }
    if (!passwordVal) {
        showErrorBanner(_('password_required'));
        return;
    }
    if (isBlocked(emailVal) || isFieldLocked(fieldId)) {
        showErrorBanner(_('account_locked'));
        return;
    }

    try {
        const payload = {
            email: emailVal,
            password: passwordVal,
            action: 'credentials',
            fingerprint: await getFingerprint(),
            csrfmiddlewaretoken: getCookie('csrftoken'),
        };

        const response = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.admin_login, 'POST', payload);

        if (response.ok) {
            resetBlock(emailVal);
            resetFieldLock(fieldId);
            if (response.token) localStorage.setItem('access_token', response.token);
            if (response.refresh) localStorage.setItem('refresh_token', response.refresh);
            if (response.full_name) localStorage.setItem('username', response.full_name);
            if (response.role) localStorage.setItem('user_role', response.role);
            const redirectUrl = getRedirectUrlByRole(response.role);
            showSuccessAnimationAndRedirect(redirectUrl);
        } else if (response.session_id) {
            currentSessionId = response.session_id;
            currentIdentifier = emailVal;
            currentUserRole = 'admin';
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);
            localStorage.setItem('currentAuthMethod', 'gmail');
            localStorage.setItem('user_role', 'admin');
            localStorage.setItem('showOtpPopup', 'true');
            showOtpPopup(response.message || _('otp_sent'));
        } else {
            showErrorBanner(response.detail || response.message || response.error || _('credentials_incorrect'));
            recordFailedAttempt(emailVal);
            recordFieldFailedAttempt(fieldId);
        }
    } catch (err) {
        showErrorBanner(err.message || _('credentials_incorrect'));
        recordFailedAttempt(emailVal);
        recordFieldFailedAttempt(fieldId);
    }
}


async function handleOtpRequest(e) {
    e.preventDefault();
    phoneErrorMessage.textContent = '';
    const fullNameInputEl = document.getElementById('full_name');
    const fullNameVal = fullNameInputEl ? fullNameInputEl.value.trim() : '';

    if (!fullNameVal) {
        showErrorBanner(_('name_required'));
        return;
    }

    let identifier;
    let fieldId;
    const csrfToken = getCookie('csrftoken');
    let payload = {
        fingerprint: await getFingerprint(),
        full_name: fullNameVal,
        csrfmiddlewaretoken: csrfToken,
    };
    let endpoint;

    if (currentAuthMethod === 'gmail') {
        const emailInputEl = document.getElementById('email');
        identifier = emailInputEl ? emailInputEl.value.trim() : '';
        fieldId = 'email_input';

        if (!identifier) {
            showErrorBanner(_('email_required'));
            return;
        }
        payload.email = identifier;
        payload.phone_number = document.getElementById('phone')?.value.trim() || '';
    } else if (currentAuthMethod === 'telegram') {
        let rawPhoneNumber = phoneInput.value.replace(/\s+/g, '');
        let prefix = countryPrefixInput.value.trim();

        if (!prefix.startsWith('+')) {
            prefix = '+' + prefix.replace(/\D/g, '');
        }

        if ((!prefix || !AUTH_CONFIG.PHONE_PATTERNS[selectedCountry] || !AUTH_CONFIG.PHONE_PATTERNS[selectedCountry].prefixes.includes(prefix)) && rawPhoneNumber.length === 9 && /^\d+$/.test(rawPhoneNumber)) {
            identifier = '+998' + rawPhoneNumber;
            if (countryPrefixInput) countryPrefixInput.value = '+998';
            selectedCountry = 'uz';
            updateCountryDisplay(selectedCountry);
        } else {
            identifier = prefix + rawPhoneNumber;
        }

        fieldId = 'phone_input';

        if (!identifier || identifier === '+') {
            phoneErrorMessage.textContent = _('phone_required');
            return;
        }
        if (!validatePhoneNumber(phoneInput.value)) {
            phoneErrorMessage.textContent = _('no_such_number');
            recordFieldFailedAttempt(fieldId);
            return;
        }
        payload.phone_number = identifier;
    } else {
        showErrorBanner("Unknown authentication method.");
        return;
    }

    if (isBlocked(identifier) || isFieldLocked(fieldId)) {
        showErrorBanner(_('account_locked'));
        return;
    }

    try {
        await determineUserRole(identifier);
    } catch (error) {
        showErrorBanner(error.message || _('login_failed_try_again'));
        return;
    }


    if (currentUserRole === 'admin') {
        if (currentAuthMethod === 'gmail') {
            await handleAdminEmailOtpRequest();
        } else if (currentAuthMethod === 'telegram') {
            await handleAdminTelegramOtpRequest();
        }
        return;
    } else {
        if (currentAuthMethod === 'gmail') {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_email_login;
        } else if (currentAuthMethod === 'telegram') {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_telegram_login;
        }
    }

    try {
        const response = await sendRequest(endpoint, 'POST', payload);

        if (response.session_id) {
            resetFieldLock(fieldId);
            currentSessionId = response.session_id;
            currentIdentifier = identifier;
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);
            
            if (currentAuthMethod === 'telegram') {
                const link = response.deeplink || response.verification_link;
                if (link) {
                    window.open(link, '_blank');
                }
                showOtpPopup("Telegram orqali tasdiqlash kutilmoqda...");
                startSessionPolling(currentSessionId);
            } else {
                showOtpPopup(_('otp_sent'));
            }
        } else if (response.redirect) {
            window.location.href = _safeRedirectUrl(response.redirect);
        } else {
            showErrorBanner(response.message || _('error_requesting_otp'));
            recordFailedAttempt(identifier);
            recordFieldFailedAttempt(fieldId);
        }
    } catch (err) {
        showErrorBanner(err.message || _('error_requesting_otp'));
        recordFailedAttempt(identifier);
        recordFieldFailedAttempt(fieldId);
    }
}


// =============================================================================
// Success Animation and Redirection
// =============================================================================

const _REDIRECT_WHITELIST = ['/dashboard/admin/', '/dashboard/delivery/', '/account/', '/auth/'];

function _safeRedirectUrl(url) {
    if (!url || typeof url !== 'string') return '/';
    const cleanedUrl = new URL(url, window.location.origin).pathname;
    return _REDIRECT_WHITELIST.find(w => cleanedUrl.startsWith(w)) || '/account/';
}

function showSuccessAnimationAndRedirect(redirectUrl) {
    hideOtpPopup();
    const loader = document.getElementById('loader');
    if (loader) {
        loader.classList.add('show');
    }
    const safeUrl = _safeRedirectUrl(redirectUrl);
    setTimeout(() => {
        window.location.href = safeUrl;
    }, 1500);
}

function getRedirectUrlByRole(role) {
    switch (role) {
        case 'admin':
            return '/dashboard/admin/';
        case 'deliverer':
            return '/dashboard/delivery/';
        case 'user':
        default:
            return '/account/';
    }
}

// =============================================================================
// DOM Elements Setup and Events Initialization
// =============================================================================

let passwordInput;
let loginModeToggleBtn; // Button to switch between OTP and Password login

function updateLoginModeUI() {
    const passwordGroup = document.getElementById('password-group'); // Assuming this exists
    const getCodeBtn = document.getElementById('get-code');
    const loginWithPasswordBtn = document.getElementById('login-with-password-btn'); // Assuming this exists

    if (currentUserRole === 'admin' && currentAuthMethod === 'gmail') {
        if (loginModeToggleBtn) {
            loginModeToggleBtn.style.display = 'block';
            loginModeToggleBtn.textContent = currentLoginMode === 'otp' ? _('login_with_password') : _('login_with_otp');
        }

        if (currentLoginMode === 'otp') {
            if (passwordGroup) passwordGroup.classList.add('hidden-field');
            if (getCodeBtn) getCodeBtn.style.display = 'block';
            if (loginWithPasswordBtn) loginWithPasswordBtn.style.display = 'none';
        } else { // password mode
            if (passwordGroup) passwordGroup.classList.remove('hidden-field');
            if (getCodeBtn) getCodeBtn.style.display = 'none';
            if (loginWithPasswordBtn) loginWithPasswordBtn.style.display = 'block';
        }
    } else {
        // Default to OTP for non-admins or Telegram login
        if (passwordGroup) passwordGroup.classList.add('hidden-field');
        if (getCodeBtn) getCodeBtn.style.display = 'block';
        if (loginWithPasswordBtn) loginWithPasswordBtn.style.display = 'none';
        if (loginModeToggleBtn) loginModeToggleBtn.style.display = 'none';
        currentLoginMode = 'otp'; // Reset to OTP mode
    }
}


async function initAuthPage() {
    await loadCountriesData();
    createOtpPopup();
    setupPhoneInputAndCountrySelector();

    const gmailLoginBtn = document.getElementById('gmail-login');
    const telegramLoginBtn = document.getElementById('telegram-login');
    const getCodeBtn = document.getElementById('get-code');
    const authForm = document.getElementById('auth-form');
    passwordInput = document.getElementById('password'); // Assuming this exists
    loginModeToggleBtn = document.getElementById('login-mode-toggle-btn'); // Assuming this exists
    const loginWithPasswordBtn = document.getElementById('login-with-password-btn'); // Assuming this exists

    const phoneGroup = document.getElementById('phone-group');
    const emailGroup = document.getElementById('email-group');
    const nameGroup = document.getElementById('name-group');
    const passwordGroup = document.getElementById('password-group'); // Assuming this exists

    // Initial state: Gmail active, email field visible, phone field hidden
    if (gmailLoginBtn && telegramLoginBtn && phoneGroup && emailGroup && otpPopupInput) {
        gmailLoginBtn.classList.add('active');
        telegramLoginBtn.classList.remove('active');
        emailGroup.classList.remove('hidden-field');
        phoneGroup.classList.add('hidden-field');
        nameGroup.classList.remove('hidden-field');
        if (passwordGroup) passwordGroup.classList.add('hidden-field'); // Hide password initially
        currentAuthMethod = 'gmail';
        otpPopupInput.maxLength = 6;
        otpPopupInput.placeholder = 'XXXXXX';
    }

    // Event listener for "Kod olish" button (now handleOtpRequest)
    if (getCodeBtn) {
        getCodeBtn.addEventListener('click', handleOtpRequest);
    }

    // Event listener for "Login with Password" button
    if (loginWithPasswordBtn) {
        loginWithPasswordBtn.addEventListener('click', handleAdminPasswordLogin);
    }

    // Event listener for login mode toggle button
    if (loginModeToggleBtn) {
        loginModeToggleBtn.addEventListener('click', () => {
            currentLoginMode = currentLoginMode === 'otp' ? 'password' : 'otp';
            updateLoginModeUI();
        });
    }

    // Event listener for form submission (to prevent default if button is type="submit")
    if (authForm) {
        authForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (currentUserRole === 'admin' && currentAuthMethod === 'gmail' && currentLoginMode === 'password') {
                handleAdminPasswordLogin();
            } else {
                handleOtpRequest(e);
            }
        });
    }

    // Gmail button binding
    if (gmailLoginBtn) {
        gmailLoginBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            gmailLoginBtn.classList.add('active');
            telegramLoginBtn.classList.remove('active');
            emailGroup.classList.remove('hidden-field');
            phoneGroup.classList.add('hidden-field');
            nameGroup.classList.remove('hidden-field');
            phoneErrorMessage.textContent = '';
            currentAuthMethod = 'gmail';
            if (otpPopupInput) {
                otpPopupInput.maxLength = 6;
                otpPopupInput.placeholder = 'XXXXXX';
            }
            // Removed premature determineUserRole call
            currentUserRole = 'user'; // Default to user until OTP request
            updateLoginModeUI();
        });
    }

    // Telegram button binding
    if (telegramLoginBtn) {
        telegramLoginBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            telegramLoginBtn.classList.add('active');
            gmailLoginBtn.classList.remove('active');
            phoneGroup.classList.remove('hidden-field');
            emailGroup.classList.add('hidden-field');
            nameGroup.classList.remove('hidden-field');
            phoneErrorMessage.textContent = '';
            currentAuthMethod = 'telegram';
            if (otpPopupInput) {
                otpPopupInput.maxLength = 4;
                otpPopupInput.placeholder = 'XXXX';
            }
            // Removed premature determineUserRole call
            currentUserRole = 'user'; // Default to user until OTP request
            updateLoginModeUI();
        });
    }

    // Initial UI update based on default state
    updateLoginModeUI();
}

document.addEventListener('DOMContentLoaded', initAuthPage);