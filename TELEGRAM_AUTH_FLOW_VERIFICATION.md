# Telegram OTP Authentication Flow - Non-Admin Users

## Overview
Fixed the "session expired" error in Telegram authentication for non-admin users by:
1. Extending session TTL from 5 min (300s) to 30 min (1800s)
2. Using unified `admin_session` namespace instead of separate `auth_session`
3. Implementing bot handler logic to send OTP codes to non-admin users
4. Adding session TTL refresh during user interaction

## Complete Flow

### Step 1: User Initiates Telegram Login
**Endpoint:** `POST /api/v1/users/login/telegram/`
**Request:** 
```json
{
  "phone_number": "+998XXXXXXXXX",
  "telegram_id": "123456789",
  "name": "User Name"
}
```

**Backend Actions:** (`users/views.py:TelegramLoginView`)
1. Validates phone_number exists or creates new user
2. Calls `_create_telegram_otp_session(request, user, identifier)`
3. Generates 4-digit OTP code: `store_bot_otp(session.session_id, otp_code, ttl=1800)`
   - Stores hashed OTP in cache: `otp:{session_id}:telegram`
   - Stores plain OTP in cache: `otp:{session_id}:telegram:delivery` (TTL: 1800s)
4. Creates unified admin_session entry:
   ```python
   admin_session = {
       "user_id": user.id,
       "phone_number": str(identifier),
       "flow": "telegram_user",  # Non-admin marker
       "created_at": int(time.time()),
   }
   cache.set(f"admin_session:{session_id}", admin_session, timeout=1800)
   ```
5. Returns response with deeplink and metadata

**Response:**
```json
{
  "fallback": "otp",
  "message": "Telegram orqali 4 xonali OTP yuborildi.",
  "otp_required": true,
  "session_id": "Zjsoy9aPi96Eusc709tbhA",
  "expected_length": 4,
  "delivery": "telegram",
  "deeplink": "https://t.me/authversabot?start=Zjsoy9aPi96Eusc709tbhA",
  "otp_sent": true,
  "role": "user",
  "is_admin": false,
  "bot_message": "Telegram botdagi 4 xonali kodni kiriting."
}
```

### Step 2: User Clicks Telegram Deeplink
**Bot Handler:** `telegram_bot/runbot1.py:start_handler()`

**Execution:**
1. Bot receives `/start {session_id}`
2. Validates admin_session exists and not expired
3. Checks user exists and matches session user_id
4. Prompts user to share phone number via button
5. User clicks button → sends contact

### Step 3: Bot Verifies Phone
**Bot Handler:** `telegram_bot/runbot1.py:contact_handler()`

**Execution:**
1. Receives user's phone number
2. Validates phone matches expected phone in session
3. Retrieves admin_session and checks flow type
4. **For non-admin flow (`flow="telegram_user"`)**:
   - Retrieves OTP code from cache: `cache.get(f"otp:{session_id}:telegram:delivery")`
   - Sends to user: `"Sizning 4 xonali kod: {otp_code}\n\nLogin sahifasida ushbu kodni kiriting."`
   - Marks session as verified: `admin_session["verified"] = True`
5. **For admin flow** (different handling, maintains backward compatibility)

### Step 4: User Enters OTP Code in Client
**Endpoint:** `POST /api/v1/users/verify-otp/`
**Request:**
```json
{
  "session_id": "Zjsoy9aPi96Eusc709tbhA",
  "code": "1234",
  "identifier": "+998XXXXXXXXX"
}
```

**Backend Actions:** (`users/views.py:VerifyOtpView`)
1. **Refresh session TTL** before verification:
   ```python
   refresh_session_ttl(session_id, ttl=ADMIN_SESSION_TTL)
   ```
   - Extends `admin_session:{session_id}` TTL to 1800s
   - Extends OTP caches TTL to 1800s
   - Ensures session won't expire if user was delayed

2. Verify OTP code:
   - Calls `otp_service.verify_otp_once(session_id, code, identifier)`
   - Retrieves session from updated `get_session_meta()`:
     ```python
     # Now checks both namespaces:
     auth_session:{session_id}    # Legacy/email flow
     admin_session:{session_id}   # Admin and non-admin Telegram flows
     ```
   - Gets OTP hash and verifies against provided code
   - Uses constant-time comparison to prevent timing attacks

