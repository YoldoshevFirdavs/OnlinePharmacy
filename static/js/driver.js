// changed: driver dashboard JS
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'driver-dashboard') {
        return;
    }

    const API_BASE_URL = '/api/v1'; // Adjust if your API is on a different path
    let authToken = localStorage.getItem('accessToken');
    let refreshToken = localStorage.getItem('refreshToken');
    let locationTrackingInterval = null;
    let waitTimerInterval = null;
    let waitStartTime = null;
    let currentOrderId = null;

    // --- Utility Functions ---
    function getAuthHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        };
    }

    async function refreshTokenIfNeeded() {
        if (!refreshToken) {
            console.error("No refresh token available. Redirecting to login.");
            window.location.href = '/login/'; // Assuming a login page
            return false;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/users/token/refresh/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh: refreshToken })
            });
            if (!response.ok) {
                throw new Error('Failed to refresh token');
            }
            const data = await response.json();
            authToken = data.access;
            localStorage.setItem('accessToken', authToken);
            // Optionally, if refresh token rotation is enabled, update refresh token too
            if (data.refresh) {
                refreshToken = data.refresh;
                localStorage.setItem('refreshToken', refreshToken);
            }
            return true;
        } catch (error) {
            console.error("Token refresh failed:", error);
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            window.location.href = '/login/';
            return false;
        }
    }

    async function authenticatedFetch(url, options = {}) {
        let response = await fetch(url, { ...options, headers: { ...getAuthHeaders(), ...options.headers } });
        if (response.status === 401) { // Unauthorized, try refreshing token
            const refreshed = await refreshTokenIfNeeded();
            if (refreshed) {
                response = await fetch(url, { ...options, headers: { ...getAuthHeaders(), ...options.headers } });
            } else {
                return response; // Still unauthorized after refresh attempt
            }
        }
        return response;
    }

    function formatDateTime(isoString) {
        if (!isoString) return 'N/A';
        const date = new Date(isoString);
        return date.toLocaleString();
    }

    function showToast(message, type = 'info') {
        // Simple toast implementation, replace with a proper UI library if available
        alert(`${type.toUpperCase()}: ${message}`);
    }

    // --- Theme Toggle ---
    const darkModeToggle = document.getElementById('darkModeToggle');
    function applyTheme(theme) {
        document.documentElement.dataset.theme = theme;
        localStorage.setItem('theme', theme);
        if (darkModeToggle) {
            darkModeToggle.checked = (theme === 'dark');
        }
    }

    // Initialize theme from localStorage or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', (event) => {
            applyTheme(event.target.checked ? 'dark' : 'light');
        });
    }

    // --- Driver Profile ---
    async function loadDriverProfile() {
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/profile/`);
            if (!response.ok) {
                throw new Error('Failed to load driver profile');
            }
            const profile = await response.json();
            document.getElementById('driver-name').textContent = profile.user.full_name || profile.user.phone_number;
            document.getElementById('driver-phone').textContent = profile.phone;
            document.getElementById('profile-vehicle-type').textContent = profile.vehicle_type;
            document.getElementById('profile-license-plate').textContent = profile.license_plate || 'N/A';
            document.getElementById('profile-status').textContent = profile.is_available ? 'Available' : 'Unavailable';

            // Populate edit modal
            document.getElementById('vehicleType').value = profile.vehicle_type;
            document.getElementById('vehicleDescription').value = profile.vehicle_description;
            document.getElementById('licensePlate').value = profile.license_plate;

        } catch (error) {
            console.error("Error loading driver profile:", error);
            showToast("Failed to load profile.", "error");
        }
    }

    document.getElementById('driver-profile-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/profile/`, {
                method: 'PATCH',
                body: JSON.stringify(data),
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                throw new Error('Failed to update profile');
            }
            showToast("Profile updated successfully!", "success");
            loadDriverProfile(); // Reload profile to update UI
            bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
        } catch (error) {
            console.error("Error updating driver profile:", error);
            showToast("Failed to update profile.", "error");
        }
    });

    // --- Order Management ---
    async function loadAssignedOrders() {
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/orders/`);
            if (!response.ok) {
                throw new Error('Failed to load assigned orders');
            }
            const orders = await response.json();
            const ordersList = document.getElementById('orders-list');
            ordersList.innerHTML = ''; // Clear previous orders

            if (orders.length === 0) {
                ordersList.innerHTML = '<p class="text-muted" id="no-orders-message">No assigned orders.</p>';
                return;
            }

            orders.forEach(order => {
                const orderElement = document.createElement('a');
                orderElement.href = '#';
                orderElement.classList.add('list-group-item', 'list-group-item-action');
                orderElement.dataset.orderId = order.id;
                orderElement.innerHTML = `
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">Order #${order.id}</h5>
                        <small class="text-muted">${formatDateTime(order.created_at)}</small>
                    </div>
                    <p class="mb-1">Customer: ${order.customer.full_name || order.customer.phone_number}</p>
                    <small>Status: ${order.status}</small>
                `;
                orderElement.addEventListener('click', (e) => {
                    e.preventDefault();
                    showOrderDetailModal(order.id);
                });
                ordersList.appendChild(orderElement);
            });
        } catch (error) {
            console.error("Error loading assigned orders:", error);
            showToast("Failed to load orders.", "error");
        }
    }

    async function showOrderDetailModal(orderId) {
        currentOrderId = orderId;
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/orders/${orderId}/`);
            if (!response.ok) {
                throw new Error('Failed to load order details');
            }
            const order = await response.json();

            document.getElementById('modal-order-id').textContent = order.id;
            document.getElementById('modal-customer-name').textContent = order.customer.full_name || order.customer.phone_number;
            document.getElementById('modal-customer-phone').textContent = order.customer.phone_number;
            document.getElementById('modal-address').textContent = order.address;
            document.getElementById('modal-total-price').textContent = `${order.total_price} UZS`;
            document.getElementById('modal-status').textContent = order.status;

            const mapLink = document.getElementById('modal-map-link');
            if (order.address_lat && order.address_lng) { // Assuming order has lat/lng for address
                mapLink.href = `https://www.google.com/maps/search/?api=1&query=${order.address_lat},${order.address_lng}`;
                mapLink.classList.remove('d-none');
            } else {
                mapLink.classList.add('d-none');
            }

            const itemsList = document.getElementById('modal-items-list');
            itemsList.innerHTML = '';
            order.order_items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = `${item.product.name} x ${item.quantity} (${item.price_at_order} UZS each)`;
                itemsList.appendChild(li);
            });

            renderDeliveryActions(order);
            renderArrivalWaitSection(order);

            const orderDetailModal = new bootstrap.Modal(document.getElementById('orderDetailModal'));
            orderDetailModal.show();
        } catch (error) {
            console.error("Error loading order details:", error);
            showToast("Failed to load order details.", "error");
        }
    }

    function renderDeliveryActions(order) {
        const actionsDiv = document.getElementById('delivery-actions');
        actionsDiv.innerHTML = '';

        let button = null;
        switch (order.status) {
            case 'Assigned':
                button = createActionButton('Accept Order', 'btn-success', async () => {
                    await updateOrderStatus(order.id, 'accept');
                });
                break;
            case 'Accepted':
                button = createActionButton('Picked Up', 'btn-primary', async () => {
                    await updateOrderStatus(order.id, 'status', { status: 'Picked Up' });
                });
                break;
            case 'Picked Up':
                button = createActionButton('On The Way', 'btn-info', async () => {
                    await updateOrderStatus(order.id, 'status', { status: 'On The Way' });
                });
                break;
            case 'On The Way':
                button = createActionButton('Arrived at Location', 'btn-warning', async () => {
                    await updateOrderStatus(order.id, 'arrival', { wait_seconds: 0 }); // Initial arrival, wait_seconds will be updated later
                });
                break;
            case 'Arrived':
                // Handled by renderArrivalWaitSection
                break;
            case 'Delivered':
                actionsDiv.innerHTML = '<p class="text-success">Order Delivered!</p>';
                break;
            case 'Canceled':
                actionsDiv.innerHTML = '<p class="text-danger">Order Canceled.</p>';
                break;
            default:
                actionsDiv.innerHTML = `<p>Current Status: ${order.status}</p>`;
                break;
        }
        if (button) {
            actionsDiv.appendChild(button);
        }
    }

    function createActionButton(text, className, onClickHandler) {
        const button = document.createElement('button');
        button.textContent = text;
        button.classList.add('btn', className, 'me-2');
        button.addEventListener('click', onClickHandler);
        return button;
    }

    async function updateOrderStatus(orderId, actionType, payload = {}) {
        let url = '';
        let method = 'POST';
        let successMessage = '';

        switch (actionType) {
            case 'accept':
                url = `${API_BASE_URL}/users/drivers/orders/${orderId}/accept/`;
                successMessage = `Order ${orderId} accepted.`;
                break;
            case 'status':
                url = `${API_BASE_URL}/users/drivers/orders/${orderId}/status/`;
                successMessage = `Order ${orderId} status updated to ${payload.status}.`;
                break;
            case 'arrival':
                url = `${API_BASE_URL}/users/drivers/orders/${orderId}/arrival/`;
                successMessage = `Order ${orderId} marked as arrived.`;
                break;
            default:
                console.error("Unknown action type:", actionType);
                return;
        }

        try {
            const response = await authenticatedFetch(url, {
                method: method,
                body: JSON.stringify(payload),
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update order status');
            }
            showToast(successMessage, "success");
            loadAssignedOrders(); // Reload orders list
            // If modal is open, refresh its content
            if (bootstrap.Modal.getInstance(document.getElementById('orderDetailModal')) && currentOrderId === orderId) {
                showOrderDetailModal(orderId);
            }
        } catch (error) {
            console.error(`Error updating order ${orderId} status:`, error);
            showToast(`Failed to update order status: ${error.message}`, "error");
        }
    }

    function renderArrivalWaitSection(order) {
        const arrivalWaitSection = document.getElementById('arrival-wait-section');
        const modalArrivedAt = document.getElementById('modal-arrived-at');
        const modalWaitTimer = document.getElementById('modal-wait-timer');
        const btnStopWait = document.getElementById('btn-stop-wait');

        if (order.status === 'Arrived') {
            arrivalWaitSection.classList.remove('d-none');
            modalArrivedAt.textContent = formatDateTime(order.delivery_details.arrived_at);
            waitStartTime = new Date(order.delivery_details.arrived_at);
            startWaitTimer(order.delivery_details.wait_seconds || 0);

            btnStopWait.onclick = async () => {
                const elapsedSeconds = Math.floor((new Date() - waitStartTime) / 1000);
                await updateOrderStatus(order.id, 'arrival', { wait_seconds: elapsedSeconds });
                await updateOrderStatus(order.id, 'status', { status: 'Delivered' }); // Mark as delivered after waiting
                stopWaitTimer();
            };
        } else {
            arrivalWaitSection.classList.add('d-none');
            stopWaitTimer();
        }
    }

    function startWaitTimer(initialWaitSeconds) {
        stopWaitTimer(); // Clear any existing timer
        let seconds = initialWaitSeconds;
        const modalWaitTimer = document.getElementById('modal-wait-timer');
        modalWaitTimer.textContent = `${seconds} seconds`;

        waitTimerInterval = setInterval(() => {
            seconds++;
            modalWaitTimer.textContent = `${seconds} seconds`;
        }, 1000);
    }

    function stopWaitTimer() {
        if (waitTimerInterval) {
            clearInterval(waitTimerInterval);
            waitTimerInterval = null;
        }
    }

    // --- Location Tracking ---
    const startTrackingBtn = document.getElementById('start-location-tracking');
    const stopTrackingBtn = document.getElementById('stop-location-tracking');
    const lastLocationUpdateSpan = document.getElementById('last-location-update');
    const currentLocationSpan = document.getElementById('current-location');

    async function sendLocationUpdate(latitude, longitude) {
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/location/`, {
                method: 'POST',
                body: JSON.stringify({ lat: latitude, lng: longitude, timestamp: new Date().toISOString() }),
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                throw new Error('Failed to send location update');
            }
            lastLocationUpdateSpan.textContent = formatDateTime(new Date().toISOString());
            currentLocationSpan.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
            console.log("Location updated:", latitude, longitude);
        } catch (error) {
            console.error("Error sending location update:", error);
            showToast("Failed to update location.", "error");
            stopLocationTracking(); // Stop tracking on error
        }
    }

    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    sendLocationUpdate(position.coords.latitude, position.coords.longitude);
                },
                (error) => {
                    console.error("Geolocation error:", error);
                    showToast("Geolocation failed. Please enable location services.", "error");
                    stopLocationTracking();
                },
                { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
            );
        } else {
            showToast("Geolocation is not supported by this browser.", "error");
            stopLocationTracking();
        }
    }

    function startLocationTracking() {
        if (locationTrackingInterval) return; // Already tracking

        startTrackingBtn.classList.add('d-none');
        stopTrackingBtn.classList.remove('d-none');
        showToast("Location tracking started.", "info");

        // Send initial location immediately
        getLocation();
        // Then send periodically (e.g., every 30 seconds)
        locationTrackingInterval = setInterval(getLocation, 30000); // 30 seconds
    }

    function stopLocationTracking() {
        if (locationTrackingInterval) {
            clearInterval(locationTrackingInterval);
            locationTrackingInterval = null;
            startTrackingBtn.classList.remove('d-none');
            stopTrackingBtn.classList.add('d-none');
            showToast("Location tracking stopped.", "info");
        }
    }

    startTrackingBtn.addEventListener('click', startLocationTracking);
    stopTrackingBtn.addEventListener('click', stopLocationTracking);

    // --- Payouts ---
    async function loadPayoutsSummary() {
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/users/drivers/payouts/`);
            if (!response.ok) {
                throw new Error('Failed to load payouts summary');
            }
            const payouts = await response.json();
            // This is a simplified summary. In a real app, you'd aggregate data.
            const totalEarnings = payouts.reduce((sum, p) => sum + parseFloat(p.amount_net), 0);
            const pendingPayouts = payouts.filter(p => p.status === 'Pending').reduce((sum, p) => sum + parseFloat(p.amount_net), 0);

            document.getElementById('earnings-total').textContent = `${totalEarnings.toFixed(2)} UZS`;
            document.getElementById('earnings-pending').textContent = `${pendingPayouts.toFixed(2)} UZS`;

            // Link to a hypothetical payouts history page
            document.getElementById('payouts-history-link').href = '/dashboard/payouts/'; // Assuming a separate payouts page
        } catch (error) {
            console.error("Error loading payouts summary:", error);
            showToast("Failed to load payouts summary.", "error");
        }
    }

    // --- Logout ---
    document.getElementById('logout-form').addEventListener('submit', (event) => {
        event.preventDefault();
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login/'; // Redirect to login page
    });

    // --- Initial Load ---
    if (authToken) {
        loadDriverProfile();
        loadAssignedOrders();
        loadPayoutsSummary();
    } else {
        window.location.href = '/login/'; // Redirect to login if no token
    }
});