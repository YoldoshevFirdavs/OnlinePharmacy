/**
 * OnlinePharmacy — Account & Form Real-time Validation Module
 * Validates Email and Phone uniqueness asynchronously with error-resilience and debounce.
 * Automatically manages submit button state across user account, admin account,
 * user create/edit, and delivery driver create/edit forms.
 */
(function (global) {
    'use strict';

    // Helper: get CSRF token
    function getCSRFToken() {
        if (global.Dashboard && typeof global.Dashboard.getCSRFToken === 'function') {
            return global.Dashboard.getCSRFToken();
        }
        if (global.DashboardAuth && typeof global.DashboardAuth.getCSRFToken === 'function') {
            return global.DashboardAuth.getCSRFToken();
        }
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.getAttribute('content')) {
            return meta.getAttribute('content');
        }
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    // Helper: create or get feedback container
    function getOrCreateFeedback(input, type) {
        var existing = input.parentNode.querySelector('.validation-feedback, #' + type + '-feedback, #id_' + type + '-feedback');
        if (existing) return existing;

        var feedback = document.createElement('div');
        feedback.className = 'form-text validation-feedback';
        feedback.id = (input.id || ('id_' + type)) + '-feedback';
        feedback.style.fontSize = '0.85rem';
        feedback.style.marginTop = '4px';
        input.parentNode.appendChild(feedback);
        return feedback;
    }

    // Main validator state management per form
    function initFormValidation(form) {
        if (!form || form.__validationInitialized) return;
        form.__validationInitialized = true;

        var submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"], #btnSubmit, #btnSaveSettings, #btn_account_save');
        var inputs = form.querySelectorAll('input[type="email"], input[name="email"], input[name="phone_number"], input[name="phone"], #id_email, #id_phone, #id_phone_number, .check-unique');

        var validationState = new Map();

        function updateSubmitButton() {
            var hasInvalidField = false;
            validationState.forEach(function (isInvalid) {
                if (isInvalid) hasInvalidField = true;
            });

            submitButtons.forEach(function (btn) {
                btn.disabled = hasInvalidField;
                if (hasInvalidField) {
                    btn.classList.add('btn--disabled', 'disabled');
                } else {
                    btn.classList.remove('btn--disabled', 'disabled');
                }
            });
        }

        inputs.forEach(function (input) {
            var isEmail = input.type === 'email' || (input.name && input.name.toLowerCase().indexOf('email') !== -1) || (input.id && input.id.toLowerCase().indexOf('email') !== -1) || input.getAttribute('data-type') === 'email';
            var isPhone = !isEmail && ((input.name && input.name.toLowerCase().indexOf('phone') !== -1) || (input.id && input.id.toLowerCase().indexOf('phone') !== -1) || input.getAttribute('data-type') === 'phone');

            if (!isEmail && !isPhone) return;

            var type = isEmail ? 'email' : 'phone';
            var feedbackEl = getOrCreateFeedback(input, type);
            var debounceTimer = null;
            var initialValue = (input.value || '').trim();

            validationState.set(input, false);

            function validateField() {
                var value = (input.value || '').trim();
                var currentUserId = input.getAttribute('data-user-id') || (form.dataset && form.dataset.userId) || '';

                // If empty or identical to initial value when editing existing user
                if (!value) {
                    input.classList.remove('is-invalid', 'is-valid');
                    feedbackEl.textContent = '';
                    feedbackEl.className = 'form-text validation-feedback';
                    validationState.set(input, false);
                    updateSubmitButton();
                    return;
                }

                if (initialValue && value === initialValue && currentUserId) {
                    input.classList.remove('is-invalid');
                    feedbackEl.textContent = '';
                    feedbackEl.className = 'form-text validation-feedback';
                    validationState.set(input, false);
                    updateSubmitButton();
                    return;
                }

                var endpoint = isEmail ? '/api/v1/users/check_email/' : '/api/v1/users/check_phone/';
                var queryParam = isEmail ? ('email=' + encodeURIComponent(value)) : ('phone_number=' + encodeURIComponent(value));
                if (currentUserId) {
                    queryParam += '&exclude_user_id=' + encodeURIComponent(currentUserId);
                }

                var csrf = getCSRFToken();
                var headers = {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                };
                if (csrf) {
                    headers['X-CSRFToken'] = csrf;
                }

                var postBody = isEmail ? { email: value } : { phone_number: value };
                if (currentUserId) {
                    postBody.exclude_user_id = currentUserId;
                }

                // Try GET first, fallback to POST gracefully
                fetch(endpoint + '?' + queryParam, {
                    method: 'GET',
                    headers: headers
                })
                .then(function (response) {
                    if (response.status === 405) {
                        return fetch(endpoint, {
                            method: 'POST',
                            headers: Object.assign({}, headers, { 'Content-Type': 'application/json' }),
                            body: JSON.stringify(postBody)
                        }).then(function (r) { return r.ok ? r.json() : { exists: false }; });
                    }
                    if (!response.ok) {
                        return { exists: false };
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (data && data.exists) {
                        input.classList.add('is-invalid');
                        input.classList.remove('is-valid');
                        var errorMsg = isEmail ? 'Bu email allaqachon ro‘yxatdan o‘tgan' : 'Bu telefon raqam allaqachon ro‘yxatdan o‘tgan';
                        feedbackEl.textContent = errorMsg;
                        feedbackEl.className = 'form-text validation-feedback text-danger text-error';
                        feedbackEl.style.color = '#dc3545';
                        validationState.set(input, true);
                    } else {
                        input.classList.remove('is-invalid');
                        if (value.length > 3) {
                            input.classList.add('is-valid');
                        }
                        feedbackEl.textContent = '';
                        feedbackEl.className = 'form-text validation-feedback';
                        validationState.set(input, false);
                    }
                    updateSubmitButton();
                })
                .catch(function () {
                    // Safe error fallback: do not block form on network error
                    input.classList.remove('is-invalid');
                    feedbackEl.textContent = '';
                    validationState.set(input, false);
                    updateSubmitButton();
                });
            }

            input.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(validateField, 350);
            });

            input.addEventListener('blur', function () {
                clearTimeout(debounceTimer);
                validateField();
            });
        });
    }

    function initPasswordValidation(form) {
        var newPass = form.querySelector('#id_new_password1, #new_password');
        var confPass = form.querySelector('#id_new_password2, #confirm_password');
        var submitBtn = form.querySelector('button[type="submit"], #btn_password_submit, #btnSaveSettings, #btnSubmit');

        if (newPass && confPass) {
            var matchFeedback = form.querySelector('#password-match-feedback') || (function () {
                var el = document.createElement('div');
                el.className = 'form-text';
                el.id = 'password-match-feedback';
                confPass.parentNode.appendChild(el);
                return el;
            })();

            function validatePasswordMatch() {
                var p1 = newPass.value;
                var p2 = confPass.value;

                if (!p2) {
                    confPass.classList.remove('is-invalid', 'is-valid');
                    matchFeedback.textContent = '';
                    return true;
                }

                if (p1 === p2) {
                    confPass.classList.remove('is-invalid');
                    confPass.classList.add('is-valid');
                    matchFeedback.textContent = 'Parollar mos keldi.';
                    matchFeedback.className = 'form-text text-success';
                    matchFeedback.style.color = '#28a745';
                    return true;
                } else {
                    confPass.classList.remove('is-valid');
                    confPass.classList.add('is-invalid');
                    matchFeedback.textContent = 'Parollar mos kelmadi.';
                    matchFeedback.className = 'form-text text-danger';
                    matchFeedback.style.color = '#dc3545';
                    return false;
                }
            }

            newPass.addEventListener('input', validatePasswordMatch);
            confPass.addEventListener('input', validatePasswordMatch);
        }
    }

    function initAllValidators() {
        var forms = document.querySelectorAll('form');
        forms.forEach(function (form) {
            initFormValidation(form);
            initPasswordValidation(form);
        });

        // Also check standalone inputs outside forms if any
        var standaloneInputs = document.querySelectorAll('input.check-unique:not(form input), #id_email:not(form #id_email), #id_phone:not(form #id_phone)');
        if (standaloneInputs.length > 0) {
            var pseudoForm = document.body;
            initFormValidation(pseudoForm);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllValidators);
    } else {
        initAllValidators();
    }

    // Expose global validator object for dynamic invocations
    global.AccountValidator = {
        init: initAllValidators,
        initForm: initFormValidation
    };

})(typeof window !== 'undefined' ? window : this);