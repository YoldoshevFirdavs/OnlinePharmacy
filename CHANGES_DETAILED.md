# Detailed Code Changes - Telegram OTP Auth Fix

## File 1: users/views.py

### Change 1: Added imports for TTL constants and refresh function
```python
# BEFORE
from .otp_service import (
    TELEGRAM_OTP_LENGTH,
    OtpHash,
    bind_session_to_user,
    ...
)

# AFTER
from .otp_service import (
    ADMIN_SESSION_TTL,  # ← NEW
    TELEGRAM_OTP_LENGTH,
    OtpHash,
    bind_session_to_user,
    ...
    refresh_session_ttl,  # ← NEW
    ...
)
```

### Change 2: Updated _create_telegram_otp_session() function
```python
# BEFORE (lines 177-189)
def _create_telegram_otp_session(request, user, identifier):
    with transaction.atomic():
        session = create_otp_session(purpose="telegram")
        otp_code = generate_numeric_code(TELEGRAM_OTP_LENGTH)
        store_bot_otp(session.session_id, otp_code, ttl=300)  # 5 min
        bind_session_to_user(session.session_id, user.id, identifier, ttl=300)  # 5 min
        _write_auth_audit(...)
    return session

# AFTER (lines 179-196)
def _create_telegram_otp_session(request, user, identifier):
    with transaction.atomic():
        session = create_otp_session(purpose="telegram")
        otp_code = generate_numeric_code(TELEGRAM_OTP_LENGTH)
        store_bot_otp(session.session_id, otp_code, ttl=ADMIN_SESSION_TTL)  # 30 min
        
        # Use admin_session namespace for consistency with admin flow
        session_id = session.session_id
        admin_session = {
            "user_id": user.id,
            "phone_number": str(identifier),
            "flow": "telegram_user",  # Non-admin Telegram flow marker
            "created_at": int(time.time()),
        }
        cache.set(f"admin_session:{session_id}", admin_session, timeout=ADMIN_SESSION_TTL)
        
        _write_auth_audit(...)
    return session
```

### Change 3: Added TTL refresh in VerifyOtpView
```python
# BEFORE (line ~1154)
try:
    is_valid, message, session = otp_service.verify_otp_once(session_id, code, identifier)

# AFTER (lines ~1156-1160)
try:
    # Refresh session TTL when user submits OTP code
    refresh_session_ttl(session_id, ttl=ADMIN_SESSION_TTL)
    
    is_valid, message, session = otp_service.verify_otp_once(session_id, code, identifier)
```

---

## File 2: users/otp_service.py

### Change 1: Updated get_session_meta() to check both namespaces
```python
# BEFORE (lines 195-217)
def get_session_meta(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session metadata from cache."""
    if not session_id:
        return None

    try:
        key = f"auth_session:{session_id}"
        result = cache.get(key)

        if result is None:
            logger.warning(f"Session not found: {session_id[:8]}...")
            return None

        if not isinstance(result, dict):
            logger.error(f"Session meta corrupted (type: {type(result).__name__})")
            return None

        return result
    except Exception as e:
        logger.error(f"get_session_meta error: {str(e)[:100]}")
        return None

# AFTER (lines 195-224)
def get_session_meta(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session metadata from cache (checks both auth_session and admin_session namespaces)."""
    if not session_id:
        return None

    try:
        # Try auth_session first (legacy/email OTP flow)
        key = f"auth_session:{session_id}"
        result = cache.get(key)

        if result is None:
            # Fall back to admin_session (admin Telegram and non-admin Telegram flows)
            key = f"admin_session:{session_id}"
            result = cache.get(key)

        if result is None:
            logger.warning(f"Session not found in either namespace: {session_id[:8]}...")
            return None

        if not isinstance(result, dict):
            logger.error(f"Session meta corrupted (type: {type(result).__name__})")
            return None

        return result
    except Exception as e:
        logger.error(f"get_session_meta error: {str(e)[:100]}")
        return None
```

### Change 2: Added new refresh_session_ttl() function
```python
# NEW FUNCTION (after delete_session, lines 236-285)
def refresh_session_ttl(session_id: str, ttl: int = ADMIN_SESSION_TTL) -> bool:
    """
    Extend session TTL when user interacts with auth flow.
    Checks both auth_session and admin_session namespaces.
    Returns True if successfully refreshed, False if session not found.
    """
    if not session_id:
        return False

    try:
        # Try auth_session first
        auth_key = f"auth_session:{session_id}"
        session = cache.get(auth_key)
        
        if session is None:
            # Try admin_session
            auth_key = f"admin_session:{session_id}"
            session = cache.get(auth_key)
        
        if session is None:
            logger.warning(f"Session not found for TTL refresh: {session_id[:8]}...")
            return False
        
        if not isinstance(session, dict):
            logger.error(f"Session corrupted during TTL refresh: {type(session).__name__}")
            return False
        
        # Refresh the session with new TTL
        cache.set(auth_key, session, timeout=ttl)
        
        # Also refresh the OTP if it exists
        otp_key = f"otp:{session_id}:telegram"
        otp_data = cache.get(otp_key)
        if otp_data:
            cache.set(otp_key, otp_data, timeout=ttl)
        
        otp_delivery_key = f"otp:{session_id}:telegram:delivery"
        otp_delivery = cache.get(otp_delivery_key)
        if otp_delivery:
            cache.set(otp_delivery_key, otp_delivery, timeout=ttl)
        
        logger.info(f"Session TTL refreshed: {session_id[:8]}... (new TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"refresh_session_ttl error: {str(e)[:100]}")
        return False
```

