TIMESTAMP: 2026-07-31T13:18:10+05:00
COMPONENT: dashboard_updates
USER: id=1; email=f***@gmail.com
ERROR: None
ACTION: All 12 requested dashboard UI, stat card, chart rendering, header profile/brand preview, user account avatar editing, search filter, and media serving fixes successfully executed and verified.
TIMESTAMP: 2026-07-31T13:30:00+05:00
COMPONENT: dashboard_edits
ERROR: FILE_NOT_FOUND: templates/dashboard/includes/header.html (header is in templates/dashboard/base.html instead)
ACTION: Used `templates/dashboard/base.html` for header edits. Created .bak copies for each edited file and updated header behavior, theme toggle, customize palette, avatar UI, and favicon fixes.
FILES_MODIFIED: templates/dashboard/base.html, templates/edit_profile.html, static/dashboard/js/header.js, static/dashboard/js/theme.js, templates/dashboard/design/customize.html, templates/dashboard/account/settings.html
BACKUPS_CREATED: templates/dashboard/base.html.bak, templates/edit_profile.html.bak, static/dashboard/js/header.js.bak, static/dashboard/css/theme.css.bak, templates/dashboard/design/customize.html.bak, templates/dashboard/account/settings.html.bak
NOTE: MEDIA_URL and MEDIA_ROOT confirmed in config/settings.py; media serving configured in config/urls.py. If browser CSP blocks external media, add necessary sources to img-src and log CSP errors.

TIMESTAMP: 2026-07-31T13:44:00+05:00
COMPONENT: media_check
ERROR: MEDIA FILE NOT FOUND: media/users_profile_avatars/python.jpg
ACTION: File missing on disk; avatar templates will fallback to static default. Please place the user's avatar at `media/users_profile_avatars/python.jpg` or update storage settings.


COMPONENT: login_page
USER: id=1; email=f***@gmail.com
ERROR: Reverse for 'dashboard' not found. 'dashboard' is not a valid view function or pattern name.
ACTION: Login failed during login(request, user)
TRACEBACK: Traceback (most recent call last):
  File "/app/dashboard/views.py", line 177, in login_page
    return redirect("dashboard:dashboard-admin")
  File "/usr/local/lib/python3.10/site-packages/django/shortcuts.py", line 49, in redirect
    return redirect_class(resolve_url(to, *args, **kwargs))
  File "/usr/
---
TIMESTAMP: 2026-07-31T17:01:25+05:00
COMPONENT: auth_page_layout
ACTION: Fixed auth page layout: enlarged form elements, fixed social buttons alignment, and implemented sticky header/footer.
FILES_MODIFIED: templates/auth.html, static/css/auth.css, static/dashboard/js/base.js

TIMESTAMP: 2026-07-31T17:30:00+05:00
COMPONENT: me_endpoint_reliability
USER: N/A
ERROR: None
ACTION: Updated /me endpoint for reliable auth. Added roles field to UserSerializer (computed from is_staff, is_superuser, deliverer, seller). Updated all frontend JS /me fetch calls with credentials: include for cookie session auth. Fixed avatar_routing.js, account.js, header.js to use credentials: include. dashboard/base.js already had credentials: include.
FILES_MODIFIED: users/serializers.py, static/js/avatar_routing.js, static/js/account.js, static/js/header.js
BACKUPS_CREATED: users/serializers.py.bak, users/views.py.bak, static/js/avatar_routing.js.bak, static/js/account.js.bak, static/js/header.js.bak
NOTE: /me endpoint now reliably returns roles array: ['admin'] for staff users, ['deliverer'] for active deliverers, ['seller'] for sellers, ['user'] for regular users. All JS fetch calls to /api/v1/users/me/ include credentials: include.

