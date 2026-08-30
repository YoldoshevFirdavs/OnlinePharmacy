/**
 * Delete Modal Handlers - Barcha admin sahifalar uchun
 * Delete modal HTML base.html da inline joylashgan
 */

// Get CSRF token from cookie
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

// Show delete confirmation modal - GLOBAL FUNCTION
function showDeleteModal(itemName, deleteUrl, row, itemType) {
    const modal = document.getElementById('deleteModal');
    if (!modal) {
        return;
    }
    
    const itemNameEl = document.getElementById('deleteItemName');
    const undoNotification = document.getElementById('undoNotification');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    if (!itemNameEl || !undoNotification || !confirmBtn) {
        return;
    }
    
    // Reset modal
    itemNameEl.textContent = itemName;
    window.currentDeleteItem = itemName;
    window.currentDeleteUrl = deleteUrl;
    window.currentRow = row;
    
    // Hide undo notification initially
    undoNotification.style.display = 'none';
    document.getElementById('deletedItemId').value = '';
    document.getElementById('deletedItemType').value = '';
    document.getElementById('undoUrl').value = '';
    
    // Change button text
    confirmBtn.textContent = 'Ha, o\'chirish';
    confirmBtn.style.background = '#e74c3c';
    
    // Show modal with animation
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

// Get item type from URL
function getCurrentItemType(url) {
    if (!url) return 'unknown';
    if (url.includes('/bans/')) return 'ban';
    if (url.includes('/users/')) return 'user';
    if (url.includes('/medicines/')) return 'medicine';
    if (url.includes('/categories/')) return 'category';
    if (url.includes('/delivery/')) return 'delivery';
    if (url.includes('/orders/')) return 'order';
    return 'unknown';
}

// Execute delete with undo functionality - GLOBAL FUNCTION
async function executeDelete() {
    if (!window.currentDeleteUrl || !window.currentRow) {
        return;
    }
    
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const undoNotification = document.getElementById('undoNotification');
    
    if (!confirmBtn || !undoNotification) return;
    
    // Show loading
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> O\'chirilmoqda...';
    
    try {
        const response = await fetch(window.currentDeleteUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            
            // Show undo notification
            undoNotification.style.display = 'flex';
            document.getElementById('deletedItemId').value = window.currentDeleteItem;
            document.getElementById('deletedItemType').value = getCurrentItemType(window.currentDeleteUrl);
            document.getElementById('undoUrl').value = data.undo_url || window.currentDeleteUrl;
            
            // Fade out the row
            window.currentRow.style.opacity = '0.5';
            window.currentRow.style.pointerEvents = 'none';
            window.currentRow.classList.add('delete-in-progress');
            
            // Show undo button
            const undoBtn = document.getElementById('undoDeleteBtn');
            if (undoBtn) {
                undoBtn.onclick = () => undoDelete();
            }
            
            // Start 10-second countdown timer for undo
            startUndoCountdown(10);
            
            // Auto-close modal after short delay
            setTimeout(() => {
                closeDeleteModal();
            }, 800);
        } else {
            alert(data.message || 'O\'chirishda xatolik yuz berdi');
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Ha, o\'chirish';
            confirmBtn.style.background = '#e74c3c';
        }
    } catch (error) {
        alert('Xatolik yuz berdi. Qayta urinib ko\'ring.');
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Ha, o\'chirish';
        confirmBtn.style.background = '#e74c3c';
    }
}

// Undo delete functionality - GLOBAL FUNCTION
async function undoDelete() {
    const undoUrl = document.getElementById('undoUrl').value;
    if (!undoUrl) {
        return;
    }
    
    // Clear countdown interval if running
    if (window.undoCountdownInterval) {
        clearInterval(window.undoCountdownInterval);
    }
    
    const undoBtn = document.getElementById('undoDeleteBtn');
    const notification = document.getElementById('undoNotification');
    
    if (!undoBtn || !notification) return;
    
    undoBtn.disabled = true;
    undoBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Qaytarilmoqda...';
    
    try {
        const response = await fetch(undoUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: 'undo' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            
            // Restore row
            if (window.currentRow) {
                window.currentRow.style.opacity = '1';
                window.currentRow.style.pointerEvents = 'auto';
                window.currentRow.classList.remove('delete-in-progress');
            }
            
            // Hide notification
            notification.style.display = 'none';
            undoBtn.disabled = false;
            undoBtn.textContent = 'Qaytarish';
            alert('Element muvaffaqiyatli qaytarildi!');
        } else {
            alert(data.message || 'Qaytarishda xatolik yuz berdi');
            undoBtn.disabled = false;
            undoBtn.textContent = 'Qaytarish';
        }
    } catch (error) {
        alert('Xatolik yuz berdi. Qayta urinib ko\'ring.');
        undoBtn.disabled = false;
        undoBtn.textContent = 'Qaytarish';
    }
}

// Close delete modal - GLOBAL FUNCTION
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (!modal) return;
    
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        window.currentDeleteItem = null;
        window.currentDeleteUrl = null;
        window.currentRow = null;
    }, 300);
}