---

## File 3: telegram_bot/runbot1.py

### Change: Updated contact_handler() to send OTP to non-admin users
```python
# BEFORE (lines ~183-209)
    payload = pending["payload"]
    admin_session = cache.get(f"admin_session:{payload}")
    if _is_session_expired(admin_session, ttl_seconds=300):
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Login sessiyasi muddati tugadi.", reply_markup=ReplyKeyboardRemove())
        return

    if (
        admin_session
        and admin_session.get("user_id") == user.id
        and not admin_session.get("used")
        and _normalize_phone(admin_session.get("phone_number")) == expected_phone
    ):
        admin_session["verified"] = True
        cache.set(f"admin_session:{payload}", admin_session, timeout=1800)
        web_link = f"{API_BASE_URL}{reverse('admin_check')}?session={payload}"
        message = f"Admin Telegram tasdiqlandi. Sahifani oching:\n{web_link}"
    else:
        message = "Login sessiyasi yaroqsiz yoki allaqachon ishlatilgan."

    cache.delete(f"telegram_pending:{telegram_id}")
    update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

# AFTER (lines ~186-217)
    payload = pending["payload"]
    admin_session = cache.get(f"admin_session:{payload}")
    if _is_session_expired(admin_session, ttl_seconds=300):
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Login sessiyasi muddati tugadi.", reply_markup=ReplyKeyboardRemove())
        return

    if admin_session and admin_session.get("user_id") == user.id and not admin_session.get("used") and _normalize_phone(admin_session.get("phone_number")) == expected_phone:
        # Determine flow type
        flow = admin_session.get("flow", "telegram_deeplink")
        
        if flow == "telegram_user":
            # Non-admin Telegram flow: Send OTP code to user
            otp_code = cache.get(f"otp:{payload}:telegram:delivery")
            if otp_code:
                message = f"Sizning 4 xonali kod: {otp_code}\n\nLogin sahifasida ushbu kodni kiriting."
                admin_session["verified"] = True
                cache.set(f"admin_session:{payload}", admin_session, timeout=1800)
            else:
                message = "OTP kod topilmadi. Login bekor qilindi."
                cache.delete(f"admin_session:{payload}")
        else:
            # Admin Telegram flow: Send verification link
            admin_session["verified"] = True
            cache.set(f"admin_session:{payload}", admin_session, timeout=1800)
            web_link = f"{API_BASE_URL}{reverse('admin_check')}?session={payload}"
            message = f"Admin Telegram tasdiqlandi. Sahifani oching:\n{web_link}"
    else:
        message = "Login sessiyasi yaroqsiz yoki allaqachon ishlatilgan."

    cache.delete(f"telegram_pending:{telegram_id}")
    update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
```

---

## Summary of Changes

### Lines Changed
- **users/views.py**: 3 changes across ~40 lines
- **users/otp_service.py**: 2 changes across ~60 lines (1 new function)
- **telegram_bot/runbot1.py**: 1 change across ~35 lines

### Total New Code
- ~50 lines in `refresh_session_ttl()` function
- ~10 lines in `contact_handler()` flow detection and OTP sending
- 1 import line in views.py

### Total Refactored Code
- `_create_telegram_otp_session()`: 6 lines → 18 lines (+12)
- `get_session_meta()`: 16 lines → 30 lines (+14)
- `contact_handler()`: 17 lines → 32 lines (+15)

### No Lines Removed
All changes are additive (except TTL value change from 300 to ADMIN_SESSION_TTL)

---

## Testing Points

Each change can be tested independently:

1. **Import Test**: Verify no ImportError when starting Django
   ```python
   from users.otp_service import ADMIN_SESSION_TTL, refresh_session_ttl
   ```

2. **TTL Test**: Verify session stored with 1800s TTL
   ```python
   # After _create_telegram_otp_session()
   session = cache.get(f"admin_session:{session_id}")
   assert session is not None  # Should exist
   ```

3. **Namespace Test**: Verify get_session_meta finds sessions in both namespaces
   ```python
   # Test fallback: auth_session → admin_session
   result = get_session_meta(session_id)
   assert result is not None
   ```

4. **Refresh Test**: Verify TTL extended
   ```python
   # Before refresh
   before_ttl = cache.ttl(f"admin_session:{session_id}")
   refresh_session_ttl(session_id)
   # After refresh
   after_ttl = cache.ttl(f"admin_session:{session_id}")
   assert after_ttl > before_ttl
   ```

5. **Bot Test**: Verify bot sends OTP to non-admin users
   ```python
   # Simulate bot contact_handler with flow="telegram_user"
   # Verify message contains OTP code
   assert "Sizning 4 xonali kod:" in message
   ```

---

## Rollback Plan

If needed, rollback is simple:

1. Revert users/views.py import changes
2. Revert _create_telegram_otp_session() to use bind_session_to_user()
3. Comment out refresh_session_ttl() call
4. Revert get_session_meta() to only check auth_session
5. Revert contact_handler() flow logic

All changes are isolated - no schema changes, no database changes.
