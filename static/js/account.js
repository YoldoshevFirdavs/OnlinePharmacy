// static/js/account.js

// Inlined getCookie function from utils.js
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

// Inlined sendRequest function from utils.js (modified for FormData)
async function sendRequest(url, method, data = null, isFormData = false) {
    const csrftoken = getCookie('csrftoken');
    const headers = {
        'Accept': 'application/json'
    };

    if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
    }

    const config = {
        method: method,
        headers: headers,
        credentials: 'same-origin'
    };

    if (data) {
        if (isFormData) {
            delete headers['Content-Type']; // Let browser set Content-Type for FormData
            config.body = data;
        } else {
            headers['Content-Type'] = 'application/json';
            config.body = JSON.stringify(data);
        }
    }

    const response = await fetch(url, config);

    if (!response.ok) {
        const errorData = await response.json().catch(() => {
            throw new Error(`HTTP error! Status: ${response.status} - ${response.statusText}`);
        });
        throw errorData;
    }
    return response.json();
}

const ACCOUNT_CONFIG = {
    PROFILE_API_URL: '/api/v1/users/me/',
    ORDERS_API_URL: '/api/v1/orders/my_orders/', // Assuming an endpoint for user orders
    DEFAULT_AVATAR: '/static/images/default_avatar.png',
    AUTH_PAGE_URL: '/auth/',
    I18N: {
        uz: {
            profile_updated: "Profil muvaffaqiyatli yangilandi!",
            error_updating_profile: "Profilni yangilashda xato yuz berdi.",
            error_fetching_profile: "Profil ma'lumotlarini yuklashda xato yuz berdi.",
            error_fetching_orders: "Buyurtmalarni yuklashda xato yuz berdi.",
            no_orders: "Buyurtmalar topilmadi.",
            logout_success: "Tizimdan chiqdingiz.",
            logout_error: "Tizimdan chiqishda xato yuz berdi.",
            confirm_logout: "Haqiqatan ham tizimdan chiqmoqchimisiz?",
            reverify_email_phone: "Email yoki telefon raqami o'zgardi. Qayta tasdiqlash kerak."
        }
    },
    DEFAULT_LANG: 'uz'
};

function _(key) {
    const lang = localStorage.getItem('user_lang') || ACCOUNT_CONFIG.DEFAULT_LANG;
    return ACCOUNT_CONFIG.I18N[lang][key] || ACCOUNT_CONFIG.I18N[ACCOUNT_CONFIG.DEFAULT_LANG][key] || key;
}

// --- DOM Elements ---
const profileAvatar = document.getElementById('profile-avatar');
const profileFullName = document.getElementById('profile-full-name');
const profileEmail = document.getElementById('profile-email');
const profilePhoneNumber = document.getElementById('profile-phone-number');
const fullNameInput = document.getElementById('full_name');
const emailInput = document.getElementById('email');
const phoneNumberInput = document.getElementById('phone_number');
const avatarUploadInput = document.getElementById('avatar_upload');
const profileForm = document.getElementById('profile-form');
const editProfileBtn = document.getElementById('edit-profile-btn');
const logoutBtn = document.getElementById('logout-btn');
const ordersTableBody = document.getElementById('orders-table-body');

// --- Functions ---

async function fetchUserProfile() {
    try {
        const userData = await sendRequest(ACCOUNT_CONFIG.PROFILE_API_URL, 'GET');
        displayUserProfile(userData);
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.error_fetching_profile, error);
        alert(ACCOUNT_CONFIG.I18N.uz.error_fetching_profile);
        // Redirect to auth page if not logged in or session expired
        if (error.detail === "Authentication credentials were not provided." || error.code === "token_not_valid") {
            window.location.href = ACCOUNT_CONFIG.AUTH_PAGE_URL;
        }
    }
}

function displayUserProfile(user) {
    if (profileAvatar) profileAvatar.src = user.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
    if (profileFullName) profileFullName.textContent = user.full_name || '';
    if (profileEmail) profileEmail.textContent = user.email || '';
    if (profilePhoneNumber) profilePhoneNumber.textContent = user.phone_number || '';

    if (fullNameInput) fullNameInput.value = user.full_name || '';
    if (emailInput) emailInput.value = user.email || '';
    if (phoneNumberInput) phoneNumberInput.value = user.phone_number || '';

    // Store user data in localStorage for header.js
    localStorage.setItem('username', user.full_name || '');
    localStorage.setItem('avatar_url', user.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR);
    localStorage.setItem('user_email', user.email || '');
    localStorage.setItem('user_role', user.role || 'user');
}

async function handleProfileUpdate(event) {
    event.preventDefault();

    const formData = new FormData();
    formData.append('full_name', fullNameInput.value);
    formData.append('email', emailInput.value);
    formData.append('phone_number', phoneNumberInput.value);

    if (avatarUploadInput.files && avatarUploadInput.files[0]) {
        formData.append('avatar', avatarUploadInput.files[0]);
    }

    try {
        const response = await sendRequest(ACCOUNT_CONFIG.PROFILE_API_URL, 'PATCH', formData, true);
        if (response.message === "reverify") {
            alert(_('reverify_email_phone'));
            // Optionally redirect to a re-verification flow or show a message
        } else {
            alert(_('profile_updated'));
            displayUserProfile(response); // Update UI with new data
        }
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.error_updating_profile, error);
        alert(error.detail || _('error_updating_profile'));
    }
}

async function fetchUserOrders() {
    try {
        const orders = await sendRequest(ACCOUNT_CONFIG.ORDERS_API_URL, 'GET');
        displayUserOrders(orders);
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.error_fetching_orders, error);
        alert(ACCOUNT_CONFIG.I18N.uz.error_fetching_orders);
    }
}

function displayUserOrders(orders) {
    if (!ordersTableBody) return;

    ordersTableBody.innerHTML = ''; // Clear existing rows

    if (orders.length === 0) {
        ordersTableBody.innerHTML = `<tr><td colspan="5" class="no-orders">${_('no_orders')}</td></tr>`;
        return;
    }

    orders.forEach(order => {
        const row = ordersTableBody.insertRow();
        row.innerHTML = `
            <td>${order.id}</td>
            <td>${new Date(order.created_at).toLocaleDateString()}</td>
            <td class="status-${order.status.toLowerCase().replace(' ', '-')}">${order.status}</td>
            <td>${order.total_amount}</td>
            <td><a href="/orders/${order.id}/" class="btn-view-details">Ko'rish</a></td>
        `;
    });
}

async function handleLogout() {
    if (!confirm(_('confirm_logout'))) {
        return;
    }
    try {
        await sendRequest(ACCOUNT_CONFIG.LOGOUT_API_URL, 'POST', {
            csrfmiddlewaretoken: getCookie('csrftoken'),
        });
        alert(_('logout_success'));
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.logout_error, error);
        alert(error.detail || _('logout_error'));
    } finally {
        // Clear all local storage related to auth
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('username');
        localStorage.removeItem('avatar_url');
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_email');
        localStorage.removeItem('currentSessionId');
        localStorage.removeItem('currentIdentifier');
        localStorage.removeItem('showOtpPopup');
        sessionStorage.clear();
        window.location.href = ACCOUNT_CONFIG.AUTH_PAGE_URL;
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    fetchUserProfile();
    fetchUserOrders();

    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
});
