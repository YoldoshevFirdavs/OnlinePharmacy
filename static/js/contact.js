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

    // Create modal HTML if it doesn't exist
    function ensureModalExists() {
        if (!document.getElementById('contact-modal')) {
            const modalHTML = `
                <div id="contact-modal" class="contact-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; display:flex; align-items:center; justify-content:center;">
                    <div class="contact-modal-content" style="background:white; border-radius:16px; padding:40px; text-align:center; box-shadow:0 10px 40px rgba(0,0,0,0.3); max-width:400px; animation:slideIn 0.3s ease-out;">
                        <div id="modal-icon" style="font-size:60px; margin-bottom:20px;"></div>
                        <h2 id="modal-title" style="font-size:24px; font-weight:600; margin-bottom:10px; color:#333;"></h2>
                        <p id="modal-message" style="font-size:16px; color:#666; margin-bottom:20px;"></p>
                        <button id="modal-close" class="btn-primary-gradient" style="padding:12px 30px; border:none; border-radius:8px; cursor:pointer; font-weight:600;">Yopish</button>
                    </div>
                </div>
                <style>
                    @keyframes slideIn {
                        from {
                            opacity: 0;
                            transform: translateY(-20px);
                        }
                        to {
                            opacity: 1;
                            transform: translateY(0);
                        }
                    }
                    
                    .contact-modal {
                        animation: fadeIn 0.3s ease-out;
                    }
                    
                    @keyframes fadeIn {
                        from {
                            opacity: 0;
                        }
                        to {
                            opacity: 1;
                        }
                    }
                </style>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
    }

    // Show modal with success/error
    function showModal(title, message, isSuccess = true) {
        ensureModalExists();
        
        const modal = document.getElementById('contact-modal');
        const modalIcon = document.getElementById('modal-icon');
        const modalTitle = document.getElementById('modal-title');
        const modalMessage = document.getElementById('modal-message');
        const modalClose = document.getElementById('modal-close');
        
        // Set icon and colors based on success/error
        if (isSuccess) {
            modalIcon.innerHTML = '✅';
            modalIcon.style.color = '#28a745';
            modalTitle.style.color = '#28a745';
            modalClose.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
        } else {
            modalIcon.innerHTML = '❌';
            modalIcon.style.color = '#dc3545';
            modalTitle.style.color = '#dc3545';
            modalClose.style.background = 'linear-gradient(135deg, #dc3545, #c82333)';
        }
        
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modal.style.display = 'flex';
        
        // Close modal on button click
        modalClose.onclick = () => {
            modal.style.display = 'none';
        };
        
        // Close modal on background click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
        
        // Auto close after 5 seconds for success
        if (isSuccess) {
            setTimeout(() => {
                modal.style.display = 'none';
            }, 5000);
        }
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
            emailError.textContent = 'Noto'g'ri email formati.';
            contactEmailInput.style.borderColor = '#dc3545';
            isValid = false;
        }
        if (contactMessageInput.value.trim() === '') {
            messageError.textContent = 'Xabaringizni kiriting.';
            contactMessageInput.style.borderColor = '#dc3545';
            isValid = false;
        }

        if (!isValid) {
            showModal('Xatolik!', 'Iltimos, barcha maydonlarni to\'g\'ri to\'ldiring.', false);
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
                showModal('Muvaffaqiyatli!', 'Xabaringiz muvaffaqiyatli yuborildi! Tez orada javob beramiz.', true);
                contactForm.reset(); // Clear the form on success
            } else {
                // Handle specific backend errors if provided
                const errorMessage = response.message || response.detail || 'Xabar yuborishda xatolik yuz berdi.';
                showModal('Xatolik!', errorMessage, false);
            }
        } catch (error) {
            console.error('❌ Contact form submission error:', error);
            if (error.status === 401) {
                showModal('Xatolik!', 'Iltimos, avval tizimga kiring.', false);
                // Optionally redirect to login page or show login modal
                // window.location.href = '/auth/';
            } else if (error instanceof TypeError && error.message === 'Failed to fetch') {
                showModal('Tarmoq Xatosi!', "Serverga ulanib bo'lmadi. Iltimos, internetingizni tekshiring.", false);
            } else {
                showModal('Xatolik!', 'Xabar yuborishda kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.', false);
            }
        }
    });
});
