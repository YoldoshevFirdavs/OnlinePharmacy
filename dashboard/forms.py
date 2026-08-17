from django import forms

from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser, DeliveryDriver


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
            "is_prescription_required": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "main_image": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
        }


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False
    )

    class Meta:
        model = CustomUser
        fields = [
            "full_name",
            "email",
            "phone_number",
            "address",
            "avatar",
            "is_staff",
            "is_superuser",
            "is_active",
            "is_verified",
            "role",
            "password",
            "banned_for",
            "ban_reason",
            "ban_until",
            "is_permanent_ban",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            "banned_for": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masalan: admin_login, dashboard, etc."}),
            "ban_reason": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Ban berilgan sababi"}),
            "ban_until": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "is_permanent_ban": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password"]:
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class DeliveryDriverForm(forms.ModelForm):
    class Meta:
        model = DeliveryDriver
        fields = ["user", "phone_number", "vehicle_info", "status", "avatar"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_info": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }


# Admin va Deliverer uchun Account Settings formasi
class AccountSettingsForm(forms.ModelForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), required=False
    )

    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "phone_number", "address", "avatar"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 and not old_password:
            self.add_error(
                "old_password", "Parolni o'zgartirish uchun eski parolni kiriting."
            )
        if new_password1 and new_password1 != new_password2:
            self.add_error("new_password2", "Yangi parollar mos kelmadi.")
        if old_password and not self.instance.check_password(old_password):
            self.add_error("old_password", "Eski parol noto'g'ri.")

        return cleaned_data


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["user", "total_price", "status", "address"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "total_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
