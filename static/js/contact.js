import { getCookie, sendRequest } from './utils.js';

document.addEventListener('DOMContentLoaded', () => {
    const contactForm = document.getElementById('contact-form');
    const contactNameInput = document.getElementById('contact-name');
    const contactEmailInput = document.getElementById('contact-email');
    const contactMessageInput = document.getElementById('contact-message');
    const nameError = document.getElementById('name-error');
    const emailError = document.getElementById('email-error');
    const messageError = document.getElementById('message-error');
    const messageBanner = document.getElementById('contact-message-banner');

    // Null-safe check for all elements
    if (!contactForm || !contactNameInput || !contactEmailInput || !contactMessageInput || !nameError || !emailError || !messageError || !messageBanner) {
        console.error('One or more contact form elements not found. Contact form functionality disabled.');
        return;
    }

    // Show message banner at top
    function showMessageBanner(message, isSuccess = true) {
        messageBanner.textContent = message;
        messageBanner.className = isSuccess ? 'success' : 'error';
        messageBanner.style.display = 'block';
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageBanner.style.display = 'none';
        }, 5000);
    }

    // Function to clear all error messages
    function clearErrors() {
        nameError.textContent = '';
        emailError.textContent = '';
        messageError.textContent = '';
        contactNameInput.style.borderColor = '#ddd';
        contactEmailInput.style.borderColor = '#ddd';
        contactMessageInput.style.borderColor = '#ddd';
    }

    // Basic email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearErrors(); // Clear previous errors

        let isValid = true;

        // Client-side validation
        if (contactNameInput.value.trim() === '') {
            nameError.textContent = 'Ismingizni kiriting.';
            contactNameInput.style.borderColor = '#dc3545';
            isValid = false;
        }
        if (contactEmailInput.value.trim() === '') {
            emailError.textContent = 'Emailingizni kiriting.';
            contactEmailInput.style.borderColor = '#dc3545';
            isValid = false;
        } else if (!emailRegex.test(contactEmailInput.value.trim())) {
            emailError.textContent = 'Noto\'g\'ri email formati.';
            contactEmailInput.style.borderColor = '#dc3545';
            isValid = false;
        }
        if (contactMessageInput.value.trim() === '') {
            messageError.textContent = 'Xabaringizni kiriting.';
            contactMessageInput.style.borderColor = '#dc3545';
            isValid = false;
        }

        if (!isValid) {
            showMessageBanner('Iltimos, barcha maydonlarni to\'g\'ri to\'ldiring.', false);
            return;
        }

        const formData = {
            name: contactNameInput.value.trim(),
            email: contactEmailInput.value.trim(),
            message: contactMessageInput.value.trim(),
            csrfmiddlewaretoken: getCookie('csrftoken'), // Include CSRF token
        };

        try {
            console.log("📤 Sending contact form...", formData);
            
            // Submit to contact API endpoint at /api/v1/products/contact/
            const response = await sendRequest('/api/v1/products/contact/', 'POST', formData);

            console.log("✅ Response:", response);
            
            if (response.success) {
                // Show success message at top
                showMessageBanner('✅ Xabaringiz muvaffaqiyatli yuborildi! Tez orada javob beramiz.', true);
                
                // Clear form fields
                contactForm.reset();
                clearErrors();
            } else {
                // Handle specific backend errors if provided
                const errorMessage = response.message || response.detail || 'Xabar yuborishda xatolik yuz berdi.';
                showMessageBanner('❌ ' + errorMessage, false);
            }
        } catch (error) {
            console.error('❌ Contact form submission error:', error);
            if (error.status === 401) {
                showMessageBanner('❌ Iltimos, avval tizimga kiring.', false);
                // Optionally redirect to login page
                // window.location.href = '/auth/';
            } else if (error instanceof TypeError && error.message === 'Failed to fetch') {
                showMessageBanner('❌ Tarmoq xatosi: Serverga ulanib bo\'lmadi.', false);
            } else {
                showMessageBanner('❌ Xabar yuborishda kutilmagan xatolik yuz berdi.', false);
            }
        }
    });
});
