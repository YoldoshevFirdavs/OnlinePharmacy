document.addEventListener('DOMContentLoaded', function() {
    // Check if ADMIN_CODE_SETTINGS is available
    if (typeof window.ADMIN_CODE_SETTINGS === 'undefined') {
        console.warn("ADMIN_CODE_SETTINGS not found. Telegram code UI will not function.");
        return;
    }

    const settings = window.ADMIN_CODE_SETTINGS;
    const getCodeButton = document.getElementById('get-code-button'); // Assuming this button exists in auth.html or similar
    const codeDisplay = document.getElementById('code-display'); // Element to display the 4-digit code
    const countdownDisplay = document.getElementById('countdown-display'); // Element to display the timer
    const codeInput = document.getElementById('code-input'); // Input field for the code
    const verifyCodeButton = document.getElementById('verify-code-button'); // Button to verify the code
    const telegramLinkContainer = document.getElementById('telegram-link-container'); // Container for the deep link
    const telegramDeepLink = document.getElementById('telegram-deep-link'); // The deep link itself

    let countdownInterval;
    let remainingSeconds = settings.countdownSeconds;

    function updateCountdownDisplay() {
        countdownDisplay.textContent = `(${remainingSeconds} sekund qoldi)`;
        if (remainingSeconds <= settings.thresholds.redSeconds) {
            countdownDisplay.className = 'countdown-red';
        } else if (remainingSeconds <= settings.thresholds.yellowSeconds) {
            countdownDisplay.className = 'countdown-yellow';
        } else {
            countdownDisplay.className = 'countdown-green';
        }
    }

    function startCountdown() {
        remainingSeconds = settings.countdownSeconds;
        updateCountdownDisplay();
        countdownInterval = setInterval(() => {
            remainingSeconds--;
            updateCountdownDisplay();
            if (remainingSeconds <= 0) {
                clearInterval(countdownInterval);
                countdownDisplay.textContent = '(Vaqt tugadi)';
                countdownDisplay.className = 'countdown-expired';
                // Optionally disable code input/verify button
                if (codeInput) codeInput.disabled = true;
                if (verifyCodeButton) verifyCodeButton.disabled = true;
            }
        }, 1000);
    }

    // Function to simulate API call for getting the code
    // In a real scenario, this would be an AJAX call to your backend
    // which then sends the code to Telegram and returns the deep link.
    function requestTelegramCode() {
        // This is a placeholder. Replace with actual API call.
        // Example: fetch('/api/v1/users/telegram-login-request', { method: 'POST', body: JSON.stringify({ /* user info */ }) })
        // .then(response => response.json())
        // .then(data => {
        //     const botUsername = data.telegramBotUsername || settings.telegramBotUsername;
        //     const startParam = data.startParam || 'manual'; // Backend should return this
        //     const deepLinkUrl = `https://t.me/${botUsername}?${settings.telegramStartParamPrefix}=${startParam}`;
        //     telegramDeepLink.href = deepLinkUrl;
        //     telegramDeepLink.textContent = `Kodni olish uchun Telegram botga o'ting`;
        //     telegramLinkContainer.style.display = 'block';
        //
        //     // Open in new tab
        //     const newTab = window.open('about:blank', '_blank');
        //     if (newTab) {
        //         newTab.location.href = deepLinkUrl;
        //     } else {
        //         alert("Yangi tab ochilmadi. Iltimos, brauzeringizda pop-up blokirovkalashni o'chiring va linkni qo'lda bosing.");
        //     }
        //
        //     codeDisplay.textContent = '****'; // Code will be entered manually
        //     startCountdown();
        //     getCodeButton.disabled = true;
        //     getCodeButton.textContent = 'Kod yuborildi';
        // })
        // .catch(error => {
        //     console.error("Error requesting Telegram code:", error);
        //     alert("Kod so'rashda xato yuz berdi. Iltimos, qayta urinib ko'ring.");
        // });

        // --- Mockup for demonstration ---
        const mockCode = Math.floor(1000 + Math.random() * 9000).toString(); // Simulate 4-digit code
        const mockStartParam = 'mock_session_id_123'; // Simulate session ID from backend
        const botUsername = settings.telegramBotUsername;
        const deepLinkUrl = `https://t.me/${botUsername}?${settings.telegramStartParamPrefix}=${mockStartParam}`;

        telegramDeepLink.href = deepLinkUrl;
        telegramDeepLink.textContent = `Kodni olish uchun Telegram botga o'ting`;
        telegramLinkContainer.style.display = 'block';

        const newTab = window.open('about:blank', '_blank');
        if (newTab) {
            newTab.location.href = deepLinkUrl;
        } else {
            alert("Yangi tab ochilmadi. Iltimos, brauzeringizda pop-up blokirovkalashni o'chiring va linkni qo'lda bosing.");
        }

        codeDisplay.textContent = '****'; // Display masked code
        startCountdown();
        getCodeButton.disabled = true;
        getCodeButton.textContent = 'Kod yuborildi';
        // End Mockup
    }

    if (getCodeButton) {
        getCodeButton.addEventListener('click', requestTelegramCode);
    }

    // Example verification (replace with actual API call)
    if (verifyCodeButton) {
        verifyCodeButton.addEventListener('click', () => {
            const enteredCode = codeInput.value;
            if (enteredCode.length === settings.codeLength) {
                alert(`Kiritilgan kod: ${enteredCode}. Tekshirilmoqda...`);
                // Here you would send the code to your backend for verification
                // fetch('/api/v1/users/verify-telegram-code', { method: 'POST', body: JSON.stringify({ code: enteredCode, sessionId: mockStartParam }) })
                // .then(response => response.json())
                // .then(data => {
                //     if (data.success) {
                //         alert("Kod muvaffaqiyatli tasdiqlandi!");
                //         // Redirect or log in user
                //     } else {
                //         alert("Noto'g'ri kod yoki vaqt tugadi. Qayta urinib ko'ring.");
                //     }
                // })
                // .catch(error => {
                //     console.error("Error verifying code:", error);
                //     alert("Kod tekshirishda xato yuz berdi.");
                // });
            } else {
                alert(`Iltimos, ${settings.codeLength} xonali kodni kiriting.`);
            }
        });
    }
});