// static/js/utils.js

const CSRF_COOKIE_NAME = 'csrftoken';
const FINGERPRINT_LIB_URL = 'https://cdnjs.cloudflare.com/ajax/libs/fingerprintjs2/2.1.0/fingerprint2.min.js';

/**
 * Cookie qiymatini nomiga qarab qaytaradi.
 * @param {string} name Cookie nomi.
 * @returns {string|null} Cookie qiymati yoki null.
 */
export function getCookie(name) {
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

/**
 * Dinamik ravishda script yuklaydi.
 * @param {string} src Script faylining URL manzili.
 * @returns {Promise<void>} Script yuklanganda resolve bo'ladigan Promise.
 */
async function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

/**
 * Foydalanuvchi qurilmasining barmoq izini (fingerprint) generatsiya qiladi.
 * Agar Fingerprint2 kutubxonasi yuklanmagan bo'lsa, uni dinamik ravishda yuklaydi.
 * @returns {Promise<string>} Qurilma barmoq izi.
 */
export async function getFingerprint() {
    if (typeof Fingerprint2 === 'undefined') {
        try {
            await loadScript(FINGERPRINT_LIB_URL);
        } catch (e) {
            console.error("Fingerprint library loading failed:", e);
            return "fallback-fingerprint-" + navigator.userAgent;
        }
    }
    return new Promise(resolve => {
        try {
            // Fingerprint2.get funksiyasi asinxron bo'lgani uchun setTimeout ichida chaqiriladi
            // Bu ba'zi brauzerlarda to'g'ri ishlashini ta'minlaydi.
            setTimeout(function () {
                Fingerprint2.get((components) => {
                    const values = components.map(component => component.value);
                    const hash = Fingerprint2.x64hash128(values.join(''), 31);
                    resolve(hash);
                });
            }, 500); // Kichik kechikish qo'shildi
        } catch (err) {
            console.error("Fingerprint2.get failed:", err);
            resolve("fallback-fingerprint-eval-" + navigator.userAgent);
        }
    });
}

/**
 * Backendga AJAX so'rov yuboradi.
 * @param {string} url So'rov yuboriladigan URL.
 * @param {string} method HTTP metodi (GET, POST, PUT, DELETE).
 * @param {object} [data] So'rov tanasi (faqat POST, PUT uchun).
 * @returns {Promise<object>} Backenddan kelgan javob.
 */
export function sendRequest(url, method, data = null) {
    const csrftoken = getCookie(CSRF_COOKIE_NAME);
    const headers = {
        'Accept': 'application/json'
    };

    if (method !== 'GET') {
        headers['Content-Type'] = 'application/json';
        headers['X-CSRFToken'] = csrftoken;
    }

    const config = {
        method: method,
        headers: headers,
        credentials: 'same-origin' // CSRF token bilan ishlash uchun muhim
    };

    if (data) {
        config.body = JSON.stringify(data);
    }

    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                // Agar javob JSON bo'lmasa, umumiy xato qaytarish
                return response.json().catch(() => {
                    throw new Error(`HTTP error! Status: ${response.status} - ${response.statusText}`);
                }).then(err => {
                    throw err; // JSON xatosini qayta tashlash
                });
            }
            return response.json();
        });
}

