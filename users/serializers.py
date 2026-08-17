import phonenumbers
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _
from phonenumbers import PhoneNumberFormat
from PIL import Image
from rest_framework import serializers

from .models import CustomUser, DeliveryDriver, Seller, SubscribedUser

User = get_user_model()


def determine_role(user):
    """
    Determine user role from server-side authoritative sources.
    Uses user.role field only.
    """
    if not user:
        return "user"

    # Return the role from the user.role field
    # If role is None or empty, return "user" as default
    return user.role if user.role else "user"


def validate_image_file(file):
    try:
        img = Image.open(file)
        img.verify()
    except Exception:
        raise serializers.ValidationError("Yuklangan fayl yaroqli rasm emas.")
    return file


class PhoneNumberField(serializers.CharField):

    def to_internal_value(self, data):
        data = str(data).strip()
        if not data:
            return None

        if len(data) == 9 and data.isdigit() and not data.startswith("+"):
            data = f"+{settings.PHONENUMBER_DEFAULT_REGION_CODE}{data}"

        try:

            parsed_number = phonenumbers.parse(
                data, settings.PHONENUMBER_DEFAULT_REGION
            )
            if not phonenumbers.is_valid_number(parsed_number):

                parsed_number = phonenumbers.parse(data)
                if not phonenumbers.is_valid_number(parsed_number):
                    raise serializers.ValidationError("Telefon raqami noto‘g‘ri.")

            return phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise serializers.ValidationError("Telefon raqami noto‘g‘ri formatda.")
        except Exception:
            raise serializers.ValidationError(
                "Telefon raqamini tekshirishda xato yuz berdi."
            )


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    role = serializers.SerializerMethodField()
    avatar = serializers.ImageField(
        validators=[validate_image_file], required=False, allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "phone_number",
            "email",
            "full_name",
            "telegram_id",
            "address",
            "avatar",
            "avatar_url",
            "role",
            "is_verified",
            "date_joined",
            "is_staff",
            "is_banned",
            "banned_for",
            "ban_reason",
            "ban_until",
            "is_permanent_ban",
        ]
        read_only_fields = [
            "is_verified",
            "date_joined",
            "telegram_id",
            "is_staff",
            "role",
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True, "allow_null": True},
            "full_name": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
        }

    def get_avatar_url(self, obj):
        if hasattr(obj, "seller") and obj.seller:
            return obj.seller.get_avatar_url
        if obj.avatar:
            return obj.avatar.url
        return "/static/images/default_avatar.png"

    def get_role(self, obj):
        """Compute a single, primary role based on user properties using the helper function."""
        return determine_role(obj)

    def validate_phone_number(self, value):
        if not value:
            return value # Allow empty phone number if not required
        try:
            parsed_number = phonenumbers.parse(value, settings.PHONENUMBER_DEFAULT_REGION)
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError("Telefon raqami noto'g'ri formatda.")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise serializers.ValidationError("Telefon raqami noto'g'ri formatda.")

        if self.instance and value:
            if (
                CustomUser.objects.exclude(id=self.instance.id)
                .filter(phone_number=value)
                .exists()
            ):
                raise serializers.ValidationError(
                    "Bu telefon raqami allaqachon mavjud."
                )
        elif not self.instance and value: # For create operations
            if CustomUser.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError(
                    "Bu telefon raqami allaqachon mavjud."
                )
        return value

    def validate_email(self, value):
        if value == "":
            return None # Allow empty email if not required
        if self.instance and value:
            if (
                CustomUser.objects.exclude(id=self.instance.id)
                .filter(email=value)
                .exists()
            ):
                raise serializers.ValidationError("Bu Gmail manzili allaqachon mavjud.")
        elif not self.instance and value: # For create operations
            if CustomUser.objects.filter(email=value).exists():
                raise serializers.ValidationError("Bu Gmail manzili allaqachon mavjud.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        validated_data["role"] = "user"
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        avatar = validated_data.pop("avatar", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        if avatar:
            if hasattr(instance, "seller") and instance.seller:
                instance.seller.avatar = avatar
                instance.seller.save()
            else:
                instance.avatar = avatar

        instance.save()
        return instance


class AdminVerifyResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    access = serializers.CharField(allow_null=True, required=False)
    refresh = serializers.CharField(allow_null=True, required=False)
    ban_until = serializers.DateTimeField(allow_null=True, required=False)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "access" in rep and rep["access"] is not None:
            rep["access"] = str(rep["access"])
        if "refresh" in rep and rep["refresh"] is not None:
            rep["refresh"] = str(rep["refresh"])
        return rep


class UserPublicSerializer(serializers.ModelSerializer):
    """Minimal user data for session checking."""

    avatar_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if hasattr(obj, "seller") and obj.seller:
            return obj.seller.get_avatar_url
        return obj.avatar.url if obj.avatar else "/static/images/default_avatar.png"

    def get_role(self, obj):
        """Compute a single, primary role based on user properties using the helper function."""
        return determine_role(obj)

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "phone_number",
            "role",
            "is_active",
            "full_name",
            "avatar_url",
        )
        read_only_fields = fields


class SellerSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source="user", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = [
            "id",
            "user",
            "user_details",
            "shop_name",
            "slug",
            "avatar",
            "avatar_url",
            "short_description",
            "description",
            "address",
            "licence_number",
            "tax_id",
            "is_verified",
            "rating",
            "balance",
            "sells_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_verified", "rating", "balance", "sells_count"]

    def get_avatar_url(self, obj):
        return obj.get_avatar_url


class RegisterSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        phone = data.get("phone_number")
        email = data.get("email")
        if not phone and not email:
            raise serializers.ValidationError(
                "Telefon raqami yoki email manzili kiritilishi shart."
            )
        return data


class TelegramLoginSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telegram_id = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True, default="user")  # Added role field

    def validate(self, data):
        phone_number = data.get("phone_number")
        telegram_id = data.get("telegram_id")

        if not phone_number and not telegram_id:
            raise serializers.ValidationError(
                "Telegram orqali kirish uchun telefon raqami yoki Telegram ID kerak."
            )
        
        # Validate role
        role = data.get("role", "user")
        if role not in ["user", "admin", "seller"]:
            raise serializers.ValidationError(
                {"role": "Noto'g'ri role. 'user', 'admin', yoki 'seller' bo'lishi kerak."}
            )

        return data


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification with proper session and code handling."""

    session_id = serializers.CharField(required=True)
    code = serializers.CharField(required=True, write_only=True)
    identifier = serializers.CharField(required=False, allow_blank=True)
    action = serializers.CharField(required=True)

    def validate_code(self, value):
        """Validate OTP code is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("OTP code is required.")
        return value.strip()


class VerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    session_id = serializers.CharField()
    identifier = serializers.CharField(required=False, allow_blank=True)
    method = serializers.ChoiceField(choices=["email", "telegram"], required=False)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class SubscribedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedUser
        fields = [
            "id",
            "user",
            "telegram_user",
            "email",
            "is_verified",
            "subscribed_at",
        ]
        read_only_fields = ["id", "user", "subscribed_at"]

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email kiritilishi shart.")
        if not value.lower().endswith("@gmail.com"):
            raise serializers.ValidationError(
                "Faqat gmail.com manzillari qabul qilinadi."
            )
        return value

    def create(self, validated_data):
        email = validated_data.get("email", "").strip().lower()
        user = None
        try:
            user = CustomUser.objects.filter(email__iexact=email).first()
        except Exception:
            user = None

        subscriber, created = SubscribedUser.objects.get_or_create(email=email)
        if user:
            subscriber.user = user
            subscriber.save()
        return subscriber


class AdminSetupSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        if not value.lower().endswith("@gmail.com"):
            raise serializers.ValidationError(
                "Faqat gmail.com manzillari qabul qilinadi."
            )
        return value


class DeliveryDriverSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = DeliveryDriver
        fields = (
            "id",
            "user",
            "phone_number",
            "vehicle_info",
            "status",
            "avatar",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.create_user(**user_data)
        driver = DeliveryDriver.objects.create(user=user, **validated_data)
        return driver

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class TestAdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        # Normalize phone number if provided, using the field's logic
        phone_number_internal = self.fields["phone_number"].to_internal_value(
            data.get("phone_number")
        )

        user = User.objects.filter(email__iexact=email, is_staff=True).first()

        if not user:
            raise serializers.ValidationError("Bunday admin foydalanuvchi topilmadi.")

        # Strict checks as requested
        if not user.check_password(password):
            raise serializers.ValidationError("Parol noto'g'ri.")

        if user.full_name != full_name:
            raise serializers.ValidationError("To'liq ism mos kelmadi.")

        if phone_number_internal and user.phone_number != phone_number_internal:
            raise serializers.ValidationError("Telefon raqami mos kelmadi.")

        data["user"] = user
        return data


class RoleDetermineSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=False, allow_blank=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class AdminLoginSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            "request_verification",
            "gmail_oauth",
            "verify_otp",
            "credentials",
            "request_otp",
            "telegram",
        ],
        required=True,
    )
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    otp = serializers.CharField(required=False, allow_blank=True, write_only=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, data):
        action = data.get("action")
        username = data.get("username")
        email = data.get("email")
        phone_number = data.get("phone_number")
        password = data.get("password")
        otp = data.get("otp")
        session_id = data.get("session_id")
        code = data.get("code")

        if action == "request_verification":
            if not (email or phone_number):
                raise serializers.ValidationError(
                    "request_verification requires email or phone_number"
                )
        elif action == "request_otp":
            if not (email or phone_number):
                raise serializers.ValidationError(
                    "request_otp requires email or phone_number"
                )
        elif action == "telegram":
            if not (phone_number or data.get("telegram_id")):
                pass  # validation handled in view for now
        elif action == "gmail_oauth":
            if not code:
                raise serializers.ValidationError("gmail_oauth requires code")
        elif action == "verify_otp":
            if not (session_id or phone_number or email) or not otp:
                # The view handles multiple ways, but serializer should be consistent
                pass
        elif action == "credentials":
            if not (username or email or phone_number) or not password:
                raise serializers.ValidationError(
                    "credentials requires identifier and password"
                )
        else:
            raise serializers.ValidationError("Unknown action")

        return data


