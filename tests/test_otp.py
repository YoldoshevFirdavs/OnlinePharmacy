import json
import hashlib
import pytest
from django.core.cache import cache
from users.utils import generate_otp
from users.otp_service import (
    OtpSession,
    generate_numeric_code,
    rate_limit_or_raise,
    verify_otp_once,
    hash_otp,
    store_otp_hash,
)


def test_generate_otp():
    tg = generate_otp(4)
    em = generate_otp(6)
    assert isinstance(tg, str) and tg.isdigit() and len(tg) == 4
    assert isinstance(em, str) and em.isdigit() and len(em) == 6


def test_generate_numeric_code_digits_only():
    code = generate_numeric_code(8)
    assert code.isdigit()
    assert len(code) == 8


def test_hash_otp_consistency():
    # To test consistency, we use a fixed salt or no salt. 
    # Calling hash_otp("1234") directly generates a tuple (hash, salt) because salt is None.
    # To compare them, we use the same salt.
    h1, salt1 = hash_otp("1234")
    h2 = hash_otp("1234", salt=salt1)
    assert h1 == h2
    assert h1 != hash_otp("1235", salt=salt1)


def test_store_and_verify_otp_success():
    session = OtpSession(session_id="sess1", purpose="telegram")
    otp = "1234"
    store_otp_hash(session=session, code=otp, ttl_seconds=180)

    # stored value should be hashed-only
    raw = cache.get("otp:sess1:telegram")
    assert raw is not None
    payload = json.loads(raw)
    # The store_otp_hash(session=...) hashes using sha256 without salt in our implementation
    assert payload.get("h") == hashlib.sha256(otp.encode()).hexdigest()
    assert otp not in raw

    assert verify_otp_once(session=session, code=otp) is True
    assert cache.get("otp:sess1:telegram") is None


def test_verify_otp_fails_after_use():
    session = OtpSession(session_id="sess2", purpose="email")
    otp = "654321"
    store_otp_hash(session=session, code=otp, ttl_seconds=180)

    assert verify_otp_once(session=session, code=otp) is True
    assert verify_otp_once(session=session, code=otp) is False


def test_rate_limit_blocks():
    scope = "test-scope"
    rate_limit_or_raise(scope, window_seconds=60)
    with pytest.raises(ValueError):
        rate_limit_or_raise(scope, window_seconds=60)


