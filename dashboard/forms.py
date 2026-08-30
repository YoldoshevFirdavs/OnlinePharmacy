from django import forms
from django.core.exceptions import ValidationError

from dashboard.widgets import AvatarUploadWidget
from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser, DeliveryDriver


def validate_avatar(file):
    """Validate avatar image file"""
    if file:
        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise ValidationError("Rasm 5MB dan katta bo'la olmaydi.")

        # Check file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise ValidationError("Faqat JPEG, PNG, GIF yoki WebP formatida rasmlar yuklash mumkin.")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "is_default", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-control"}),
        }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "name",
            "slug",
            "category",
            "price",
            "stock",
            "is_active",
            "seller",
            "short_description",
            "instruction",
            "side_effects",
            "contraindications",
            "storage_conditions",
            "is_prescription_required",
            "main_image",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "seller": forms.Select(attrs={"class": "form-control"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "instruction": forms.Textarea(attrs={"class": "form-control"}),
            "side_effects": forms.Textarea(attrs={"class": "form-control"}),
            "contraindications": forms.Textarea(attrs={"class": "form-control"}),
            "storage_conditions": forms.TextInput(attrs={"class": "form-control"}),
            "is_prescription_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "main_image": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False)
    telegram_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "@username yoki 123456789"}),
        required=False,
        help_text="Telegram username (@username) yoki ID (raqamlar)",
    )
    avatar = forms.ImageField(
        widget=AvatarUploadWidget(attrs={"class": "form-control-file"}),
        required=False,
        validators=[validate_avatar],
        help_text="Max 5MB, JPEG/PNG/GIF/WebP",
    )

    class Meta:
        model = CustomUser
        fields = [
            "full_name",
            "email",
            "phone_number",
            "telegram_id",
            "address",
            "avatar",
            "is_staff",
            "is_superuser",
            "is_active",
            "is_verified",
            "role",
            "password",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "@username yoki 123456789"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "role": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_telegram_id(self):
        """Validate Telegram ID"""
        telegram_id = self.cleaned_data.get("telegram_id", "").strip()

        if not telegram_id:
            return telegram_id  # Allow empty

        # Check format
        if telegram_id.startswith("@"):
            username = telegram_id[1:]
            if not username.replace("_", "").isalnum() or len(username) < 5:
                raise forms.ValidationError(
                    "Telegram username noto'g'ri formatda. Namuna: @username (eng kamida 5 ta belgi)"
                )
        else:
            if not telegram_id.isdigit():
                raise forms.ValidationError(
                    "Telegram ID raqamlar bilan yoki @username ko'rinishida bo'lishi kerak. Namuna: 123456789 yoki @username"
                )
            if len(telegram_id) < 5 or len(telegram_id) > 20:
                raise forms.ValidationError("Telegram ID 5 dan 20 ta raqamdan iborat bo'lishi kerak.")

        # Check uniqueness
        qs = CustomUser.objects.filter(telegram_id=telegram_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Bu Telegram ID allaqachon ishlatilgan.")

        return telegram_id

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password"]:
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class DeliveryDriverForm(forms.ModelForm):
    avatar = forms.ImageField(
        widget=AvatarUploadWidget(attrs={"class": "form-control-file"}),
        required=False,
        validators=[validate_avatar],
        help_text="Max 5MB, JPEG/PNG/GIF/WebP",
    )

    class Meta:
        model = DeliveryDriver
        fields = ["user", "phone_number", "vehicle_info", "status", "avatar"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_info": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


# Admin va Deliverer uchun Account Settings formasi
class AccountSettingsForm(forms.ModelForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False)
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False)
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False)
    telegram_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "@username yoki 123456789"}),
        required=False,
        help_text="Telegram username (@username) yoki ID (raqamlar)",
    )
    avatar = forms.ImageField(
        widget=AvatarUploadWidget(attrs={"class": "form-control-file"}),
        required=False,
        validators=[validate_avatar],
        help_text="Max 5MB, JPEG/PNG/GIF/WebP",
    )

    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "phone_number", "avatar", "telegram_id", "address"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "@username yoki 123456789"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_telegram_id(self):
        """Validate Telegram ID"""
        telegram_id = self.cleaned_data.get("telegram_id", "").strip()

        if not telegram_id:
            return telegram_id  # Allow empty

        # Check format
        if telegram_id.startswith("@"):
            username = telegram_id[1:]
            if not username.replace("_", "").isalnum() or len(username) < 5:
                raise forms.ValidationError(
                    "Telegram username noto'g'ri formatda. Namuna: @username (eng kamida 5 ta belgi)"
                )
        else:
            if not telegram_id.isdigit():
                raise forms.ValidationError(
                    "Telegram ID raqamlar bilan yoki @username ko'rinishida bo'lishi kerak. Namuna: 123456789 yoki @username"
                )
            if len(telegram_id) < 5 or len(telegram_id) > 20:
                raise forms.ValidationError("Telegram ID 5 dan 20 ta raqamdan iborat bo'lishi kerak.")

        # Check uniqueness
        qs = CustomUser.objects.filter(telegram_id=telegram_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Bu Telegram ID allaqachon ishlatilgan.")

        return telegram_id

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        has_password = self.instance.has_usable_password() if self.instance else False

        if new_password1 and has_password and not old_password:
            self.add_error("old_password", "Parolni o'zgartirish uchun eski parolni kiriting.")
        if new_password1 and new_password1 != new_password2:
            self.add_error("new_password2", "Yangi parollar mos kelmadi.")
        if has_password and old_password and not self.instance.check_password(old_password):
            self.add_error("old_password", "Eski parol noto'g'ri.")

        return cleaned_data


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["user", "total_price", "status", "address", "payment_method"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "total_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "payment_method": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    ("cash", "Naqd pul"),
                    ("card", "Karta"),
                ],
            ),
        }