3. On success:
   - Creates Django session and logs in user
   - Generates JWT tokens
   - Returns user data with redirect URL

## Cache Key Structure

### Session Storage
```
Key: admin_session:{session_id}
Value: {
  "user_id": int,
  "phone_number": str,
  "flow": "telegram_user" | "telegram_deeplink",  # Non-admin vs admin
  "created_at": int(timestamp),
  "verified": bool  # Set after phone verification
}
TTL: 1800 seconds (30 minutes)
```

### OTP Storage
```
Key: otp:{session_id}:telegram
Value: {"hash": str, "salt": str, "algorithm": "sha256"}
TTL: 1800 seconds (30 minutes)

Key: otp:{session_id}:telegram:delivery
Value: "1234"  # Plain OTP code for bot delivery
TTL: 1800 seconds (30 minutes)
```

## Key Improvements

| Issue | Before | After |
|-------|--------|-------|
| **TTL** | 5 min (300s) | 30 min (1800s) |
| **Session Namespace** | Separate `auth_session` | Unified `admin_session` |
| **OTP Delivery** | Not sent to user | Bot sends via Telegram message |
| **Session Lookup** | Single namespace (failed for admin_session) | Dual namespace (both auth_session and admin_session) |
| **TTL Refresh** | No extension on user interaction | Extended when user submits OTP |
| **Error Message** | "session_not_found_or_expired" | Clear, specific error messages |

## Error Handling

### Session Expired
- **Before:** Cache entry expires after 5 min, verification fails
- **After:** TTL is 30 min + refreshed on user interaction

### OTP Code Not Found
- Bot detects missing OTP: `"OTP kod topilmadi. Login bekor qilindi."`
- User is directed back to login

### Phone Mismatch
- Bot validates phone matches session
- Prevents unauthorized access

### Telegram ID Mismatch (Admin)
- For admin users, telegram_id must match account
- Prevents account hijacking

## Testing Checklist

- [ ] User starts Telegram login flow
- [ ] Deeplink generated correctly with session_id
- [ ] Bot receives start command and prompts phone verification
- [ ] User shares phone number
- [ ] Bot displays OTP code: "Sizning 4 xonali kod: XXXX"
- [ ] User enters code in client app
- [ ] Verification succeeds with user logged in
- [ ] OTP verification fails gracefully if code wrong
- [ ] Session doesn't expire if user takes >5 min (now 30 min)
- [ ] Admin Telegram flow still works (backward compatible)
- [ ] Email OTP flow still works (backward compatible)

## Code Changes

### 1. `users/views.py`
- Import: Added `ADMIN_SESSION_TTL`, `refresh_session_ttl`
- `_create_telegram_otp_session()`: Uses admin_session namespace + flow marker
- `VerifyOtpView.post()`: Calls `refresh_session_ttl()` before verification

### 2. `users/otp_service.py`
- `get_session_meta()`: Now checks both `auth_session` and `admin_session`
- Added: `refresh_session_ttl()` function to extend TTL on user interaction

### 3. `telegram_bot/runbot1.py`
- `contact_handler()`: Detects flow type and sends OTP to non-admin users

## Backward Compatibility

✅ All changes maintain backward compatibility:
- Email OTP flow: Unchanged, still uses `auth_session` namespace
- Admin Telegram flow: Enhanced, still uses `admin_session` with `flow="telegram_deeplink"`
- Admin credentials flow: Unchanged
- Existing sessions: TTL refresh handles both namespaces

## Performance Impact

- **Cache Lookups:** +1 fallback check in `get_session_meta()` (minimal, only if first lookup fails)
- **TTL Refresh:** Single cache.set() operation before each verification
- **Memory:** Same cache size, just renamed keys for consistency
- **Network:** No additional bot messages (OTP sent during normal flow)

## Notes

- OTP TTL now matches admin session TTL (1800s) for consistency
- Session is "verified" only after phone confirmation by bot
- No changes needed to client-side OTP entry form
- Admin and non-admin flows can coexist in same cache namespace
