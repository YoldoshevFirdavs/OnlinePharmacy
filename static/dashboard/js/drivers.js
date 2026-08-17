document.addEventListener('DOMContentLoaded', function () {
    const driverModal = new bootstrap.Modal(document.getElementById('driverModal'));
    const driverForm = document.getElementById('driverForm');
    const driverIdField = document.getElementById('driverId');
    const fullNameField = document.getElementById('fullName');
    const phoneNumberField = document.getElementById('phoneNumber');
    const vehicleInfoField = document.getElementById('vehicleInfo');
    const saveDriverBtn = document.getElementById('saveDriverBtn');

    // Open modal for creating a new driver
    document.getElementById('btnCreateDriver').addEventListener('click', function () {
        driverForm.reset();
        driverIdField.value = '';
        driverModal.show();
    });

    // Open modal for editing a driver
    document.querySelectorAll('.driver-edit-btn').forEach(button => {
        button.addEventListener('click', function () {
            const driverId = this.getAttribute('data-driver-id');
            fetch(`/dashboard/api/drivers/${driverId}/`)
                .then(response => response.json())
                .then(data => {
                    driverIdField.value = data.id;
                    fullNameField.value = data.user.full_name;
                    phoneNumberField.value = data.phone_number;
                    vehicleInfoField.value = data.vehicle_info;
                    driverModal.show();
                });
        });
    });

    // Save driver (create or update)
    saveDriverBtn.addEventListener('click', function () {
        const driverId = driverIdField.value;
        const url = driverId ? `/dashboard/api/drivers/${driverId}/` : '/dashboard/api/drivers/';
        const method = driverId ? 'PUT' : 'POST';

        const formData = {
            user: {
                full_name: fullNameField.value,
            },
            phone_number: phoneNumberField.value,
            vehicle_info: vehicleInfoField.value,
        };

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(formData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                driverModal.hide();
                location.reload();
            } else {
                // Handle errors
                console.error(data);
            }
        });
    });

    // Delete driver
    document.querySelectorAll('.driver-delete-btn').forEach(button => {
        button.addEventListener('click', function () {
            const driverId = this.getAttribute('data-driver-id');
            if (confirm('Are you sure you want to delete this driver?')) {
                fetch(`/dashboard/api/drivers/${driverId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                })
                .then(response => {
                    if (response.ok) {
                        location.reload();
                    }
                });
            }
        });
    });

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
});
