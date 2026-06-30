// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // Minimal interactivity for dashboard links
    const sidebarLinks = document.querySelectorAll('.dashboard-sidebar nav ul li a');
    const dashboardContent = document.querySelector('.dashboard-content');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove('active'));
            // Add active class to the clicked link
            e.target.classList.add('active');

            // Scroll to the corresponding section
            const targetId = e.target.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Example of a simple function for dashboard interactivity
    function handleFormSubmission(formId, successMessage) {
        const form = document.querySelector(`#${formId} form`);
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                alert(successMessage);
                // In a real application, you would send data to the backend here
                console.log(`Form ${formId} submitted!`);
            });
        }
    }

    handleFormSubmission('profile', 'Profile updated successfully!');
    handleFormSubmission('settings', 'Settings saved successfully!');

    // Another example function: highlight table rows on hover
    function highlightTableRows(tableSelector) {
        const table = document.querySelector(tableSelector);
        if (table) {
            table.querySelectorAll('tbody tr').forEach(row => {
                row.addEventListener('mouseenter', () => {
                    row.style.backgroundColor = '#f0f0f0';
                });
                row.addEventListener('mouseleave', () => {
                    row.style.backgroundColor = '';
                });
            });
        }
    }

    highlightTableRows('.dashboard-content table');

    // Function to toggle sidebar visibility on smaller screens (example)
    function setupSidebarToggle() {
        const toggleButton = document.createElement('button');
        toggleButton.textContent = 'Toggle Sidebar';
        toggleButton.classList.add('btn', 'btn-primary', 'sidebar-toggle-btn');
        // Append to header or main content area as appropriate
        const header = document.querySelector('.dashboard-header .container');
        if (header) {
            header.appendChild(toggleButton);
        }

        const sidebar = document.querySelector('.dashboard-sidebar');
        if (toggleButton && sidebar) {
            toggleButton.addEventListener('click', () => {
                sidebar.classList.toggle('hidden-sidebar');
            });
        }
    }

    // You might want to call setupSidebarToggle() based on screen size
    // window.addEventListener('resize', () => { /* check screen size and call */ });
    // setupSidebarToggle(); // For demonstration
});