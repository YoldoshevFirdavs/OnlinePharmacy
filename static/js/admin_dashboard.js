
const API_BASE = 'http://localhost:8000/api/v1';

// Check auth
function checkAuth() {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    
    if (!token || role !== 'admin') {
        window.location.href = '/login.html'; // Assuming a login page exists
        return;
    }
    
    // Load user info
    const userName = localStorage.getItem('user_name') || 'Admin';
    const initials = userName.split(' ').map(n => n[0]).join('').toUpperCase();
    
    document.getElementById('userName').textContent = userName;
    document.getElementById('userInitial').textContent = initials;
}

// Load dashboard data
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/admin/dashboard/`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update stats
            document.getElementById('totalOrders').textContent = data.total_orders || 0;
            document.getElementById('completedOrders').textContent = data.completed_orders || 0;
            document.getElementById('pendingOrders').textContent = data.pending_orders || 0;
            document.getElementById('monthRevenue').textContent = (data.month_revenue / 1000000).toFixed(1) + 'M' || '0M';
            
            // Load recent orders
            loadOrders(data.recent_orders || []);
        }
    } catch (error) {
        console.error('Dashboard yuklash xato:', error);
        // Optionally, display an error message on the dashboard
    }
}

// Load orders
function loadOrders(orders) {
    const tbody = document.getElementById('ordersBody');
    
    if (!tbody) return;

    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">Buyurtma yo\'q</td></tr>';
        return;
    }
    
    tbody.innerHTML = orders.map(order => `
        <tr>
            <td>#${order.id}</td>
            <td>${order.customer_name}</td>
            <td>${order.medicine_name}</td>
            <td>${order.total_price}K</td>
            <td><span class="badge badge-${getStatusClass(order.status)}">${order.status}</span></td>
            <td><button class="btn btn-primary" onclick="viewOrder(${order.id})">Ko'r</button></td>
        </tr>
    `).join('');
}

function getStatusClass(status) {
    switch(status) {
        case 'completed': return 'success';
        case 'pending': return 'warning';
        case 'cancelled': return 'danger';
        default: return 'secondary';
    }
}

// Toggle sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// Set active nav
function setActive(e) {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    e.target.closest('.nav-link').classList.add('active');
}

// Open profile
function openProfile() {
    const name = localStorage.getItem('user_name') || 'Admin';
    const profileContent = document.getElementById('profileContent');
    const profileModal = document.getElementById('profileModal');

    if (profileContent) {
        profileContent.textContent = `Foydalanuvchi: ${name}`;
    }
    if (profileModal) {
        profileModal.classList.add('active');
    }
}

// Close profile
function closeProfile() {
    const profileModal = document.getElementById('profileModal');
    if (profileModal) {
        profileModal.classList.remove('active');
    }
}

// Logout
function logout(e) {
    e.preventDefault();
    if (confirm('Rostdan ham chiqmoqsiz?')) {
        localStorage.clear();
        window.location.href = '/login.html'; // Assuming a login page exists
    }
}

// View order
function viewOrder(id) {
    alert(`Order #${id} tafsilotlari (keyin qo'shiladi)`);
}

// View all orders
function viewAllOrders() {
    window.location.href = '#orders'; // Navigate to the orders section or page
}

// Initialize
window.addEventListener('load', () => {
    checkAuth();
    loadDashboard();
});

// Refresh every 30 seconds
setInterval(loadDashboard, 30000);
