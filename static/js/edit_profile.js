let originalUserData = null;

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access_token');
    if (!token) { 
        window.location.href = '/auth/'; 
        return; 
    }

    try {
        const user = await api.getProfile();
        originalUserData = user;
        if (user) {
            document.getElementById('name').value = user.full_name || '';
            document.getElementById('email').value = user.email || '';
            document.getElementById('phone').value = user.phone_number || '';
            document.getElementById('address').value = user.address || '';
            if (user.avatar_url) {
                document.getElementById('avatarPreview').src = user.avatar_url;
            }
        }
    } catch (error) { 
        console.error('Profilni yuklashda xatolik:', error); 
        showAlert("Ma'lumotlarni yuklab bo'lmadi ❌", "error");
    }

    // Avatar Preview
    const avatarInput = document.getElementById('avatarInput');
    const preview = document.getElementById('avatarPreview');
    avatarInput?.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => preview.src = e.target.result;
            reader.readAsDataURL(file);
        }
    });
});

document.getElementById('editForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!originalUserData) return;

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.innerText = "Saqlanmoqda...";

    const formData = new FormData();
    const fullName = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const address = document.getElementById('address').value.trim();
    const avatarFile = document.getElementById('avatarInput').files[0];

    let hasChanges = false;

    // Faqat o'zgargan maydonlarni FormData'ga qo'shamiz
    if (fullName !== (originalUserData.full_name || '')) {
        formData.append('full_name', fullName);
        hasChanges = true;
    }
    
    // Email o'zgargan bo'lsagina yuboramiz, aks holda backend validation xatosi berishi mumkin
    if (email !== (originalUserData.email || '')) {
        formData.append('email', email);
        hasChanges = true;
    }

    if (phone !== (originalUserData.phone_number || '')) {
        formData.append('phone_number', phone);
        hasChanges = true;
    }

    if (address !== (originalUserData.address || '')) {
        formData.append('address', address);
        hasChanges = true;
    }
    
    if (avatarFile) {
        formData.append('avatar', avatarFile);
        hasChanges = true;
    }

    if (!hasChanges) {
        showAlert("Hech qanday o'zgarish qilinmadi ℹ️", "success");
        submitBtn.disabled = false;
        submitBtn.innerText = "O'zgarishlarni saqlash";
        setTimeout(() => window.location.href = '/account/', 1000);
        return;
    }

    const emailChanged = email !== (originalUserData.email || '') && originalUserData.email !== null;
    const phoneChanged = phone !== (originalUserData.phone_number || '');

    try {
        const response = await api.updateProfile(formData);
        
        if (response) {
            if (emailChanged || phoneChanged) {
                localStorage.clear();
                alert("Xavfsizlik yuzasidan (email/telefon o'zgargani uchun) qayta tizimga kiring ✅");
                window.location.href = '/auth/';
            } else {
                showAlert("O‘zgarishlar muvaffaqiyatli saqlandi ✅", "success");
                setTimeout(() => {
                    window.location.href = '/account/';
                }, 1500);
            }
        }
    } catch (err) {
        console.error('Saqlashda xatolik:', err);
        let errorMsg = "Saqlashda xatolik yuz berdi ❌";
        
        if (err.data) {
            if (err.data.detail) {
                errorMsg = err.data.detail;
            } else if (typeof err.data === 'object') {
                const firstKey = Object.keys(err.data)[0];
                const errorVal = err.data[firstKey];
                errorMsg = Array.isArray(errorVal) ? `${firstKey}: ${errorVal[0]}` : `${firstKey}: ${errorVal}`;
            }
        }
        
        showAlert(errorMsg, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "O'zgarishlarni saqlash";
    }
});

function showAlert(msg, type) {
    const box = document.getElementById('alertBox');
    if (box) {
        box.innerText = msg;
        box.className = `custom-alert alert-${type}`;
        box.style.display = 'block';
        setTimeout(() => {
            box.style.display = 'none';
        }, 4000);
    }
}