// Set auto-hide timer for undo notification
function setUndoTimer(ms) {
    if (window.deleteTimeout) clearTimeout(window.deleteTimeout);
    
    window.deleteTimeout = setTimeout(() => {
        const notification = document.getElementById('undoNotification');
        if (notification && notification.style.display !== 'none') {
            notification.style.display = 'none';
        }
    }, ms);
}

// Start 10-second undo countdown
function startUndoCountdown(seconds) {
    const undoCountdownSec = document.getElementById('undoCountdownSec');
    const undoProgressBar = document.getElementById('undoProgressBar');
    const undoNotification = document.getElementById('undoNotification');
    
    if (!undoCountdownSec || !undoProgressBar || !undoNotification) return;
    
    let secondsLeft = seconds;
    const totalSeconds = seconds;
    
    // Update every 100ms for smooth progress bar
    const interval = setInterval(() => {
        secondsLeft -= 0.1;
        
        // Update progress bar
        const progressPercent = (secondsLeft / totalSeconds) * 100;
        undoProgressBar.style.width = progressPercent + '%';
        
        // Update countdown display (show whole seconds)
        undoCountdownSec.textContent = Math.ceil(secondsLeft);
        
        // When time is up
        if (secondsLeft <= 0) {
            clearInterval(interval);
            undoNotification.style.display = 'none';
            undoProgressBar.style.width = '0%';
            
            // Delete the item permanently
            if (window.currentRow) {
                window.currentRow.style.display = 'none';
            }
        }
    }, 100);
    
    // Store interval ID for cleanup
    window.undoCountdownInterval = interval;
}

// Delete item helper function
function deleteItem(btn, type, url) {
    const row = btn.closest('tr');
    let itemName = '';
    
    // Extract item name from row
    const nameCell = row.querySelector('td:first-child');
    if (nameCell) {
        itemName = nameCell.textContent.trim();
    } else {
        itemName = `${type} #${btn.dataset[type + 'Id'] || ''}`;
    }
    
    // Show modal
    showDeleteModal(itemName, url, row, type);
}

// Initialize delete handlers for all delete buttons
function initDeleteHandlers() {
    // Order delete
    document.querySelectorAll('.order-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            const url = this.dataset.deleteUrl || `/dashboard/orders/${orderId}/delete/`;
            deleteItem(this, 'order', url);
        });
    });
    
    // User delete
    document.querySelectorAll('.user-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const userId = this.dataset.userId;
            const url = this.dataset.deleteUrl || `/dashboard/users/${userId}/delete/`;
            deleteItem(this, 'user', url);
        });
    });
    
    // Delivery/Driver delete
    document.querySelectorAll('.driver-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const driverId = this.dataset.driverId;
            const url = this.dataset.deleteUrl || `/dashboard/delivery/${driverId}/delete/`;
            deleteItem(this, 'delivery', url);
        });
    });
    
    // Medicine delete
    document.querySelectorAll('.medicine-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const medicineId = this.dataset.medicineId;
            const url = this.dataset.deleteUrl || `/dashboard/medicines/${medicineId}/delete/`;
            deleteItem(this, 'medicine', url);
        });
    });
    
    // Category delete
    document.querySelectorAll('.category-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const categoryId = this.dataset.categoryId;
            const url = this.dataset.deleteUrl || `/dashboard/categories/${categoryId}/delete/`;
            deleteItem(this, 'category', url);
        });
    });
    
    // Ban delete
    document.querySelectorAll('.ban-delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const banId = this.dataset.banId;
            const url = this.dataset.deleteUrl || `/dashboard/bans/${banId}/delete/`;
            deleteItem(this, 'ban', url);
        });
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initDeleteHandlers();
});
