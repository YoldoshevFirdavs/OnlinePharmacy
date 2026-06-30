#!/usr/bin/env python
"""Full OTP flow diagnostic - registration, bot, and verification"""
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.otp_service import (
    create_otp_session, bind_session_to_user, store_otp,
    generate_numeric_code, hash_otp, verify_otp_once,
    _store_otp_for_test_session, OtpSession, get_session_meta, get_otp
)
import json
import redis

# Redis connection
r = redis.from_url('redis://localhost:6379/0')

print("=" * 70)
print("FULL OTP FLOW DIAGNOSTIC")
print("=" * 70)

# Test Registration Flow
print("\n1. REGISTRATION FLOW:")
reg_session = create_otp_session(purpose="registration")
reg_identifier = "+998901234567"
reg_user_id = 99999

print(f"   Session ID: {reg_session.session_id}")
bind_session_to_user(reg_session.session_id, reg_user_id, reg_identifier)

otp_code = generate_numeric_code(6)
hashed_otp, salt = hash_otp(otp_code)
store_otp(reg_identifier, json.dumps({"hash": hashed_otp, "salt": salt}), timeout=900)

print(f"   OTP: {otp_code}")
print(f"   Identifier: {reg_identifier}")

# Check Redis keys
auth_key = f"auth_session:{reg_session.session_id}"
otp_key = f"otp_code:{reg_identifier}"
print(f"\n   Redis keys:")
print(f"   - {auth_key}")
print(f"   - {otp_key}")

auth_data = r.get(auth_key)
otp_data = r.get(otp_key)
print(f"\n   Values:")
print(f"   - auth_session: {auth_data}")
print(f"   - otp_code: {otp_data}")

# Test Registration OTP verification
print("\n   Testing registration OTP verification...")
result = verify_otp_once(session_id=reg_session.session_id, code=otp_code)
print(f"   Result: {result}")

# Test Bot Flow
print("\n2. BOT FLOW:")
bot_session = create_otp_session(purpose="telegram")
bot_identifier = "+998902222222"
bot_user_id = 88888

bind_session_to_user(bot_session.session_id, bot_user_id, bot_identifier)
bot_otp = generate_numeric_code(4)
_store_otp_for_test_session(session=OtpSession(session_id=bot_session.session_id, purpose="telegram"), code=bot_otp)

print(f"   Session ID: {bot_session.session_id}")
print(f"   Bot OTP: {bot_otp}")

bot_key = f"otp:{bot_session.session_id}:telegram"
print(f"\n   Redis key: {bot_key}")
bot_data = r.get(bot_key)
print(f"   Value: {bot_data}")

print("\n   Testing bot OTP verification...")
result = verify_otp_once(session_id=bot_session.session_id, code=bot_otp)
print(f"   Result: {result}")

# Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)
print(f"\nRedis keys count: {len(r.keys('*'))}")

all_keys = r.keys('*')
print("\nAll Redis keys:")
for k in all_keys:
    key_str = k.decode() if isinstance(k, bytes) else k
    ttl = r.ttl(k)
    val = r.get(k)
    print(f"   {key_str} -> TTL: {ttl}s, Value: {str(val)[:50]}...")

print("\n" + "=" * 70)
print("TEST COMPLETED")
print("=" * 70)