class GmailOAuthSerializer(serializers.Serializer):
    code = serializers.CharField()
    redirect_uri = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not getattr(settings, "GOOGLE_CLIENT_ID", None) or not getattr(
            settings, "GOOGLE_CLIENT_SECRET", None
        ):
            raise serializers.ValidationError(
                "Google OAuth client credentials not configured"
            )
        return data

    def build_token_exchange_payload(self):
        return {
            "code": self.validated_data.get("code"),
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": self.validated_data.get("redirect_uri"),
            "grant_type": "authorization_code",
        }


# CUSTOM JWT SERIALIZER
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom TokenObtainPairSerializer that includes user role in JWT claims.
    Role is computed server-side via determine_role() for security.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to token
        token["role"] = determine_role(user)
        token["email"] = user.email or ""
        token["full_name"] = user.full_name or ""
        return token



class UserBanSerializer(serializers.ModelSerializer):
    """Ban mehanism bilan bog'liq user ma'lumotlari."""
    banned_by_name = serializers.CharField(source='banned_by.full_name', read_only=True, allow_null=True)
    ban_until_formatted = serializers.SerializerMethodField()
    is_ban_active = serializers.SerializerMethodField()
    time_remaining_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'phone_number',
            'full_name',
            'role',
            'banned_for',
            'ban_reason',
            'ban_until',
            'ban_until_formatted',
            'is_permanent_ban',
            'banned_by',
            'banned_by_name',
            'is_ban_active',
            'time_remaining_seconds',
        ]
        read_only_fields = [
            'id',
            'banned_by_name',
            'is_ban_active',
            'time_remaining_seconds',
            'ban_until_formatted',
        ]
    
    def get_ban_until_formatted(self, obj):
        """Ban tugash vaqtini insan o'qiga tushunadigan formatda qaytarish."""
        if not obj.ban_until:
            return None
        from django.utils.timezone import localtime
        local_time = localtime(obj.ban_until)
        return local_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_is_ban_active(self, obj):
        """Ban hozir faol yoki yo'q."""
        return obj.is_active_ban()
    
    def get_time_remaining_seconds(self, obj):
        """Vaqtli ban uchun qolgan sekund soni."""
        if not obj.ban_until or obj.is_permanent_ban:
            return None
        from django.utils import timezone
        remaining = (obj.ban_until - timezone.now()).total_seconds()
        return max(0, int(remaining))


class BanUserSerializer(serializers.Serializer):
    """Ban berish uchun serializer."""
    user_id = serializers.IntegerField()
    page = serializers.CharField(max_length=255, help_text="Qaysi page uchun ban (masalan: 'admin_login')")
    duration_seconds = serializers.IntegerField(required=False, allow_null=True, help_text="Vaqtli ban bo'lsa, necha sekundga. Null bo'lsa, permanent ban.")
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    is_permanent = serializers.BooleanField(default=False)
    
    def validate_user_id(self, value):
        """User mavjudligini tekshirish."""
        try:
            CustomUser.objects.get(id=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Foydalanuvchi topilmadi.")
        return value
    
    def create(self, validated_data):
        """Ban berish."""
        user = CustomUser.objects.get(id=validated_data['user_id'])
        page = validated_data['page']
        duration_seconds = validated_data.get('duration_seconds')
        reason = validated_data.get('reason', '')
        is_permanent = validated_data.get('is_permanent', False)
        
        # Admin user-ni get qilish (banned_by field uchun)
        from rest_framework.request import Request
        if hasattr(self, 'context') and 'request' in self.context:
            admin_user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        else:
            admin_user = None
        
        user.ban_user(
            page=page,
            duration_seconds=duration_seconds,
            reason=reason,
            banned_by=admin_user,
            is_permanent=is_permanent
        )
        return user


class UnbanUserSerializer(serializers.Serializer):
    """Ban olib tashlash uchun serializer."""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        """User mavjudligini tekshirish."""
        try:
            CustomUser.objects.get(id=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Foydalanuvchi topilmadi.")
        return value
    
    def create(self, validated_data):
        """Ban olib tashlash."""
        user = CustomUser.objects.get(id=validated_data['user_id'])
        user.unban_user()
        return user
