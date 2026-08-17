/**
 * Device Fingerprint Generator
 * Creates a deterministic device fingerprint using browser properties
 * and stores it in a secure cookie for ban and rate limiting purposes.
 * 
 * Requirements:
 * - Deterministic: Same device always produces same fingerprint
 * - Secure: SHA256 hash, cookie with Secure; SameSite=Lax
 * - Fallback: Header injection for API requests
 */

class DeviceFingerprintGenerator {
    constructor() {
        this.cookieName = 'device_fp';
        this.headerName = 'Authorization-Fingerprint';
    }

    /**
     * Generate deterministic device fingerprint
     * Uses: userAgent, platform, screen WxH, colorDepth, timezone, language,
     *       hardwareConcurrency, maxTouchPoints, canvas fingerprint
     * @returns {Promise<string>} SHA256 hash of device properties
     */
    async generateFingerprint() {
        const parts = [];
        
        try {
            // 1. Browser properties
            parts.push(navigator.userAgent || '');
            parts.push(navigator.platform || '');
            
            // 2. Screen properties
            parts.push(screen.width + 'x' + screen.height);
            parts.push(screen.colorDepth || '');
            
            // 3. Timezone
            try {
                parts.push(Intl.DateTimeFormat().resolvedOptions().timeZone || 'unknown-timezone');
            } catch (e) {
                parts.push('unknown-timezone');
            }
            
            // 4. Language and hardware
            parts.push(navigator.language || '');
            parts.push(navigator.hardwareConcurrency || '');
            parts.push(navigator.maxTouchPoints || '');
            
            // 5. Minimal canvas fingerprint
            try {
                const canvas = document.createElement('canvas');
                canvas.width = 200;
                canvas.height = 50;
                const ctx = canvas.getContext('2d');
                
                if (ctx) {
                    ctx.textBaseline = 'top';
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#000000';
                    ctx.fillText('Device Fingerprint', 2, 2);
                    
                    // Add geometric shapes
                    ctx.beginPath();
                    ctx.arc(50, 25, 10, 0, Math.PI * 2);
                    ctx.fill();
                    
                    parts.push(canvas.toDataURL());
                } else {
                    parts.push('no-canvas-context');
                }
            } catch (e) {
                parts.push('no-canvas');
            }
            
            // Join all parts with separator
            const raw = parts.join('||');
            
            // Generate SHA256 hash
            const msgUint8 = new TextEncoder().encode(raw);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            
            return hashHex;
        } catch (error) {
            console.error('Error generating fingerprint:', error);
            // Fallback: generate a simpler hash
            const fallback = [
                navigator.userAgent || 'unknown',
                navigator.platform || 'unknown',
                screen.width + 'x' + screen.height,
                Date.now().toString()
            ].join('||');
            
            // Simple hash fallback
            let hash = 0;
            for (let i = 0; i < fallback.length; i++) {
                const char = fallback.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            return Math.abs(hash).toString(16);
        }
    }

    /**
     * Set fingerprint cookie with secure settings
     * Cookie name: device_fp
     * Flags: Path=/; SameSite=Lax; Max-Age=86400 (24 hours)
     * Secure flag only for HTTPS
     */
    setCookie(fingerprint) {
        const isSecure = window.location.protocol === 'https:';
        const cookieValue = `${this.cookieName}=${fingerprint}; Path=/; SameSite=Lax; Max-Age=86400`;
        
        // Add Secure flag only for HTTPS
        if (isSecure) {
            document.cookie = cookieValue + '; Secure';
        } else {
            document.cookie = cookieValue;
        }
        
        console.log('Device fingerprint cookie set:', fingerprint.substring(0, 8) + '...');
    }

    /**
     * Get existing fingerprint from cookie
     * @returns {string|null} Existing fingerprint or null
     */
    getCookie() {
        const name = this.cookieName + '=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookieArray = decodedCookie.split(';');
        
        for (let cookie of cookieArray) {
            cookie = cookie.trim();
            if (cookie.indexOf(name) === 0) {
                return cookie.substring(name.length);
            }
        }
        return null;
    }

    /**
     * Add fingerprint to AJAX headers
     * Injects into XMLHttpRequest and fetch for API calls
     */
    addToHeaders(fingerprint) {
        // Override XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(...args) {
            this._fp_url = args[1];
            return originalOpen.apply(this, args);
        };
        
        XMLHttpRequest.prototype.send = function(...args) {
            // Add fingerprint header to API calls
            if (this._fp_url && (this._fp_url.startsWith('/api/') || this._fp_url.startsWith('/dashboard/'))) {
                this.setRequestHeader(this.constructor.prototype.headerName || 'Authorization-Fingerprint', fingerprint);
            }
            return originalSend.apply(this, args);
        };

        // Override fetch
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (typeof url === 'string' && (url.startsWith('/api/') || url.startsWith('/dashboard/'))) {
                options.headers = options.headers || {};
                options.headers[window.deviceFP.headerName] = fingerprint;
            }
            return originalFetch(url, options);
        }.bind(this);
    }

    /**
     * Initialize device fingerprint system
     * Called automatically on DOMContentLoaded
     * @returns {Promise<string>} Current device fingerprint
     */
    async init() {
        try {
            let fingerprint = this.getCookie();
            
            // If no existing fingerprint or it's invalid, generate new one
            if (!fingerprint || fingerprint.length < 32) {
                console.log('Generating new device fingerprint...');
                fingerprint = await this.generateFingerprint();
                this.setCookie(fingerprint);
            } else {
                console.log('Using existing device fingerprint:', fingerprint.substring(0, 8) + '...');
            }
            
            // Add to AJAX headers for future requests
            this.addToHeaders(fingerprint);
            
            return fingerprint;
        } catch (error) {
            console.error('Failed to initialize device fingerprint:', error);
            return null;
        }
    }

    /**
     * Get current fingerprint (from cookie or generate new)
     * @returns {Promise<string>} Current device fingerprint
     */
    async getCurrentFingerprint() {
        let fingerprint = this.getCookie();
        if (!fingerprint) {
            fingerprint = await this.generateFingerprint();
            this.setCookie(fingerprint);
        }
        return fingerprint;
    }

    /**
     * Manual refresh function for debugging
     * @returns {Promise<string|null>} New fingerprint or null
     */
    async refresh() {
        try {
            console.log('Manually refreshing device fingerprint...');
            const fingerprint = await this.generateFingerprint();
            this.setCookie(fingerprint);
            this.addToHeaders(fingerprint);
            window.currentDeviceFingerprint = fingerprint;
            console.log('New fingerprint:', fingerprint);
            return fingerprint;
        } catch (error) {
            console.error('Manual fingerprint refresh failed:', error);
            return null;
        }
    }
}

