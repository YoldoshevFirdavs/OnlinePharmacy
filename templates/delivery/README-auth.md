# Delivery Authentication Configuration

This document specifies the client-side configuration, endpoints, brute-force mitigation limits, settings keys, and local testing instructions for the delivery auth page.

## Configuration Items (AUTH_CONFIG)

The following configuration object is exported by `static/js/auth.js`:

```javascript
const AUTH_CONFIG = {
    AUTH_ENDPOINTS: {
        password: '/api/v1/admin/login/',
        otp: '/api/v1/admin/login/',
        telegram: '/api/v1/admin/login/',
        email_magic_link: '/api/v1/admin/login/',
        ip_block_notify: '/api/v1/admin/login/',
    },
    TIMER_SETTINGS: {
        default_seconds: 240, 
        warning_seconds: 120, 
        danger_seconds: 10,   
        colors: {
            green: '#28a745',
            yellow: '#ffc107',
            red: '#dc3545'
        }
    },
    PHONE_PATTERNS: {
        uz: {
            prefixes: ['+998', '998'],
            regex: /^\+?998\d{9}$/,
            placeholder: "+998 XX XXX XX XX",
            mask: "+998 99 999 99 99"
        },
        us: {
            prefixes: ['+1', '1'],
            regex: /^\+?1\d{10}$/,
            placeholder: "+1 (XXX) XXX-XXXX",
            mask: "+1 (999) 999-9999"
        }
    },
    SECURITY: {
        max_attempts_before_block: 5,
        block_duration_seconds: 600,
        max_blocks_before_ban: 5,
        ban_behavior: 'deny_all',
        field_brute_force_attempts: 5,
        field_brute_force_duration: 600,
    },
    DEBUG_AUTH_PAGE: false
};
```

### Key Security & Brute-Force Mechanics
1. **Identifier Lockout**: If an identifier (phone number or email) receives 5 failed credential/OTP attempts, it is locked out for 10 minutes (600 seconds) using a browser `localStorage` timestamp block.
2. **Permanent Ban Mode**: If the identifier lockout repeats 5 times (`max_blocks_before_ban`), the client enters permanent ban mode (`deny_all`).
3. **Field-level lockout**: If the phone input field receives 5 consecutive invalid formats or verification errors, it is locked immediately for 10 minutes.
4. **Debug Override**: Setting `DEBUG_AUTH_PAGE` to `true` disables all frontend lockouts.

## Local Test Commands
- **Runserver**:
  ```bash
  python manage.py runserver
  ```
- **Verification Page URL**:
  Navigate to `http://127.0.0.1:8000/delivery/auth/` and verify AJAX network payloads and JavaScript variables via Console.
- **Django Shell URL reverse validation**:
  ```python
  python manage.py shell
  # Inside shell:
  from django.urls import reverse
  reverse('dashboard:admin_settings')
  ```
- **JS Stub tests**:
  ```bash
  npm test static/js/*.test.js
  ```
