from rest_framework import serializers
from django.conf import settings
from .models import CustomUser, Seller, SubscribedUser, Deliverer
from django.contrib.auth import get_user_model
import phonenumbers
from phonenumbers import PhoneNumberFormat

User = get_user_model()

DEFAULT_AVATAR_URL = "/static/images/default_avatar.png"

class PhoneNumberField(serializers.CharField):
    """
    Custom serializer field for phone numbers, validating and normalizing to E.164 format.
    """
    def to_internal_value(self, data):
        if not data:
            return None
        
        # Attempt to parse the number using the default region from settings
        try:
            parsed_number = phonenumbers.parse(data, settings.PHONENUMBER_DEFAULT_REGION)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise serializers.ValidationError("Noto'g'ri telefon raqami formati.")

        if not phonenumbers.is_valid_number(parsed_number):
            raise serializers.ValidationError("Noto'g'ri telefon raqami.")
        
        # Normalize to E.164 format
        return phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    phone_number = PhoneNumberField(required=False, allow_null=True) # Use custom field

    class Meta:
        model = CustomUser
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'avatar', 'avatar_url',
            'address', 'telegram_id', 'is_verified', 'date_joined', 'is_staff', 'role',
        ]
        read_only_fields = ['is_verified', 'date_joined', 'telegram_id', 'is_staff', 'role', 'id']
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'full_name': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
        }

    def _resolve_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            url = obj.avatar.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return DEFAULT_AVATAR_URL

    def get_avatar(self, obj):
        return self._resolve_avatar_url(obj)

    def get_avatar_url(self, obj):
        return self._resolve_avatar_url(obj)

    def validate_phone_number(self, value):
        if value is None: # Allow null phone number
            return None
        if self.instance and value:
            if CustomUser.objects.exclude(id=self.instance.id).filter(phone_number=value).exists():
                raise serializers.ValidationError("Bu telefon raqami allaqachon mavjud.")
        return value

    def validate_email(self, value):
        if value == "":
            return None
        if self.instance and value:
            if CustomUser.objects.exclude(id=self.instance.id).filter(email=value).exists():
                raise serializers.ValidationError("Bu Gmail manzili allaqachon mavjud.")
        return value

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.FILES.get('avatar'):
            instance.avatar = request.FILES['avatar']
        return super().update(instance, validated_data)


class SellerSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Seller
        fields = [
            'id', 'user', 'user_details', 'shop_name', 'slug', 'avatar',
            'short_description', 'description', 'address', 'licence_number',
            'tax_id', 'is_verified', 'rating', 'balance', 'sells_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['is_verified', 'rating', 'balance', 'sells_count']


class RegisterSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=False, allow_null=True) # Use custom field
    email = serializers.EmailField(required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=255, required=True, allow_blank=True)

    def validate(self, data):
        phone = data.get('phone_number')
        email = data.get('email')
        if not phone and not email:
            raise serializers.ValidationError("Telefon raqami yoki email manzilidan biri kiritilishi shart.")
        return data


class VerifySerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=6, required=False)
    otp = serializers.CharField(max_length=6, required=False)
    phone_number = serializers.CharField(max_length=20, required=False) # Keep as CharField for raw input
    email = serializers.EmailField(required=False)


class TelegramLoginSerializer(serializers.Serializer):
    phone_number = PhoneNumberField() # Use custom field
    full_name = serializers.CharField(max_length=255, required=True, allow_blank=False)


class SubscribedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedUser
        fields = ['id', 'user', 'telegram_user', 'email', 'is_verified', 'subscribed_at']
        read_only_fields = ['id', 'user', 'subscribed_at']

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('Email required')
        if not value.lower().endswith('@gmail.com'):
            raise serializers.ValidationError('Only gmail.com addresses are accepted.')
        return value

    def create(self, validated_data):
        email = validated_data.get('email', '').strip().lower()
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


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    phone_number = PhoneNumberField(required=False, allow_null=True) # Use custom field
    password = serializers.CharField(max_length=128, required=False)
    action = serializers.CharField(max_length=50)
    otp = serializers.CharField(max_length=6, required=False)
    session_id = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        action = data.get('action')
        username = data.get('username')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')
        otp = data.get('otp')
        session_id = data.get('session_id')

        if action == 'credentials':
            if not (username or email or phone_number):
                raise serializers.ValidationError("Login uchun username, email yoki telefon raqami kerak.")
            if not password:
                raise serializers.ValidationError("Parol kiritilishi shart.")
        elif action == 'request_otp':
            if not (email or phone_number):
                raise serializers.ValidationError("OTP so'rash uchun email yoki telefon raqami kerak.")
        elif action == 'verify_otp':
            if not (email or phone_number):
                raise serializers.ValidationError("OTP tasdiqlash uchun email yoki telefon raqami kerak.")
            if not otp:
                raise serializers.ValidationError("OTP kodi kiritilishi shart.")
            if not session_id:
                raise serializers.ValidationError("Session ID kiritilishi shart.")
        else:
            raise serializers.ValidationError("Noto'g'ri 'action' qiymati.")
        return data


class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    phone_number = PhoneNumberField() # Use custom field

    class Meta:
        model = Deliverer
        fields = '__all__'


class DelivererOnboardingSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True)
    # Assuming phone_number is not directly part of this serializer's input,
    # but rather comes from the associated user or is set during Deliverer creation.


class DelivererStripeConnectSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    deliverer_id = serializers.IntegerField()
    payment_method_id = serializers.CharField(max_length=255)


class TestAdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = PhoneNumberField(required=False, allow_null=True) # Use custom field

    def validate(self, data):
        if not settings.DEBUG:
            raise serializers.ValidationError("This serializer is only available in DEBUG mode.")

        email = data.get('email')
        phone_number = data.get('phone_number')

        if not email and not phone_number:
            raise serializers.ValidationError("Email or phone number must be provided.")

        try:
            if email:
                user = User.objects.get(email=email, is_staff=True)
            else:
                user = User.objects.get(phone_number=phone_number, is_staff=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Admin user not found.")

        data['user'] = user
        return data


class RoleDetermineSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        phone = data.get('phone_number')
        email = data.get('email')
        if not phone and not email:
            raise serializers.ValidationError("Telefon raqami yoki email manzilidan biri kiritilishi shart.")
        return data


class PayoutSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField(max_length=50)
    created_at = serializers.DateTimeField(read_only=True)
    driver_id = serializers.IntegerField(source='driver.id')
    driver_full_name = serializers.CharField(source='driver.user.full_name')