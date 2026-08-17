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
        admin_verify_otp:     '/api/v1/users/admin/verify-otp/', // AdminLoginViewSet - verify_otp action (new endpoint)
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
    ALLOWED_DOMAINS: ['gmail.com', 'yahoo.com', 'mail.ru', 'ok.ru', 'hotmail.com'],
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
            otp_session_expired: "OTP session has expired. Please request a new one.",
            email_valid: "Email to'g'ri.",
            email_invalid: "Email noto'g'ri. Faqat ruxsat etilgan domenlardan foydalaning.",
            phone_valid: "Telefon raqam to'g'ri.",
            phone_invalid: "Telefon raqam noto'g'ri. Format: +998 XX XXX XX XX"
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
            error_requesting_otp: "Error requesting OTP.",
            no_such_number: "Bunday raqam topilmadi.",
            name_required: "Ismni kiriting.",
            password_required: "Parol majburiy.",
            login_with_password: "Parol bilan kirish",
            login_with_otp: "OTP bilan kirish",
            login_failed_try_again: "Kirish amalga oshmadi, iltimos qayta urinib ko'ring.",
            otp_session_expired: "OTP sessiyasi muddati tugadi. Iltimos, yangi OTP so‘rang.",
            email_valid: "Email to‘g‘ri.",
            email_invalid: "Email noto‘g‘ri. Faqat ruxsat etilgan domenlardan foydalaning.",
            phone_valid: "Telefon raqam to‘g‘ri.",
            phone_invalid: "Telefon raqam noto‘g‘ri. Format: +998 XX XXX XX XX"
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
        let payload;
        let endpoint;

        // This is the main fix: always include the action based on the auth method
        const action = currentAuthMethod === 'gmail' ? 'gmail' : 'telegram';

        if (currentUserRole === 'admin') {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.admin_verify_otp; // Use the new dedicated endpoint
            payload = {
                action: 'verify_otp', // FIXED: Added action field for admin verify_otp
                session_id: currentSessionId,
                code: otpInputVal, // Changed from 'otp' to 'code' for consistency with VerifyOTPSerializer
                fingerprint: await getFingerprint(),
            };
            if (currentIdentifier.includes('@')) {
                payload.email = currentIdentifier;
            } else {
                payload.phone_number = currentIdentifier;
            }
        } else {
            endpoint = AUTH_CONFIG.AUTH_ENDPOINTS.user_verify_otp;
            payload = {
                code: otpInputVal,
                session_id: currentSessionId,
                identifier: currentIdentifier,
                action: action,
                fingerprint: await getFingerprint(),
            };
        }

        console.debug('[Auth] Verifying OTP with payload:', payload);
        const response = await sendRequest(endpoint, 'POST', payload);
        console.debug('[Auth] OTP verification response:', response);

        if (response.success || response.ok) {
            if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.green;
            hideOtpPopup();
            resetBlock(currentIdentifier);
            resetFieldLock('otp_input');

            // Store token, refresh, user_id, role, and avatar_url
            if (response.token) localStorage.setItem('access_token', response.token);
            if (response.refresh) localStorage.setItem('refresh_token', response.refresh);
            if (response.user_id) localStorage.setItem('user_id', response.user_id);
            if (response.full_name) localStorage.setItem('username', response.full_name);

            const role = response.role || currentUserRole;
            localStorage.setItem('user_role', role);
            if (response.avatar_url) localStorage.setItem('avatar_url', response.avatar_url);

            // FIX: Update header immediately after saving tokens
            if (typeof window.updateHeaderAfterLogin === 'function') {
                window.updateHeaderAfterLogin();
            }

            const redirectUrl = response.redirect || getRedirectUrlByRole(role);
            showSuccessAnimationAndRedirect(redirectUrl);
        } else {
            const errorMessage = response.error || response.detail || _('otp_incorrect');
            showErrorBanner(errorMessage);
            if (otpPopupInput) otpPopupInput.style.borderColor = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
            recordFailedAttempt(currentIdentifier);
            recordFieldFailedAttempt('otp_input');
        }
    } catch (error) {
        const errorMessage = error.error || error.message || _('otp_session_expired');
        showErrorBanner(errorMessage);
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
    console.debug(`[Auth] Starting session polling for session_id: ${sessionId}`);
    if (pollingInterval) clearInterval(pollingInterval);

    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/v1/users/login/check-session/?session_id=${sessionId}`);
            const data = await response.json();
            if (data.success && data.verified) {
                console.debug('[Auth] Session verified via polling. Completing login.');
                clearInterval(pollingInterval);
                pollingInterval = null;
                hideOtpPopup();
                if (data.access) localStorage.setItem('access_token', data.access);
                if (data.refresh) localStorage.setItem('refresh_token', data.refresh);
                if (data.user_id) localStorage.setItem('user_id', data.user_id);
                if (data.username) localStorage.setItem('username', data.username);
                if (data.role) localStorage.setItem('user_role', data.role);
                if (data.avatar_url) localStorage.setItem('avatar_url', data.avatar_url);

                // FIX: Update header immediately after saving tokens
                if (typeof window.updateHeaderAfterLogin === 'function') {
                    window.updateHeaderAfterLogin();
                }

                const redirectUrl = getRedirectUrlByRole(data.role);
                showSuccessAnimationAndRedirect(redirectUrl);
            }
        } catch (error) {
            console.error("Polling error:", error);
        }
    }, 2000);

    // FIX: Add a listener to clear the interval if the user navigates away
    window.addEventListener('beforeunload', () => {
        if (pollingInterval) {
            console.debug('[Auth] Clearing polling interval due to page unload.');
            clearInterval(pollingInterval);
        }
    });
}

async function handleAdminTelegramOtpRequest() {
    const localPhoneInput = document.getElementById('phone');
    const localCountryPrefixInput = document.getElementById('country-prefix-input');
    const localPhoneErrorMessage = document.getElementById('phone-error-message');

    if (!localPhoneInput || !localCountryPrefixInput || !localPhoneErrorMessage) {
        showErrorBanner("Tizim xatosi: Telefon raqam kiritish maydonlari topilmadi.");
        console.error("Phone input elements not found for admin telegram OTP request.");
        return;
    }

    const fullPhoneNumber = localCountryPrefixInput.value.replace(/\s+/g, '') + localPhoneInput.value.replace(/\s+/g, '');
    const fieldId = 'phone_input';

    if (!fullPhoneNumber) {
        localPhoneErrorMessage.textContent = _('phone_required');
        return;
    }
    if (!validatePhoneNumber(localPhoneInput.value)) {
        localPhoneErrorMessage.textContent = _('no_such_number');
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

    if (!emailInputEl) {
        showErrorBanner("Tizim xatosi: Email kiritish maydoni topilmadi.");
        console.error("Email input not found for admin email OTP request.");
        return;
    }

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

    if (!emailInputEl || !passwordInputEl) {
        showErrorBanner("Tizim xatosi: Email yoki parol kiritish maydonlari topilmadi.");
        console.error("Email or password input not found for admin password login.");
        return;
    }

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

        if (response.success) {
            resetBlock(emailVal);
            resetFieldLock(fieldId);
            // Store token, refresh, user_id, role, and avatar_url
            if (response.token) localStorage.setItem('access_token', response.token);
            if (response.refresh) localStorage.setItem('refresh_token', response.refresh);
            if (response.user_id) localStorage.setItem('user_id', response.user_id);
            if (response.full_name) localStorage.setItem('username', response.full_name);
            if (response.role) localStorage.setItem('user_role', response.role);
            if (response.avatar_url) localStorage.setItem('avatar_url', response.avatar_url);

            // FIX: Update header immediately after saving tokens
            if (typeof window.updateHeaderAfterLogin === 'function') {
                window.updateHeaderAfterLogin();
            }

            const redirectUrl = getRedirectUrlByRole(response.role);
            showSuccessAnimationAndRedirect(redirectUrl);
        } else if (response.session_id) {
            // FIXED: Don't hardcode currentUserRole as 'admin'
            // Call determine_role to get actual role from server
            try {
                const rolePayload = { email: emailVal };
                const roleResponse = await sendRequest(AUTH_CONFIG.AUTH_ENDPOINTS.determine_role, 'POST', rolePayload);
                if (roleResponse.role) {
                    currentUserRole = roleResponse.role;
                    localStorage.setItem('user_role', roleResponse.role);
                } else {
                    // Fallback to 'user' if role determination fails
                    currentUserRole = 'user';
                    localStorage.setItem('user_role', 'user');
                }
            } catch (err) {
                console.warn('Failed to determine role, defaulting to user', err);
                currentUserRole = 'user';
                localStorage.setItem('user_role', 'user');
            }

            currentSessionId = response.session_id;
            currentIdentifier = emailVal;
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);
            localStorage.setItem('currentAuthMethod', 'gmail');
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

// FIX: Added debounce to prevent spamming the OTP request button.
let isRequestingOtp = false;
const otpRequestDebounceTime = 5000; // 5 seconds

async function handleOtpRequest() {
    if (isRequestingOtp) {
        console.warn('[Auth] OTP request is already in progress. Please wait.');
        showErrorBanner('Iltimos, biroz kuting...');
        return;
    }

    isRequestingOtp = true;
    const getCodeBtn = document.getElementById('get-code-btn');
    if (getCodeBtn) getCodeBtn.disabled = true;

    setTimeout(() => {
        isRequestingOtp = false;
        if (getCodeBtn) getCodeBtn.disabled = false;
    }, otpRequestDebounceTime);

    // Clear previous errors
    const phoneErrorMessage = document.getElementById('phone-error-message');
    if (phoneErrorMessage) phoneErrorMessage.textContent = '';
    const emailValidator = document.getElementById('email-validator');
    if (emailValidator) emailValidator.textContent = '';
    const authErrorBanner = document.getElementById('auth-error-banner');
    if (authErrorBanner) authErrorBanner.style.display = 'none';

    try {
        const fullNameInputEl = document.getElementById('full_name');
        if (!fullNameInputEl) {
            throw new Error("Tizim xatosi: Ism kiritish maydoni topilmadi.");
        }
        const fullNameVal = fullNameInputEl.value.trim();
        if (!fullNameVal) {
            throw new Error(_('name_required'));
        }

        let identifier;
        let fieldId;
        const payload = {
            fingerprint: await getFingerprint(),
            full_name: fullNameVal,
            csrfmiddlewaretoken: getCookie('csrftoken'),
        };

        if (currentAuthMethod === 'gmail') {
            const emailInputEl = document.getElementById('email');
            if (!emailInputEl) throw new Error("Tizim xatosi: Email kiritish maydoni topilmadi.");
            identifier = emailInputEl.value.trim();
            if (!identifier) throw new Error(_('email_required'));
            payload.email = identifier;
            fieldId = 'email_input';
        } else if (currentAuthMethod === 'telegram') {
            const localPhoneInput = document.getElementById('phone');
            const localCountryPrefixInput = document.getElementById('country-prefix-input');
            if (!localPhoneInput || !localCountryPrefixInput) throw new Error("Tizim xatosi: Telefon raqam kiritish maydonlari topilmadi.");

            let rawPhoneNumber = localPhoneInput.value.replace(/\s+/g, '');
            let prefix = localCountryPrefixInput.value.trim();
            if (!prefix.startsWith('+')) prefix = '+' + prefix.replace(/\D/g, '');

            identifier = prefix + rawPhoneNumber;
            if (!identifier || identifier === '+') throw new Error(_('phone_required'));
            if (!validatePhoneNumber(localPhoneInput.value)) throw new Error(_('no_such_number'));

            payload.phone_number = identifier;
            fieldId = 'phone_input';
        } else {
            throw new Error("Noma'lum autentifikatsiya usuli.");
        }

        if (isBlocked(identifier) || isFieldLocked(fieldId)) {
            throw new Error(_('account_locked'));
        }

        const role = await determineUserRole(identifier);
        if (role === 'admin') {
            if (currentAuthMethod === 'gmail') await handleAdminEmailOtpRequest();
            else if (currentAuthMethod === 'telegram') await handleAdminTelegramOtpRequest();
            return;
        }

        const endpoint = currentAuthMethod === 'gmail' ? AUTH_CONFIG.AUTH_ENDPOINTS.user_email_login : AUTH_CONFIG.AUTH_ENDPOINTS.user_telegram_login;
        console.debug("Sending OTP request to:", endpoint);
        const response = await sendRequest(endpoint, 'POST', payload);

        if (response.session_id) {
            resetFieldLock(fieldId);
            currentSessionId = response.session_id;
            currentIdentifier = identifier;
            localStorage.setItem('currentSessionId', currentSessionId);
            localStorage.setItem('currentIdentifier', currentIdentifier);

            if (currentAuthMethod === 'telegram') {
                const link = response.deeplink || response.verification_link;
                if (link) window.open(link, '_blank');
                showOtpPopup("Telegram orqali tasdiqlash kutilmoqda...");
                startSessionPolling(currentSessionId);
            } else {
                showOtpPopup(_('otp_sent'));
            }
        } else if (response.redirect) {
            window.location.href = _safeRedirectUrl(response.redirect);
        } else {
            throw new Error(response.message || _('error_requesting_otp'));
        }
    } catch (err) {
        console.error("Error in handleOtpRequest:", err);
        showErrorBanner(err.message || "Noma'lum xatolik yuz berdi.");
        // Re-enable button immediately on error
        isRequestingOtp = false;
        if (getCodeBtn) getCodeBtn.disabled = false;
    }
}


// =============================================================================
// Success Animation and Redirection
// =============================================================================

// FIX: Expanded the redirect whitelist to include all valid dashboard URLs.
const _REDIRECT_WHITELIST = [
    '/dashboard/admin/',
    '/dashboard/seller/',
    '/dashboard/delivery/',
    '/dashboard/driver/',
    '/account/',
    '/auth/',
    '/shop/'
];

let isRedirecting = false; // Flag to prevent multiple redirects

function _safeRedirectUrl(url) {
    if (!url || typeof url !== 'string') {
        console.warn(`[Auth] Invalid or empty redirect URL provided. Defaulting to /shop/`);
        return '/shop/';
    }
    try {
        const cleanedUrl = new URL(url, window.location.origin).pathname;
        // Find if the cleaned URL starts with any of the whitelisted paths
        const matchedPath = _REDIRECT_WHITELIST.find(w => cleanedUrl.startsWith(w));
        if (matchedPath) {
            console.debug(`[Auth] Redirect URL ${cleanedUrl} is whitelisted.`);
            return cleanedUrl;
        }
        console.warn(`[Auth] Redirect URL ${cleanedUrl} not in whitelist. Defaulting to /shop/`);
        return '/shop/';
    } catch (e) {
        console.error(`[Auth] Invalid redirect URL format: ${url}. Defaulting to /shop/`);
        return '/shop/';
    }
}

function showSuccessAnimationAndRedirect(redirectUrl) {
    if (isRedirecting) {
        console.warn('[Auth] Redirect already in progress. Ignoring duplicate call.');
        return;
    }
    isRedirecting = true;
    console.debug(`[Auth] Login successful. Preparing to redirect to: ${redirectUrl}`);

    hideOtpPopup();
    const loader = document.getElementById('loader');
    if (loader) {
        loader.classList.add('show');
    }
    // The actual redirect happens inside debounceRedirect after its timer.
    // This function just sets up the visual feedback.
    setTimeout(() => {
        // No reload, just navigate
        window.location.href = redirectUrl;
    }, 1500);
}

function getRedirectUrlByRole(role) {
    if (!role) {
        console.warn("[Auth] No role provided, defaulting to shop page");
        return '/shop/';
    }

    const redirectMap = {
        'admin': '/dashboard/admin/',
        'seller': '/dashboard/seller/',
        'user': '/shop/',
        'deliverer': '/dashboard/delivery/',
        'driver': '/dashboard/driver/'
    };

    const redirectUrl = redirectMap[role] || redirectMap['user'];
    console.debug(`[Auth] Redirecting user with role '${role}' to: ${redirectUrl}`);
    return redirectUrl;
}

// =============================================================================
// DOM Elements Setup and Events Initialization
// =============================================================================

let passwordInput;
let loginModeToggleBtn; // Button to switch between OTP and Password login

function updateLoginModeUI() {
    const passwordGroup = document.getElementById('password-group'); // Assuming this exists
    const getCodeBtn = document.getElementById('get-code-btn');
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

function validateEmail(email) {
    if (!email) return false;
    const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    if (!re.test(String(email).toLowerCase())) return false;
    const domain = email.split('@')[1];
    return AUTH_CONFIG.ALLOWED_DOMAINS.includes(domain);
}

function validatePhoneNumberFormat() {
    const countryData = AUTH_CONFIG.PHONE_PATTERNS[selectedCountry];
    if (!countryData || !countryData.regex) return false;
    const cleanNum = countryPrefixInput.value + phoneInput.value.replace(/\s+/g, '');
    return countryData.regex.test(cleanNum);
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadCountriesData();
    createOtpPopup();
    setupPhoneInputAndCountrySelector();

    const emailInput = document.getElementById('email');
    const emailValidator = document.getElementById('email-validator');
    const phoneInput = document.getElementById('phone');
    const phoneValidator = document.getElementById('phone-validator');
    const getCodeBtn = document.getElementById('get-code-btn');

    let isEmailValid = false;
    let isPhoneValid = false;

    function checkFormValidity() {
        if (!getCodeBtn) return;
        if (currentAuthMethod === 'gmail') {
            getCodeBtn.disabled = !isEmailValid;
        } else if (currentAuthMethod === 'telegram') {
            getCodeBtn.disabled = !isPhoneValid;
        } else {
            getCodeBtn.disabled = true;
        }
    }

    if (emailInput && emailValidator) {
        emailInput.addEventListener('input', () => {
            const email = emailInput.value;
            isEmailValid = validateEmail(email);
            if (isEmailValid) {
                emailValidator.textContent = _('email_valid');
                emailValidator.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.green;
            } else {
                emailValidator.textContent = _('email_invalid');
                emailValidator.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
            }
            checkFormValidity();
        });
    }

    if (phoneInput && phoneValidator) {
        phoneInput.addEventListener('input', () => {
            isPhoneValid = validatePhoneNumberFormat();
            if (isPhoneValid) {
                phoneValidator.textContent = _('phone_valid');
                phoneValidator.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.green;
            } else {
                phoneValidator.textContent = _('phone_invalid');
                phoneValidator.style.color = AUTH_CONFIG.TIMER_SETTINGS.colors.red;
            }
            checkFormValidity();
        });
    }


    const gmailLoginBtn = document.getElementById('gmail-login');
    const telegramLoginBtn = document.getElementById('telegram-login');
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
        if(phoneErrorMessage) phoneErrorMessage.textContent = '';
        currentAuthMethod = 'gmail';
        if (otpPopupInput) {
            otpPopupInput.maxLength = 6;
            otpPopupInput.placeholder = 'XXXXXX';
        }
        // Removed premature determineUserRole call
        currentUserRole = 'user'; // Default to user until OTP request
        updateLoginModeUI();
        checkFormValidity();
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

    // Gmail button binding
    if (gmailLoginBtn) {
        gmailLoginBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            gmailLoginBtn.classList.add('active');
            telegramLoginBtn.classList.remove('active');
            emailGroup.classList.remove('hidden-field');
            phoneGroup.classList.add('hidden-field');
            nameGroup.classList.remove('hidden-field');
            if(phoneErrorMessage) phoneErrorMessage.textContent = '';
            currentAuthMethod = 'gmail';
            if (otpPopupInput) {
                otpPopupInput.maxLength = 6;
                otpPopupInput.placeholder = 'XXXXXX';
            }
            // Removed premature determineUserRole call
            currentUserRole = 'user'; // Default to user until OTP request
            updateLoginModeUI();
            checkFormValidity();
        });
    }

    if (telegramLoginBtn) {
        telegramLoginBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            telegramLoginBtn.classList.add('active');
            gmailLoginBtn.classList.remove('active');
            phoneGroup.classList.remove('hidden-field');
            emailGroup.classList.add('hidden-field');
            nameGroup.classList.remove('hidden-field');
            if(phoneErrorMessage) phoneErrorMessage.textContent = '';
            currentAuthMethod = 'telegram';
            if (otpPopupInput) {
                otpPopupInput.maxLength = 4;
                otpPopupInput.placeholder = 'XXXX';
            }
            // Removed premature determineUserRole call
            currentUserRole = 'user'; // Default to user until OTP request
            updateLoginModeUI();
            checkFormValidity();
        });
    }

    // Initial UI update based on default state
    updateLoginModeUI();
});

// FIX: Expose updateHeaderAfterLogin to window for header refresh after login
window.updateHeaderAfterLogin = function() {
    console.debug('[Auth] updateHeaderAfterLogin called');

    const token = localStorage.getItem('access_token');
    if (!token) {
        console.warn('[Auth] No access token found for header update');
        return;
    }

    // Trigger header reload using loadUser from header.js
    if (typeof window.loadUser === 'function') {
        window.loadUser();
    } else {
        console.warn('[Auth] loadUser not found on window object');
    }
};

// FIX: Add loadUser function for header.js compatibility
window.loadUser = async function() {
    console.debug('[Auth] loadUser called');
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.warn('[Auth] No access token for loadUser');
        return;
    }

    try {
        const response = await fetch('/api/v1/users/me/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            credentials: 'include'
        });

        if (response.ok) {
            const user = await response.json();
            
            // Get full_name, username, or email - NOT role!
            const username = user.full_name || user.username || user.email || localStorage.getItem('username');
            
            // Update localStorage
            localStorage.setItem('username', username || '');
            localStorage.setItem('avatar_url', user.avatar_url || '');
            if (user.role) localStorage.setItem('user_role', user.role);

            // Update header UI
            if (typeof window.updateHeaderUI === 'function') {
                const userRole = user.role || localStorage.getItem('user_role');
                const shouldShowDropdown = userRole === 'admin' || userRole === 'seller' || userRole === 'user';
                window.updateHeaderUI(true, username, user.avatar_url || user.avatar, user.email || '', userRole, shouldShowDropdown);
            }
        }
    } catch (err) {
        console.error('[Auth] loadUser error:', err);
    }
};