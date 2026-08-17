import { getCookie, sendRequest } from './utils.js'; // Assuming utils.js has getCookie and sendRequest

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

    // Function to display messages in the banner
    function displayMessage(message, type = 'error') {
        messageBanner.textContent = message;
        messageBanner.className = ''; // Clear existing classes
        messageBanner.classList.add('contact-message-banner', type);
        messageBanner.style.display = 'block';
        setTimeout(() => {
            messageBanner.style.display = 'none';
        }, 5000); // Hide after 5 seconds
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
            emailError.textContent = 'Noto‘g‘ri email formati.';
            contactEmailInput.style.borderColor = '#dc3545';
            isValid = false;
        }
        if (contactMessageInput.value.trim() === '') {
            messageError.textContent = 'Xabaringizni kiriting.';
            contactMessageInput.style.borderColor = '#dc3545';
            isValid = false;
        }

        if (!isValid) {
            displayMessage('Iltimos, barcha maydonlarni to‘g‘ri to‘ldiring.', 'error');
            return;
        }

        const formData = {
            name: contactNameInput.value.trim(),
            email: contactEmailInput.value.trim(),
            message: contactMessageInput.value.trim(),
            csrfmiddlewaretoken: getCookie('csrftoken'), // Include CSRF token
        };

        try {
            // Assuming a contact API endpoint exists at /api/v1/contact/
            const response = await sendRequest('/api/v1/contact/', 'POST', formData);

            if (response.success) {
                displayMessage('Xabaringiz muvaffaqiyatli yuborildi!', 'success');
                contactForm.reset(); // Clear the form on success
            } else {
                // Handle specific backend errors if provided
                const errorMessage = response.message || response.detail || 'Xabar yuborishda xatolik yuz berdi.';
                displayMessage(errorMessage, 'error');
            }
        } catch (error) {
            console.error('Contact form submission error:', error);
            if (error.status === 401) {
                displayMessage('Iltimos, avval tizimga kiring.', 'error');
                // Optionally redirect to login page or show login modal
                // window.location.href = '/auth/';
            } else if (error instanceof TypeError && error.message === 'Failed to fetch') {
                displayMessage("Tarmoq xatosi: Serverga ulanib bo'lmadi. Iltimos, internetingizni tekshiring.", 'error');
            } else {
                displayMessage('Xabar yuborishda kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.', 'error');
            }
        }
    });
});
