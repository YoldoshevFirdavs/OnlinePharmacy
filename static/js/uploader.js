document.addEventListener('DOMContentLoaded', () => {
    const avatarInput = document.getElementById('avatarInput');
    const chooseAvatarBtn = document.getElementById('chooseAvatar');
    const avatarPreview = document.getElementById('avatarPreview');
    const avatarEditBtn = document.getElementById('avatarEditBtn');
    const avatarMessage = document.getElementById('avatar-message');

    const MAX_FILE_SIZE_MB = 10;
    const ALLOWED_FILE_TYPES = ['image/png', 'image/jpeg', 'image/jpg'];

    function showMessage(message, type) {
        if (!avatarMessage) return;
        avatarMessage.textContent = message;
        avatarMessage.className = `message-box ${type}`;
        avatarMessage.classList.remove('hidden');
        setTimeout(() => {
            avatarMessage.classList.add('hidden');
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

    if (chooseAvatarBtn && avatarInput && avatarPreview && avatarEditBtn) {
        chooseAvatarBtn.addEventListener('click', () => {
            avatarInput.click();
        });

        avatarEditBtn.addEventListener('click', () => {
            avatarInput.click();
        });

        avatarInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (!file) {
                avatarPreview.src = "{% static 'images/default_avatar.png' %}";
                return;
            }

            // Client-side validation
            if (!ALLOWED_FILE_TYPES.includes(file.type)) {
                showMessage("Faqat JPG, JPEG, PNG formatidagi rasmlar qabul qilinadi.", "error");
                avatarInput.value = ''; // Clear the input
                return;
            }

            if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
                showMessage(`Rasm hajmi ${MAX_FILE_SIZE_MB} MB dan oshmasligi kerak.`, "error");
                avatarInput.value = ''; // Clear the input
                return;
            }

            // Preview image
            const reader = new FileReader();
            reader.onload = (e) => {
                avatarPreview.src = e.target.result;
                // Here you might integrate a cropping library if needed
                // For now, it's a simple preview
            };
            reader.readAsDataURL(file);

            // Automatically upload the avatar after selection and client-side validation
            uploadAvatar(file);
        });
    }

    async function uploadAvatar(file) {
        const formData = new FormData();
        formData.append('avatar', file);

        try {
            // Assuming callApi is globally available from api.js
            const response = await callApi('/api/v1/admin/account/avatar/', 'POST', formData, {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    // 'Content-Type': 'multipart/form-data' is automatically set by fetch when using FormData
                },
                body: formData // Pass formData directly as body
            });

            if (response && response.avatar_url) {
                avatarPreview.src = response.avatar_url;
                showMessage("Profil rasmi muvaffaqiyatli yangilandi!", "success");
                // Optionally update avatar in header if it exists
                const headerAvatar = document.getElementById('header-user-avatar'); // Assuming header has this ID
                if (headerAvatar) headerAvatar.src = response.avatar_url;
            } else {
                showMessage(response.error || "Profil rasmini yuklashda xato yuz berdi.", "error");
            }
        } catch (error) {
            console.error('Avatar yuklashda xato:', error);
            showMessage(`Xatolik yuz berdi: ${error.message || 'Noma\'lum xato'}`, "error");
        }
    }
});