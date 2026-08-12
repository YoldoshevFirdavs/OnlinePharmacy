from django import forms

from orders.models import Order
from pharmacy.models import Category, Medicine
from users.models import CustomUser, Deliverer


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
            "is_active",
            "is_verified",
            "role",
            "password",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "role": forms.Select(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password"]:
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class DriverForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Ism",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )

    class Meta:
        model = Deliverer
        fields = ["phone_number", "vehicle_info", "status"]
        labels = {
            "phone_number": "Telefon",
            "vehicle_info": "Transport vositasi",
            "status": "Status",
        }
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-input"}),
            "vehicle_info": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            ("pending", "Kutilmoqda"),
            ("active", "Faol"),
            ("suspended", "To'xtatilgan"),
        ]
        if self.instance and self.instance.pk:
            self.fields["full_name"].initial = self.instance.user.full_name
        self.order_fields(["full_name", "phone_number", "vehicle_info", "status"])

    def save(self, commit=True):
        full_name = self.cleaned_data["full_name"]
        phone_number = self.cleaned_data["phone_number"]
        deliverer = super().save(commit=False)

        if self.instance.pk:
            user = deliverer.user
            user.full_name = full_name
            user.phone_number = phone_number
            if commit:
                user.save()
                deliverer.save()
        else:
            user = CustomUser.objects.create_user(
                phone_number=phone_number,
                full_name=full_name,
            )
            deliverer.user = user
            if commit:
                deliverer.save()
        return deliverer


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
