import requests
import time
import os

BASE = 'http://127.0.0.1:8000/api/v1/users'
REG_URL = f"{BASE}/registration/"
VERIFY_URL = f"{BASE}/verify-otp/"
ME_URL = f"{BASE}/me/"

# Wait for service
for i in range(40):
    try:
        r = requests.get('http://127.0.0.1:8000/healthcheck/')
        if r.status_code < 500:
            break
    except Exception:
        pass
    time.sleep(1)

# Use unique email to avoid conflicts
email = f"auto_test+{int(time.time())}@example.com"
payload = {"email": email, "full_name": "Auto Test"}

try:
    r = requests.post(REG_URL, json=payload, timeout=10)
    data = r.json() if r.content else {}
except Exception as e:
    print('failed')
    raise SystemExit(1)

session_id = data.get('session_id')
otp_code = data.get('otp_code')

# If otp_code not in response, try to read from Redis (if available)
if not otp_code:
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        rc = redis.from_url(redis_url)
        # Try identifier key
        ident_key = f"otp_code:{email}"
        stored = rc.get(ident_key)
        if stored:
            # if stored JSON contains 'hash' we cannot recover code; abort
            otp_code = None
    except Exception:
        otp_code = None

if not session_id or not otp_code:
    print('failed')
    raise SystemExit(1)

# Verify
try:
    r2 = requests.post(VERIFY_URL, json={"session_id": session_id, "code": otp_code}, timeout=10)
    data2 = r2.json() if r2.content else {}
except Exception:
    print('failed')
    raise SystemExit(1)

access = data2.get('access')
if not access:
    print('failed')
    raise SystemExit(1)

# Check /me
try:
    hdr = {'Authorization': f'Bearer {access}'}
    r3 = requests.get(ME_URL, headers=hdr, timeout=10)
    if r3.status_code == 200:
        print('worked')
    else:
        print('failed')
except Exception:
    print('failed')
    raise SystemExit(1)
