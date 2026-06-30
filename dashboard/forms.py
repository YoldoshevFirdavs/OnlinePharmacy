from django import forms
from users.models import CustomUser, Deliverer
from pharmacy.models import Category, Medicine
from orders.models import Order

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'is_default', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
        }

class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'name', 'slug', 'category', 'price', 'stock', 'is_active', 'seller',
            'short_description', 'instruction', 'side_effects', 'contraindications',
            'storage_conditions', 'is_prescription_required', 'main_image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'seller': forms.Select(attrs={'class': 'form-control'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'instruction': forms.Textarea(attrs={'class': 'form-control'}),
            'side_effects': forms.Textarea(attrs={'class': 'form-control'}),
            'contraindications': forms.Textarea(attrs={'class': 'form-control'}),
            'storage_conditions': forms.TextInput(attrs={'class': 'form-control'}),
            'is_prescription_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'main_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'phone_number', 'address', 'is_staff', 'is_active', 'is_verified', 'role', 'password']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

# Admin va Deliverer uchun Account Settings formasi
class AccountSettingsForm(forms.ModelForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'phone_number', 'address', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and not old_password:
            self.add_error('old_password', "Parolni o'zgartirish uchun eski parolni kiriting.")
        if new_password1 and new_password1 != new_password2:
            self.add_error('new_password2', "Yangi parollar mos kelmadi.")
        if old_password and not self.instance.check_password(old_password):
            self.add_error('old_password', "Eski parol noto'g'ri.")
        
        return cleaned_data

# Deliverer uchun Order statusini yangilash formasi
class DelivererOrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }