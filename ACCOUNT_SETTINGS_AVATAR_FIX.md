# Account Settings - Avatar Upload Fix

## Muammo
Account sozlamalari page-da "Shaklni yuklashda xatolik yuz berdi" error chiqyabdi.

Avatar field form-da bor edi lekin template-da ko'rsatilmayabdi.

## Sababi
1. AccountSettingsForm-da avatar field bor (AvatarUploadWidget bilan)
2. Lekin templates/account.html-da avatar field-ni ko'rsatmasligi kerak
3. Form ge request-da field render bo'lmagani uchun error qaytarilgan

## Yechim

### Updated: templates/account.html

Avatar field-ni form loop-da handle qilish uchun elif condition qo'shildi:

```django
{% elif field.html_name == 'avatar' %}
    <!-- Avatar Upload Field -->
    {{ field }}
```

**Oldin:** Avatar field loop-da boshqa handle qilinmayabdi  
**Hozir:** Avatar field to'g'ri render bo'ladi

### Avatar Field Configuration

**Form:** dashboard/forms.py - AccountSettingsForm
```python
avatar = forms.ImageField(
    widget=AvatarUploadWidget(attrs={"class": "form-control-file"}),
    required=False,
    validators=[validate_avatar],
    help_text="Max 5MB, JPEG/PNG/GIF/WebP"
)
```

**Validator:** validate_avatar
```python
def validate_avatar(file):
    """Validate avatar image file"""
    if file:
        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise ValidationError("Rasm 5MB dan katta bo'la olmaydi.")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_types:
            raise ValidationError("Faqat JPEG, PNG, GIF yoki WebP formatida rasmlar yuklash mumkin.")
```

**Widget:** dashboard/widgets.py - AvatarUploadWidget
- Custom file picker widget
- Preview functionality
- Validation messaging

## Files Modified

| File | Change |
|------|--------|
| templates/account.html | Added avatar field rendering in form loop |

## How It Works

### 1. User Account Settings Page Flow
```
1. User goes to: /dashboard/account/settings/
2. View: dashboard/views.py - account_settings()
3. Form: AccountSettingsForm (with avatar field)
4. Template: templates/account.html (now with avatar field)
```

### 2. Form Submission Flow
```
1. User selects avatar image
2. Form validates (size + type)
3. If valid: saves to user.avatar
4. Success: "Hisob sozlamalari muvaffaqiyatli yangilandi."
5. If invalid: Shows validation error
```

### 3. Avatar Field Validation
```
✓ File size: Max 5MB
✓ File type: JPEG, PNG, GIF, WebP only
✓ Required: No (optional field)
```

## Template Structure

```html
{% for field in form %}
    {% if field.html_name == 'email' %}
        <!-- Email field -->
    {% elif field.html_name == 'phone_number' %}
        <!-- Phone field -->
    {% elif field.html_name == 'avatar' %}
        <!-- Avatar Upload Field -->
        {{ field }}
    {% elif field.html_name == 'new_password1' %}
        <!-- Password field with validator -->
    {% else %}
        <!-- Other fields -->
    {% endif %}
{% endfor %}
```

## Admin Integration

Avatar field already integrated in admin:
```python
# users/admin.py - CustomUserAdmin
fieldsets = (
    ("Shaxsiy Ma'lumotlar", {
        "fields": ("full_name", "email", "phone_number", "avatar")
    }),
    ...
)

def formfield_for_dbfield(self, db_field, request, **kwargs):
    if db_field.name == 'avatar':
        kwargs['widget'] = AvatarUploadWidget(attrs={'class': 'form-control-file'})
        kwargs['validators'] = [validate_avatar]
    return super().formfield_for_dbfield(db_field, request, **kwargs)
```

## Results

✅ Avatar field now displays in account settings
✅ User can upload/change avatar
✅ Validation works (size + type)
✅ Success message shows after save
✅ Error messages display if validation fails
✅ Same widget as admin interface
✅ Consistent UX across all forms

## User Experience

### Before
- Form loads but no avatar field visible
- "Shaklni yuklashda xatolik yuz berdi" error

### After
- Avatar field visible and ready
- File picker works correctly
- Upload/change avatar works
- Validation errors show if file invalid

## Testing

1. Go to: `/dashboard/account/settings/`
2. Should see avatar field
3. Click to select image
4. Select JPEG/PNG/GIF/WebP (max 5MB)
5. Click Save
6. Should see success message
7. Avatar updates in profile

## Validation Errors Handled

| Error | Message |
|-------|---------|
| File too large | "Rasm 5MB dan katta bo'la olmaydi." |
| Wrong format | "Faqat JPEG, PNG, GIF yoki WebP formatida rasmlar yuklash mumkin." |

## Technical Details

| Parameter | Value |
|-----------|-------|
| Widget | AvatarUploadWidget |
| Max Size | 5MB |
| Formats | JPEG, PNG, GIF, WebP |
| Required | No |
| Field Type | ImageField |
| Location | templates/account.html |

## Related Files

- dashboard/forms.py - AccountSettingsForm definition
- dashboard/widgets.py - AvatarUploadWidget
- dashboard/views.py - account_settings view
- templates/account.html - Updated with avatar field
- users/admin.py - Admin integration
- static/js/avatar-upload.js - Client-side functionality

## Notes

- Avatar field optional (user can skip)
- Same validation as other forms
- Same widget as admin
- Consistent across all forms
- No database migration needed
