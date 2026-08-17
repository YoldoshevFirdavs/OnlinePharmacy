import re
import uuid


def check_uzbekistan(phone):
    """+998XXXXXXXXX formatini tekshiradi"""
    return bool(re.match(r"^\+998\d{9}$", phone))


def check_usa(phone):
    """+1XXXXXXXXXX formatini tekshiradi"""
    return bool(re.match(r"^\+1\d{10}$", phone))


def check_russia(phone):
    """+7XXXXXXXXXX formatini tekshiradi"""
    return bool(re.match(r"^\+7\d{10}$", phone))


# Barcha tekshiruvlar ro'yxati
VALIDATORS = [
    {"code": "+998", "func": check_uzbekistan},
    {"code": "+7", "func": check_russia},
    {"code": "+1", "func": check_usa},
]


def validate_phone_number(phone):
    """
    Boshiga qarab kerakli tekshiruv funksiyasini chaqiradi
    """
    for item in VALIDATORS:
        if phone.startswith(item["code"]):
            return item["func"](phone)
    return len(phone) >= 7


def generate_otp(length=4):
    """Tasodifiy OTP kod yaratadi"""
    # Backward-compatible wrapper (new code should use users.otp_service.generate_numeric_code)
    from users.otp_service import generate_numeric_code

    return generate_numeric_code(length)


def generate_session_id():
    """Noyob sessiya ID yaratadi"""
    return str(uuid.uuid4())


def store_otp(session_id, otp, expiry=180):
    """
    Backward-compatible wrapper.
    NOTE: this stores a hashed OTP scoped by purpose="legacy".
    New endpoints use users.otp_service directly.
    """
    from users.otp_service import store_otp as otp_service_store_otp

    # Use the store_otp from otp_service directly
    # The identifier for legacy purposes can be the session_id itself
    otp_service_store_otp(identifier=str(session_id), otp=str(otp), timeout=expiry)


def get_otp(session_id):
    """Redis-dan OTP kodni oladi"""
    from django.core.cache import cache

    # Use the identifier format from otp_service.store_otp
    return cache.get(f"otp_code:{session_id}")


def delete_otp(session_id):
    """OTP kodni o'chirib tashlaydi"""
    from django.core.cache import cache

    # Use the identifier format from otp_service.store_otp
    cache.delete(f"otp_code:{session_id}")


def determine_role(user):
    """
    Foydalanuvchining rolini aniqlaydi.
    Agar user.role maydoni mavjud bo'lsa, uning qiymatini qaytaradi.
    Aks holda, None qaytaradi (masalan, Deliverer uchun).
    """
    if hasattr(user, 'role') and user.role:
        return user.role
    return None
