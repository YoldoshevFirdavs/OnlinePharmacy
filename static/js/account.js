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
    const token = localStorage.getItem('access_token');
    const headers = {
        'Accept': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
    }

    const config = {
        method: method,
        headers: headers,
        credentials: 'include'
    };

    if (data) {
        if (isFormData) {
            // Let browser set Content-Type for FormData with boundary
            config.body = data;
        } else {
            headers['Content-Type'] = 'application/json';
            config.body = JSON.stringify(data);
        }
    }
    
    let absoluteUrl = url;
    if (url.startsWith('/')) {
        absoluteUrl = window.location.origin + url;
    }

    const response = await fetch(absoluteUrl, config);

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
const profileViewMode = document.getElementById('profile-view-mode');
const profileEditMode = document.getElementById('profile-edit-mode');

const profileAvatarDisplay = document.getElementById('profile-avatar-display');
const profileFullNameDisplay = document.getElementById('profile-full-name-display');
const profileEmailDisplay = document.getElementById('profile-email-display');
const profilePhoneNumberDisplay = document.getElementById('profile-phone-number-display');

const profileAvatarPreview = document.getElementById('profile-avatar-preview');
const fullNameInput = document.getElementById('full_name');
const emailInput = document.getElementById('email');
const phoneNumberInput = document.getElementById('phone_number');
const avatarUploadInput = document.getElementById('avatar_upload');
const profileForm = document.getElementById('profile-form');

const editProfileBtn = document.getElementById('edit-profile-btn');
const cancelEditBtn = document.getElementById('cancel-edit-btn');
const logoutBtn = document.getElementById('logout-btn');
const ordersTableBody = document.getElementById('orders-table-body');

let currentUserData = null; // To store fetched user data

// --- Functions ---

function toggleEditMode(enable) {
    if (enable) {
        profileViewMode.style.display = 'none';
        profileEditMode.style.display = 'block';
        // Populate form fields when entering edit mode
        if (currentUserData) {
            fullNameInput.value = currentUserData.full_name || '';
            emailInput.value = currentUserData.email || '';
            phoneNumberInput.value = currentUserData.phone_number || '';
            profileAvatarPreview.src = currentUserData.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
        }
    } else {
        profileViewMode.style.display = 'block';
        profileEditMode.style.display = 'none';
        // Reset avatar upload input when exiting edit mode without saving
        avatarUploadInput.value = '';
        profileAvatarPreview.src = currentUserData.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
    }
}

async function fetchUserProfile() {
    try {
        const userData = await sendRequest(ACCOUNT_CONFIG.PROFILE_API_URL, 'GET');
        currentUserData = userData; // Store fetched data
        displayUserProfile(userData);
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.error_fetching_profile, error);
        // Redirect to auth page if not logged in or session expired
        window.location.href = ACCOUNT_CONFIG.AUTH_PAGE_URL;
    }
}

function displayUserProfile(user) {
    // Update view mode elements
    if (profileAvatarDisplay) profileAvatarDisplay.src = user.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
    if (profileFullNameDisplay) profileFullNameDisplay.textContent = user.full_name || '';
    if (profileEmailDisplay) profileEmailDisplay.textContent = user.email || '';
    if (profilePhoneNumberDisplay) profilePhoneNumberDisplay.textContent = user.phone_number || '';

    // Update edit mode elements (for initial load or after save)
    if (profileAvatarPreview) profileAvatarPreview.src = user.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
    if (fullNameInput) fullNameInput.value = user.full_name || '';
    if (emailInput) emailInput.value = user.email || '';
    if (phoneNumberInput) phoneNumberInput.value = user.phone_number || '';

    // Store user data in localStorage for header.js
    localStorage.setItem('username', user.full_name || ''); // OK
    localStorage.setItem('avatar_url', user.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR); // OK
    localStorage.setItem('user_email', user.email || ''); // OK
    localStorage.setItem('user_role', user.role || 'user'); // OK
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
            currentUserData = response; // Update stored data
            displayUserProfile(response); // Update UI with new data
            toggleEditMode(false); // Switch back to view mode
        }
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.error_updating_profile, error);
        alert(error.detail || _('error_updating_profile'));
    }
}

function handleAvatarUploadChange() {
    const file = avatarUploadInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            profileAvatarPreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        profileAvatarPreview.src = currentUserData.avatar || ACCOUNT_CONFIG.DEFAULT_AVATAR;
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
        await sendRequest('/api/v1/users/logout/', 'POST');
        await sendRequest('/api/v1/users/logout/jwt/', 'POST');
        alert(_('logout_success'));
    } catch (error) {
        console.error(ACCOUNT_CONFIG.I18N.uz.logout_error, error);
        alert(error.detail || _('logout_error'));
    } finally {
        [
            'access_token', 'refresh_token', 'username', 'avatar_url', 'user_role',
            'user_email', 'user_id', 'currentSessionId', 'currentIdentifier',
            'currentAuthMethod', 'showOtpPopup'
        ].forEach(key => localStorage.removeItem(key));
        sessionStorage.clear();
        window.location.replace(ACCOUNT_CONFIG.AUTH_PAGE_URL);
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    fetchUserProfile();
    fetchUserOrders();

    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', () => toggleEditMode(true));
    }
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => toggleEditMode(false));
    }
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
    if (avatarUploadInput) {
        avatarUploadInput.addEventListener('change', handleAvatarUploadChange);
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
});