TIMESTAMP: 2026-07-31T22:50:00+05:00
COMPONENT: admin_login_verify_otp
USER: id=N/A; email=fir***@***
ERROR: Session not found: eGSB_YA1...
ACTION: Fixed admin login verify OTP endpoint mismatch. Added verify_otp method to AdminLoginViewSet. Updated JS auth.js to use correct endpoint (/api/v1/users/admin/login/verify-otp/). Added admin_verify_otp config to AUTH_ENDPOINTS.
FILES_MODIFIED: users/views.py, static/js/auth.js
BACKUPS_CREATED: users/views.py.bak, static/js/auth.js.bak
NOTE: Admin login flow now correctly calls /api/v1/users/admin/login/verify-otp/ with action: 'verify_otp' payload. Added verify_otp method to AdminLoginViewSet that handles session verification, OTP checking, and returns JWT tokens.

TIMESTAMP: 2026-07-31T22:55:00+05:00
COMPONENT: admin_rate_limit
USER: N/A
ERROR: None
ACTION: Added rate limiting to admin login/verify OTP endpoint. Implemented check_rate_limit before verification and reset_rate_limit on success. Rate limit scope: admin_login:{identifier}. Prevents brute force attacks.
FILES_MODIFIED: users/views.py
BACKUPS_CREATED: users/views.py.bak
NOTE: Admin login verify_otp endpoint now includes rate limiting to prevent brute force attacks. Maximum attempts: OTP_MAX_ATTEMPTS (default 5) per identifier in RATE_LIMIT_WINDOW (default 60 seconds).

TIMESTAMP: 2026-07-31T23:00:00+05:00
COMPONENT: admin_login_response_format
USER: id=N/A; email=fir***@***
ERROR: Session expired or not found (false positive after fix)
ACTION: Fixed response format handling in auth.js. Backend returns ok:true but JS was checking for response.success||response.redirect. Updated to check for response.ok and handle both new format (token/refresh) and legacy format (access/refresh). Also handles error field correctly.
FILES_MODIFIED: static/js/auth.js
BACKUPS_CREATED: static/js/auth.js.bak
NOTE: auth.js now correctly handles admin login verify_otp response. Fixed to check response.ok instead of response.success, and uses response.token instead of response.access. Error handling now checks for response.error field.

TIMESTAMP: 2026-07-31T23:15:00+05:00
COMPONENT: dashboard_login_handleAdminLogin
USER: id=N/A; email=fir***@***
ERROR: handleAdminLogin function not found in auth.js
ACTION: Added window.handleAdminLogin function to auth.js for dashboard/login.html compatibility. Function handles credentials login with AdminLoginViewSet and OTP flow.
FILES_MODIFIED: static/js/auth.js
BACKUPS_CREATED: static/js/auth.js.bak
NOTE: Added window.handleAdminLogin function to auth.js. Function calls /api/v1/users/admin/login/ with credentials action. If session_id returned, shows OTP popup. Supports redirect on success.

TIMESTAMP: 2026-07-31T23:20:00+05:00
COMPONENT: admin_login_response_format_all
USER: id=N/A; email=fir***@***
ERROR: Multiple response format mismatches found
ACTION: Fixed handleAdminEmailOtpRequest and handleAdminPasswordLogin to handle both new format (ok:true, token/refresh) and legacy format (success/redirect, access/refresh). Added session_id fallback for OTP flow.
FILES_MODIFIED: static/js/auth.js
BACKUPS_CREATED: static/js/auth.js.bak
NOTE: Fixed all admin login functions (handleAdminEmailOtpRequest, handleAdminPasswordLogin, handleOtpVerification) to correctly handle admin login verify_otp response format. Check response.ok, response.success||response.redirect, and response.session_id.

TIMESTAMP: 2026-07-31T23:30:00+05:00
COMPONENT: dashboard_me_endpoint
USER: id=1; email=fir***@***
ERROR: Dashboard header avatar and username not updating from /me endpoint
ACTION: Fixed updateTopbarUser function in base.js to properly handle user data from /me endpoint. Added safeText helper for display name. Endpoint now returns full_name, avatar_url, roles array correctly.
FILES_MODIFIED: static/dashboard/js/base.js
BACKUPS_CREATED: static/dashboard/js/base.js.bak
NOTE: Dashboard base.js updateTopbarUser now properly displays username from user.full_name||user.email||user.username and avatar from user.avatar_url. All fields present in /me response.
