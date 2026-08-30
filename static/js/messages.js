/**
 * Global Messages System
 * Unified error/success messages across entire app
 * Role-based detail level: admin (detailed) vs user (simple)
 */

class MessageManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create message container if not exists
        if (!document.getElementById('message-container')) {
            const container = document.createElement('div');
            container.id = 'message-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            `;
            document.body.appendChild(container);
            this.container = container;
        } else {
            this.container = document.getElementById('message-container');
        }
    }

    /**
     * Get user role for detail level
     * @returns {string} 'admin', 'user', or 'guest'
     */
    getUserRole() {
        const userEl = document.body.getAttribute('data-user-role');
        if (userEl === 'admin') return 'admin';
        if (userEl === 'authenticated') return 'user';
        return 'guest';
    }

    /**
     * Format error message based on user role
     * @param {string|Object} error - Error message or error object
     * @returns {string} Formatted message
     */
    formatErrorMessage(error) {
        const role = this.getUserRole();

        // If error object with details
        if (typeof error === 'object' && error.message) {
            if (role === 'admin') {
                // Detailed for admin
                const details = error.details ? ` (${error.details})` : '';
                const code = error.code ? ` [${error.code}]` : '';
                return `❌ ${error.message}${code}${details}`;
            } else {
                // Simple for user
                return `❌ ${error.message}`;
            }
        }

        // String error
        if (typeof error === 'string') {
            if (role === 'admin') {
                return `❌ ${error}`;
            } else {
                // Simplify common errors for users
                if (error.includes('401') || error.includes('authentication')) {
                    return '❌ Iltimos, avval tizimga kiring';
                }
                if (error.includes('403') || error.includes('permission')) {
                    return '❌ Siz bu amalni bajarolmaysiz';
                }
                if (error.includes('404') || error.includes('not found')) {
                    return '❌ Topilmadi';
                }
                if (error.includes('500') || error.includes('server')) {
                    return '❌ Server xatosi. Qayta urinib ko\'ring';
                }
                return `❌ Xatolik yuz berdi. Qayta urinib ko\'ring`;
            }
        }

        return '❌ Noma\'lum xatolik';
    }

    /**
     * Show success message
     * @param {string} message - Message text
     * @param {number} duration - Auto-hide duration (ms), 0 = manual
     */
    success(message, duration = 4000) {
        this.show('success', message, duration);
    }

    /**
     * Show error message
     * @param {string|Object} error - Error message or object
     * @param {number} duration - Auto-hide duration (ms), 0 = manual
     */
    error(error, duration = 5000) {
        const message = this.formatErrorMessage(error);
        this.show('error', message, duration);
    }

    /**
     * Show warning message
     * @param {string} message - Message text
     * @param {number} duration - Auto-hide duration (ms), 0 = manual
     */
    warning(message, duration = 4000) {
        this.show('warning', message, duration);
    }

    /**
     * Show info message
     * @param {string} message - Message text
     * @param {number} duration - Auto-hide duration (ms), 0 = manual
     */
    info(message, duration = 4000) {
        this.show('info', message, duration);
    }

    /**
     * Internal show method
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {string} message - Message text
     * @param {number} duration - Auto-hide duration
     */
    show(type, message, duration = 4000) {
        const messageEl = document.createElement('div');
        messageEl.className = `message message--${type}`;

        // Color scheme
        const colors = {
            success: { bg: '#d4edda', text: '#155724', border: '#c3e6cb' },
            error: { bg: '#f8d7da', text: '#721c24', border: '#f5c6cb' },
            warning: { bg: '#fff3cd', text: '#856404', border: '#ffeaa7' },
            info: { bg: '#d1ecf1', text: '#0c5460', border: '#bee5eb' },
        };

        const color = colors[type] || colors.info;

        messageEl.style.cssText = `
            background: ${color.bg};
            border: 1px solid ${color.border};
            color: ${color.text};
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            animation: slideInRight 0.3s ease-out;
            word-wrap: break-word;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        `;

        messageEl.innerHTML = message;

        // Click to dismiss
        messageEl.addEventListener('click', () => {
            messageEl.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => messageEl.remove(), 300);
        });

        this.container.appendChild(messageEl);

        // Auto hide
        if (duration > 0) {
            setTimeout(() => {
                if (messageEl.parentElement) {
                    messageEl.style.animation = 'slideOutRight 0.3s ease-in';
                    setTimeout(() => messageEl.remove(), 300);
                }
            }, duration);
        }
    }

    /**
     * Clear all messages
     */
    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Global instance
const messages = new MessageManager();

// CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(style);

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MessageManager;
}