// Global instance
window.DeviceFingerprintGenerator = DeviceFingerprintGenerator;
window.deviceFP = new DeviceFingerprintGenerator();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async function() {
        try {
            const fingerprint = await window.deviceFP.init();
            if (fingerprint) {
                console.log('Device fingerprint system initialized successfully');
                window.currentDeviceFingerprint = fingerprint;
            } else {
                console.warn('Failed to initialize device fingerprint system');
            }
        } catch (error) {
            console.error('Device fingerprint initialization error:', error);
        }
    });
} else {
    // DOM already loaded, initialize immediately
    (async function() {
        try {
            const fingerprint = await window.deviceFP.init();
            if (fingerprint) {
                console.log('Device fingerprint system initialized successfully');
                window.currentDeviceFingerprint = fingerprint;
            }
        } catch (error) {
            console.error('Device fingerprint initialization error:', error);
        }
    })();
}

// Reinitialize on page visibility change (in case cookie was cleared)
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Re-check fingerprint when page becomes visible
        setTimeout(async () => {
            try {
                const current = window.deviceFP.getCookie();
                if (!current) {
                    console.log('Fingerprint cookie missing, reinitializing...');
                    await window.deviceFP.init();
                }
            } catch (error) {
                console.error('Fingerprint reinitialization error:', error);
            }
        }, 1000);
    }
});