document.addEventListener('DOMContentLoaded', () => {
    window.footerSubscribe = async function(event) {
        event.preventDefault(); // Prevent default form submission

        const emailInput = document.getElementById('footer-email');
        const subscribeMessage = document.getElementById('subscribe-message');
        const email = emailInput.value.trim();

        subscribeMessage.textContent = ''; // Clear previous messages

        if (!email) {
            subscribeMessage.style.color = 'orange';
            subscribeMessage.textContent = 'Please enter your email address.';
            return;
        }

        // Basic email format validation
        if (!/\S+@\S+\.\S+/.test(email)) {
            subscribeMessage.style.color = 'orange';
            subscribeMessage.textContent = 'Please enter a valid email address.';
            return;
        }

        try {
            // Ensure window.api is available and has the subscribe method
            if (!window.api || typeof window.api.subscribe !== 'function') {
                console.error("window.api.subscribe is not defined. Make sure api.js is loaded correctly.");
                subscribeMessage.style.color = 'red';
                subscribeMessage.textContent = 'Subscription service is not available.';
                return;
            }

            const response = await window.api.subscribe({ email: email });

            if (response && response.status === 'success') {
                subscribeMessage.style.color = 'green';
                subscribeMessage.textContent = 'Successfully subscribed!';
                emailInput.value = ''; // Clear the input field
            } else {
                // Handle API-specific error messages if available
                subscribeMessage.style.color = 'red';
                subscribeMessage.textContent = response.message || 'Subscription failed. Please try again.';
            }
        } catch (error) {
            console.error('Error during subscription:', error);
            subscribeMessage.style.color = 'red';
            subscribeMessage.textContent = 'An error occurred. Please try again later.';
        }
    };
});