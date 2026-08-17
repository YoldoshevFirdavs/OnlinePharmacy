document.addEventListener('DOMContentLoaded', function () {
    // Delete driver
    document.querySelectorAll('.driver-delete-btn').forEach(button => {
        button.addEventListener('click', function () {
            const driverId = this.getAttribute('data-driver-id');
            if (confirm('Are you sure you want to delete this driver?')) {
                fetch(`/dashboard/api/delivery/${driverId}/`, {
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
