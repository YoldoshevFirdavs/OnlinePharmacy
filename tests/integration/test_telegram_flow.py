from types import SimpleNamespace

import pytest
from users.models import CustomUser, TelegrambotUser
from users.otp_service import OtpSession, generate_numeric_code, store_otp_hash


class _DummyMessage:
    def __init__(self, text=None, contact=None):
        self.text = text
        self.contact = contact
        self.sent = []

    def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.sent.append({"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})


class _DummyUpdate:
    def __init__(self, tg_user, message: _DummyMessage):
        self.effective_user = tg_user
        self.message = message
        self.callback_query = None


class _DummyContext:
    def __init__(self, args=None):
        self.args = args or []
        self.user_data = {}


@pytest.mark.django_db
def test_telegram_flow_mocked_bot(api_client):
    # user must exist for TelegramLoginView
    user = CustomUser.objects.create_user(phone_number="+998901234567", password=None)

    # 1) website starts telegram login and gets session + deeplink
    res = api_client.post("/api/v1/users/login/telegram/", {"phone_number": user.phone_number}, format="json")
    assert res.status_code == 200
    session_id = res.data["session_id"]

    # 2) simulate bot generating and storing OTP without importing python-telegram-bot
    # (python-telegram-bot==13.x is not compatible with Python 3.13 due to removed stdlib modules)
    otp = generate_numeric_code(4)
    store_otp_hash(session=OtpSession(session_id=session_id, purpose="telegram"), code=otp, ttl_seconds=180)

    # 3) Verify via API and get JWT
    verify = api_client.post("/api/v1/users/verify-otp/", {"channel": "telegram", "session_id": session_id, "code": otp}, format="json")
    assert verify.status_code == 200
    assert "access" in verify.data
    assert "refresh_token" in verify.cookies

    # 4) One-time use: replay should fail
    replay = api_client.post("/api/v1/users/verify-otp/", {"channel": "telegram", "session_id": session_id, "code": otp}, format="json")
    assert replay.status_code == 400


