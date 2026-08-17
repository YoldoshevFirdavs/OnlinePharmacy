document.addEventListener('DOMContentLoaded', function() {
    // --- Password Validation (for account.html and potentially settings.html if password fields are present) ---
    const passwordInput = document.getElementById('id_new_password1');
    const passwordConfirmInput = document.getElementById('id_new_password2');
    const passwordStrengthFeedback = document.getElementById('password-strength-feedback');
    const passwordMatchFeedback = document.getElementById('password-match-feedback');
    const passwordChangeForm = document.getElementById('password-change-form');
    const passwordSubmitButton = passwordChangeForm ? passwordChangeForm.querySelector('button[type="submit"]') : null;

    function checkPasswordStrength() {
        if (!passwordInput || !passwordStrengthFeedback) return true;

        const password = passwordInput.value;
        let feedbackText = '';
        let isValid = true;

        if (password.length < 8) {
            feedbackText += 'Parol kamida 8 ta belgidan iborat bo\'lishi kerak. ';
            isValid = false;
        }
        if (!/[A-Z]/.test(password)) {
            feedbackText += 'Parolda kamida bitta katta harf bo\'lishi kerak. ';
            isValid = false;
        }
        if (!/[a-z]/.test(password)) {
            feedbackText += 'Parolda kamida bitta kichik harf bo\'lishi kerak. ';
            isValid = false;
        }
        if (!/[0-9]/.test(password)) {
            feedbackText += 'Parolda kamida bitta raqam bo\'lishi kerak. ';
            isValid = false;
        }
        if (!/[^A-Za-z0-9]/.test(password)) {
            feedbackText += 'Parolda kamida bitta maxsus belgi bo\'lishi kerak. ';
            isValid = false;
        }

        if (password.length === 0) {
            feedbackText = '';
            isValid = true;
            passwordStrengthFeedback.className = 'form-text';
        } else if (isValid) {
            feedbackText = 'Parol kuchi: Yaxshi';
            passwordStrengthFeedback.className = 'form-text text-success';
        } else {
            passwordStrengthFeedback.className = 'form-text text-danger';
        }

        passwordStrengthFeedback.textContent = feedbackText;
        return isValid;
    }

    function checkPasswordMatch() {
        if (!passwordInput || !passwordConfirmInput || !passwordMatchFeedback) return true;

        const password = passwordInput.value;
        const confirmPassword = passwordConfirmInput.value;
        let isValid = true;

        if (password.length > 0 && confirmPassword.length > 0 && password !== confirmPassword) {
            passwordMatchFeedback.textContent = 'Parollar mos kelmadi.';
            passwordMatchFeedback.className = 'form-text text-danger';
            isValid = false;
        } else if (password.length > 0 && confirmPassword.length > 0 && password === confirmPassword) {
            passwordMatchFeedback.textContent = 'Parollar mos keldi.';
            passwordMatchFeedback.className = 'form-text text-success';
        } else {
            passwordMatchFeedback.textContent = '';
            passwordMatchFeedback.className = 'form-text';
        }
        return isValid;
    }

    function validatePasswordForm() {
        if (!passwordInput && !passwordConfirmInput) return true; // No password fields, so form is valid

        const isStrengthValid = checkPasswordStrength();
        const isMatchValid = checkPasswordMatch();

        return isStrengthValid && isMatchValid;
    }

    if (passwordInput && passwordConfirmInput) {
        passwordInput.addEventListener('input', () => {
            validatePasswordForm();
            updateAllSubmitButtons();
        });
        passwordConfirmInput.addEventListener('input', () => {
            validatePasswordForm();
            updateAllSubmitButtons();
        });
    }

    // --- Email and Phone Validation (for account.html, settings.html, and admin pages) ---
    const emailInput = document.getElementById('id_email');
    const phoneInput = document.getElementById('id_phone');
    const emailFeedback = document.getElementById('email-feedback');
    const phoneFeedback = document.getElementById('phone-feedback');

    let emailCheckTimeout;
    let phoneCheckTimeout;

    // Helper to get CSRF token
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

    function checkAvailability(inputElement, feedbackElement, endpoint) {
        if (!inputElement || !feedbackElement) return;

        const value = inputElement.value.trim();
        const fieldName = inputElement.id.includes('email') ? 'email' : 'phone_number';
        const currentUserId = inputElement.dataset.userId || null; // Get user ID from data attribute

        feedbackElement.textContent = '';
        feedbackElement.className = 'form-text'; // Reset class

        if (value.length === 0) {
            updateAllSubmitButtons();
            return;
        }

        feedbackElement.textContent = 'Tekshirilmoqda...';
        feedbackElement.className = 'form-text text-muted';

        const data = { [fieldName]: value };
        if (currentUserId) {
            data['exclude_user_id'] = currentUserId;
        }

        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                feedbackElement.textContent = `${fieldName === 'email' ? 'Bu email' : 'Bu telefon raqam'} allaqachon ro'yxatdan o'tgan.`;
                feedbackElement.className = 'form-text text-danger';
            } else {
                feedbackElement.textContent = `${fieldName === 'email' ? 'Email' : 'Telefon raqam'} mavjud.`;
                feedbackElement.className = 'form-text text-success';
            }
            updateAllSubmitButtons();
        })
        .catch(error => {
            console.error('Error during availability check:', error);
            feedbackElement.textContent = 'Tekshirishda xatolik yuz berdi.';
            feedbackElement.className = 'form-text text-warning';
            updateAllSubmitButtons();
        });
    }

    if (emailInput) {
        emailInput.addEventListener('input', function() {
            clearTimeout(emailCheckTimeout);
            emailCheckTimeout = setTimeout(() => {
                checkAvailability(emailInput, emailFeedback, '/api/v1/users/check_email/');
            }, 500);
        });
    }

    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            clearTimeout(phoneCheckTimeout);
            phoneCheckTimeout = setTimeout(() => {
                checkAvailability(phoneInput, phoneFeedback, '/api/v1/users/check_phone/');
            }, 500);
        });
    }

    // --- Universal Submit Button State Updater ---
    function updateAllSubmitButtons() {
        let isPasswordFormValid = true;
        if (passwordInput && passwordConfirmInput) {
            isPasswordFormValid = validatePasswordForm();
        }

        let isEmailValid = true;
        if (emailInput && emailFeedback && emailFeedback.classList.contains('text-danger')) {
            isEmailValid = false;
        }

        let isPhoneValid = true;
        if (phoneInput && phoneFeedback && phoneFeedback.classList.contains('text-danger')) {
            isPhoneValid = false;
        }

        // Handle password change form button
        if (passwordSubmitButton) {
            passwordSubmitButton.disabled = !isPasswordFormValid;
        }

        // Handle main user details form button (for account.html)
        const userDetailsForm = document.getElementById('user-details-form');
        const userDetailsSubmitButton = userDetailsForm ? userDetailsForm.querySelector('button[type="submit"]') : null;
        if (userDetailsSubmitButton) {
            userDetailsSubmitButton.disabled = !(isEmailValid && isPhoneValid);
        }

        // Handle admin settings form button (for settings.html and other admin forms)
        const adminSettingsForm = document.getElementById('settingsForm');
        const adminSettingsSubmitButton = adminSettingsForm ? adminSettingsForm.querySelector('button[type="submit"]') : null;
        if (adminSettingsSubmitButton) {
            adminSettingsSubmitButton.disabled = !(isEmailValid && isPhoneValid);
        }

        // Handle general admin forms (e.g., user create/edit, delivery create/edit)
        // This targets any submit button within a form that has email/phone inputs
        const generalForms = document.querySelectorAll('form:not(#password-change-form):not(#user-details-form):not(#settingsForm)');
        generalForms.forEach(form => {
            const formEmailInput = form.querySelector('#id_email');
            const formPhoneInput = form.querySelector('#id_phone');
            const formEmailFeedback = form.querySelector('#email-feedback');
            const formPhoneFeedback = form.querySelector('#phone-feedback');
            const formSubmitButton = form.querySelector('input[type="submit"], button[type="submit"]');

            if (formSubmitButton) {
                let formSpecificEmailValid = true;
                if (formEmailInput && formEmailFeedback && formEmailFeedback.classList.contains('text-danger')) {
                    formSpecificEmailValid = false;
                }

                let formSpecificPhoneValid = true;
                if (formPhoneInput && formPhoneFeedback && formPhoneFeedback.classList.contains('text-danger')) {
                    formSpecificPhoneValid = false;
                }
                formSubmitButton.disabled = !(formSpecificEmailValid && formSpecificPhoneValid);
            }
        });
    }

    // Initial state update on page load
    updateAllSubmitButtons();
});