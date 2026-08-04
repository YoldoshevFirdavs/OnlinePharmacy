document.addEventListener('DOMContentLoaded', function() {
    const headerUserBlock = document.getElementById('header-user-block');
    const headerUserAvatar = document.getElementById('header-user-avatar');
    const headerUserName = document.getElementById('header-user-name');

    if (headerUserBlock && headerUserAvatar && headerUserName) {
        headerUserBlock.addEventListener('click', async function(event) {
            event.preventDefault(); // Prevent default link behavior

            // Check if callApi is defined (from api.js)
            if (typeof callApi !== 'function') {
                console.error('callApi function is not defined. Make sure api.js is loaded.');
                window.location.href = '/account/'; // Fallback to default account page
                return;
            }

            try {
                const user = await callApi('/api/v1/users/me/', 'GET', { credentials: 'include', headers: { 'X-Requested-With': 'XMLHttpRequest' } }); // Fetch user data
                if (user && user.id) {
                    let redirectUrl = '/account/'; // Default redirect

                    if (user.role === 'deliver') {
                        redirectUrl = '/dashboard/delivery/'; // Assuming this is the correct URL
                    } else if (user.role === 'admin') {
                        redirectUrl = '/dashboard/admin/'; // Assuming this is the correct URL
                    }
                    window.location.href = redirectUrl;
                } else {
                    // If user data is not valid, redirect to login
                    window.location.href = '/auth/';
                }
            } catch (error) {
                console.error('Error fetching user data for routing:', error);
                // Handle 401 (Unauthorized) or other errors
                if (error.message && error.message.includes('401')) {
                    window.location.href = '/auth/'; // Redirect to login page
                } else {
                    window.location.href = '/account/'; // Fallback to default account page
                }
            }
        });
    }
});