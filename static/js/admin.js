document.addEventListener('DOMContentLoaded', () => {
    const adminSettingsForm = document.getElementById('admin-settings-form');
    const settingsMessage = document.getElementById('settings-message');

    function showMessage(message, type) {
        if (!settingsMessage) return;
        settingsMessage.textContent = message;
        settingsMessage.className = `message-box ${type}`;
        settingsMessage.classList.remove('hidden');
        setTimeout(() => {
            settingsMessage.classList.add('hidden');
        }, 5000);
    }

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

    // --- Admin Dashboard Logic ---
    async function fetchAdminStats() {
        try {
            // Assuming callApi is globally available from api.js
            const stats = await callApi('/api/v1/admin/stats/', 'GET');
            if (stats) {
                const totalUsersElement = document.getElementById('total-users');
                const totalOrdersElement = document.getElementById('total-orders');
                const totalRevenueElement = document.getElementById('total-revenue');

                if (totalUsersElement) totalUsersElement.textContent = stats.total_users || '0';
                if (totalOrdersElement) totalOrdersElement.textContent = stats.total_orders || '0';
                if (totalRevenueElement) totalRevenueElement.textContent = `${stats.total_revenue || '0'} so'm`;
            }
        } catch (error) {
            console.error('Admin statistikalarini yuklashda xato:', error);
            // Only show alert if on the dashboard page
            if (window.location.pathname === '/dashboard/') {
                alert(`Xatolik yuz berdi: ${error.message || 'Statistikalarni yuklashda noma\'lum xato.'}`);
            }
        }
    }

    // --- Admin Settings Logic ---
    if (adminSettingsForm) {
        adminSettingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const siteName = document.getElementById('site-name').value;
            const contactEmail = document.getElementById('contact-email').value;
            const supportPhone = document.getElementById('support-phone').value;
            const adminEmail = document.getElementById('admin-email').value;
            const adminPassword = document.getElementById('admin-password').value;
            const adminPasswordConfirm = document.getElementById('admin-password-confirm').value;

            if (adminPassword && adminPassword !== adminPasswordConfirm) {
                showMessage("Parollar mos kelmadi!", "error");
                return;
            }

            const payload = {
                site_name: siteName,
                contact_email: contactEmail,
                support_phone: supportPhone,
                admin_email: adminEmail,
            };

            if (adminPassword) {
                payload.admin_password = adminPassword;
            }

            try {
                // Assuming callApi is globally available from api.js
                const response = await callApi('/api/v1/admin/settings/', 'POST', payload, {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                });

                if (response) {
                    showMessage("Sozlamalar muvaffaqiyatli saqlandi!", "success");
                    // Optionally clear password fields after successful save
                    document.getElementById('admin-password').value = '';
                    document.getElementById('admin-password-confirm').value = '';
                }
            } catch (error) {
                console.error('Sozlamalarni saqlashda xato:', error);
                showMessage(`Xatolik yuz berdi: ${error.message || 'Noma\'lum xato'}`, "error");
            }
        });
    }

    // Function to load current settings (if an API endpoint exists for GET)
    async function loadCurrentSettings() {
        if (window.location.pathname === '/dashboard/settings/') {
            try {
                // Assuming there's a GET endpoint for admin settings
                const settings = await callApi('/api/v1/admin/settings/', 'GET');
                if (settings) {
                    const siteNameElement = document.getElementById('site-name');
                    const contactEmailElement = document.getElementById('contact-email');
                    const supportPhoneElement = document.getElementById('support-phone');
                    const adminEmailElement = document.getElementById('admin-email');

                    if (siteNameElement) siteNameElement.value = settings.site_name || '';
                    if (contactEmailElement) contactEmailElement.value = settings.contact_email || '';
                    if (supportPhoneElement) supportPhoneElement.value = settings.support_phone || '';
                    if (adminEmailElement) adminEmailElement.value = settings.admin_email || '';
                }
            } catch (error) {
                console.error('Sozlamalarni yuklashda xato:', error);
                showMessage(`Sozlamalarni yuklashda xatolik: ${error.message || 'Noma\'lum xato'}`, "error");
            }
        }
    }

    // --- Sidebar navigation active state ---
    const currentPath = window.location.pathname;
    document.querySelectorAll('.admin-sidebar nav a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // --- Initial data load based on page ---
    if (currentPath === '/dashboard/') {
        fetchAdminStats();
    } else if (currentPath === '/dashboard/settings/') {
        loadCurrentSettings();
    }
});