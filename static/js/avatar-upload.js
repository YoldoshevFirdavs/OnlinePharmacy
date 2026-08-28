/**
 * Avatar Upload Handler with Validation & Logging
 * Features: Preview, validation, loading animation, detailed logging
 * Call initAvatarUpload() manually in templates to activate
 */

// Wait for DOM ready and avatar-upload.js to load
document.addEventListener('DOMContentLoaded', function() {
    // Expose init function globally
    window.initAvatarUpload = initAvatarUpload;
});

function initAvatarUpload() {
    const fileInput = document.getElementById('id_avatar');
    const profileAvatarImg = document.getElementById('profileAvatarImg');
    const btnEditAvatar = document.getElementById('btnEditAvatar');
    const avatarPreviewContainer = document.querySelector('.avatar-preview-container');
    
    if (!fileInput || !btnEditAvatar) {
        console.warn('Avatar upload elements not found');
        return;
    }

    // Click button to open file picker
    btnEditAvatar.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener('change', handleAvatarSelect);
}

async function handleAvatarSelect(event) {
    const file = event.target.files[0];
    if (!file) {
        console.log('No file selected');
        return;
    }

    console.log('=== AVATAR UPLOAD START ===');
    console.log('File name:', file.name);
    console.log('File size:', file.size, 'bytes');
    console.log('File type:', file.type);
    console.log('Timestamp:', new Date().toISOString());

    // Show loading animation
    showLoadingAnimation();

    // Validate file
    const validation = validateAvatarFile(file);
    if (!validation.valid) {
        console.error('Validation failed:', validation.error);
        hideLoadingAnimation();
        showError(validation.error);
        return;
    }
    console.log('✓ File validation passed');

    // Show preview
    try {
        const reader = new FileReader();
        reader.onload = async (e) => {
            console.log('✓ FileReader completed, preview data ready');
            const previewUrl = e.target.result;
            
            // Show preview in circular format
            showAvatarPreview(previewUrl);
            
            // Now save to database when user clicks save button
            console.log('Preview shown. Waiting for save confirmation...');
            hideLoadingAnimation();
        };
        reader.readAsDataURL(file);
    } catch (error) {
        console.error('Preview generation failed:', error);
        hideLoadingAnimation();
        showError('Rasm ko\'rinishi yaratishda xatolik');
    }
}

function validateAvatarFile(file) {
    console.log('--- Validating file ---');
    
    // Check file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        return {
            valid: false,
            error: `Fayl turi noto'g'ri. Ruxsat etilgan: ${allowedTypes.join(', ')}`
        };
    }
    console.log('✓ File type valid:', file.type);

    // Check file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
        return {
            valid: false,
            error: `Fayl hajmi 5MB dan oshmasligi kerak. Hozirgi: ${(file.size / 1024 / 1024).toFixed(2)}MB`
        };
    }
    console.log('✓ File size valid:', (file.size / 1024).toFixed(2), 'KB');

    // Validate image dimensions (basic check via Image object)
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
            console.log('✓ Image dimensions valid:', img.width, 'x', img.height);
            resolve({ valid: true });
        };
        img.onerror = () => {
            console.error('Image format invalid or corrupted');
            resolve({
                valid: false,
                error: 'Rasm fayl qayta ishlab bo\'lmadi. Fayl toza emasmi yoki buzilganmi?'
            });
        };
        img.src = URL.createObjectURL(file);
    }).then(result => {
        if (!result.valid) {
            return result;
        }
        return { valid: true };
    });
}

function showAvatarPreview(imageUrl) {
    const profileAvatarImg = document.getElementById('profileAvatarImg');
    if (profileAvatarImg) {
        console.log('Showing preview image');
        profileAvatarImg.src = imageUrl;
        profileAvatarImg.style.border = '3px solid #28a745'; // Green border for preview
    }
    
    // Show hint to click Save button
    const hint = document.createElement('div');
    hint.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #17a2b8;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 9999;
    `;
    hint.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; font-weight: 600;">
            <i class="fa-solid fa-circle-info"></i>
            <span>Rasmni saqlash uchun "Save" tugmasini bosing</span>
        </div>
    `;
    document.body.appendChild(hint);
    console.log('Hint shown: Click Save to upload avatar');
    
    setTimeout(() => {
        hint.remove();
    }, 5000);
}

function showLoadingAnimation() {
    const loader = document.createElement('div');
    loader.id = 'avatar-upload-loader';
    loader.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        ">
            <div style="
                background: white;
                padding: 40px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            ">
                <div style="
                    width: 50px;
                    height: 50px;
                    border: 4px solid #f0f0f0;
                    border-top: 4px solid #6a00f4;
                    border-radius: 50%;
                    margin: 0 auto 16px;
                    animation: spin 1s linear infinite;
                "></div>
                <p style="margin: 0; color: #333; font-weight: 600;">Rasm tekshirilmoqda...</p>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </div>
    `;
    document.body.appendChild(loader);
    console.log('Loading animation shown');
}

function hideLoadingAnimation() {
    const loader = document.getElementById('avatar-upload-loader');
    if (loader) {
        loader.remove();
        console.log('Loading animation hidden');
    }
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #dc3545;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        max-width: 400px;
    `;
    alertDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fa-solid fa-circle-xmark"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(alertDiv);
    console.error('Error shown:', message);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        max-width: 400px;
    `;
    alertDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fa-solid fa-check-circle"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(alertDiv);
    console.log('Success shown:', message);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Log upload results (call from form submission handler)
 */
function logAvatarUpload(success, details = {}) {
    const timestamp = new Date().toISOString();
    console.log('=== AVATAR UPLOAD RESULT ===');
    console.log('Timestamp:', timestamp);
    console.log('Status:', success ? '✓ SUCCESS' : '✗ FAILED');
    console.log('Details:', details);
    console.log('User Agent:', navigator.userAgent);
    console.log('=============================');
}
