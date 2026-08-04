// Global loyiha sozlamalari

// API_BASE_URL: plain browser JS has no process.env — use window.location.origin
// so it works on both http://127.0.0.1 (dev) and https://onlinepharmacy.uz (prod)
export const API_BASE_URL = window.location.origin;

const PROJECT_CONFIG = {
    address: "Navoiy shahar, Zarapetyan ko'chasi",
    phone: "+998 97 770 55 58",
    email: "firdavsyoldoshevpython@gmail.com",
    establishedYear: 2026,
    founder: "Firdavs",
    apiBaseUrl: API_BASE_URL // API_BASE_URL ni PROJECT_CONFIG ga qo'shish
};

// Davlatlar va ularning kodlari
const COUNTRY_DATA = [
    { name: "Uzbekistan", code: "+998", flag: "https://flagcdn.com/w40/uz.png", pattern: /^\+998\d{9}$/ },
    { name: "USA", code: "+1", flag: "https://flagcdn.com/w40/us.png", pattern: /^\+1\d{10}$/ },
    { name: "Russia", code: "+7", flag: "https://flagcdn.com/w40/ru.png", pattern: /^\+7\d{10}$/ }
];

function updateGlobalInfo() {
    document.querySelectorAll('.global-address').forEach(el => el.innerText = PROJECT_CONFIG.address);
    document.querySelectorAll('.global-phone').forEach(el => el.innerText = PROJECT_CONFIG.phone);
    document.querySelectorAll('.global-email').forEach(el => el.innerText = PROJECT_CONFIG.email);
}

document.addEventListener('DOMContentLoaded', updateGlobalInfo);