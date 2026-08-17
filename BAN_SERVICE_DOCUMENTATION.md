# Ban Service - O'zbek Tilida Dokumentatsiya

## Umumiy Ma'lumot

**Ban Service** - OnlinePharmacy loyihasida foydalanuvchilarning ban holatini boshqaruvchi xizmat. Vaqtli va doimiy banlarni qo'yish, olib tashlash, tekshirish va avtomatik ochishni ta'minlaydi.

---

## Arxitektura

### 1. **BanService** (`users/services.py`)
Ban qo'yish, olib tashlash, tekshirish va ma'lumotlarni boshqarish uchun asosiy sinfdir.

#### Asosiy Metodlar:

**`ban_user(user, duration_minutes=None, reason='', banned_for='', banned_by=None, is_permanent=False)`**
- Foydalanuvchini ban qilish
- Parametrlar:
  - `user`: CustomUser instance
  - `duration_minutes`: Vaqtli ban bo'lsa, minutlarda davomiyligi
  - `reason`: Ban sababi (o'zbek tilida)
  - `banned_for`: Ban o'rni (masalan: 'admin_dashboard', 'telegram_check')
  - `banned_by`: Ban qo'ygan admin user
  - `is_permanent`: Doimiy ban bo'lsa True

**Misol:**
```python
from users.services import BanService
from users.models import CustomUser

user = CustomUser.objects.get(id=1)
BanService.ban_user(
    user,
    duration_minutes=60,
    reason='Ko\'p marta noto\'g\'ri urinish',
    banned_for='admin_dashboard',
    banned_by=admin_user,
    is_permanent=False
)
```

---

**`unban_user(user, actor=None)`**
- Ban olib tashlash
- Parametrlar:
  - `user`: CustomUser instance
  - `actor`: Ban olib tasklayotgan admin (audit log uchun)

**Misol:**
```python
BanService.unban_user(user, actor=admin_user)
```

---

**`is_user_banned(user, for_page=None)`**
- Foydalanuvchi bannalangan yoki yo'qligini tekshirish
- Qaytaradi: `True` (banned) yoki `False` (not banned)
- Vaqtli banlar o'tib ketgan bo'lsa avtomatik ochadi

**Misol:**
```python
if BanService.is_user_banned(user, for_page='admin_dashboard'):
    # User banned
    pass
```

---

**`get_ban_info(user)`**
- Ban haqida to'liq ma'lumot qaytarish
- Qaytaradi: dict yoki None

**Ma'lumot tuzilishi:**
```python
{
    'is_banned': True,
    'banned_for': 'admin_dashboard',
    'ban_reason': 'Ko\'p marta noto\'g\'ri urinish',
    'ban_created_at': None,  # Agar model-da bo'lsa
    'ban_until': datetime,
    'is_permanent': False,
    'banned_by': 'admin_name'
}
```

---

**`record_blocked_event(user, path_attempted, reason, banned_for=None)`**
- Bloklangan event-ni log qilish (audit uchun)

---

**`increment_failed_attempts(user, field='failed_telegram_attempts', limit=None, ban_page='telegram_check', ban_duration_minutes=60)`**
- Noto'g'ri urinishlarni hisoblash
- Limitga yetganda avtomatik ban qo'yish

---

### 2. **BanCheckMiddleware** (`config/middleware.py`)
Har request-da ban holatini tekshiruvchi middleware.

#### Ishlashi:
1. Authenticated user-ni tekshirish
2. Agar banned bo'lsa → `/security/not-allowed/?next=<path>` ga redirect
3. Agar admin roli yo'q bo'lsa admin URL-ga kirsa → not_allowed-ga redirect (ban bermaydi)

---

### 3. **not_allowed View** (`dashboard/views.py`)
Ban/bloklangan foydalanuvchilar uchun error sahifasi.

#### Context Ma'lumotlari:
- `ban_info`: Ban tafsilotlari (dict)
- `path_attempted`: Qaysi URL-ga kirdi
- `user`: Joriy foydalanuvchi

---

### 4. **not_allowed Template** (`templates/dashboard/not_allowed.html`)
O'zbek tilida, responsive design, countdown timer, admin uchun Unban tugmasi.

#### Elementlar:
- **Sarlavha:** "Kirish taqiqlangan"
- **Ikona:** Ban symbol (fa-ban)
- **Ban tafsilotlari:** Sabab, o'rni, turi, tugash vaqti
- **Countdown Timer:** Vaqtli banlar uchun qolgan vaqtni ko'rsatadi
- **Tugmalar:**
  - "Bosh sahifaga" - hammaga
  - "Unban qilish" - faqat admin-ga
- **Responsive Design:** Mobile va desktop

---

### 5. **Management Command** (`users/management/commands/unban_expired.py`)
Vaqtli banlarni avtomatik ochish uchun.

#### Ishlashi:
Har daqiqada cron yoki scheduler orqali ishga tushadigan command. Ban vaqti tugagan (`ban_until <= now`) foydalanuvchilarni topib unbanning qiladi.

#### Ishga tushirish:
```bash
# Dry run (hech nima o'zgartirmaydi)
python manage.py unban_expired --dry-run

# Haqiqiy ishga tushirish
python manage.py unban_expired
```

#### Cron Setup (optional):
```bash
# Har daqiqada ishga tushish
* * * * * cd /path/to/project && python manage.py unban_expired
```

---

### 6. **Serializer Integratsiyasi** (`users/serializers.py`)
CustomUserSerializer-ga ban maydonlari qo'shildi:
- `is_banned`
- `banned_for`
- `ban_reason`
- `ban_until`
- `is_permanent_ban`

Admin panel orqali bu maydonlarni ko'rish va tahrirish mumkin.

---

## Ban Modeli

### CustomUser Modelidagi Ban Maydonlari:

```python
is_banned = BooleanField(default=False)  # Legacy (Telegram login uchun)

banned_for = CharField(...)  # Qaysi page uchun ban
ban_reason = CharField(...)  # Ban sababi
ban_until = DateTimeField(..., null=True)  # Vaqtli ban tugash vaqti
is_permanent_ban = BooleanField(...)  # Doimiy ban yoki yo'q
banned_by = ForeignKey(...)  # Ban qo'ygan admin
```

---

## Workflow

### Ban Qo'yish Oqimi:

```
1. Event yuz beradi (masalan: ko'p noto'g'ri urinish)
   ↓
2. BanService.ban_user() chaqiriladi
   ↓
3. User.banned_for = 'page_name' (saqlandi)
   ↓
4. User.ban_until = now + duration (vaqtli bo'lsa)
   ↓
5. Audit log yoziladi
   ↓
6. Next request-da Middleware tekshiradi
   ↓
7. Ban_check_middleware → /security/not-allowed/ redirect
```

### Ban Olib Tashlash Oqimi:

```
1. Admin "Unban qilish" tugmasini bosadi
   ↓
2. BanService.unban_user(user, actor=admin) chaqiriladi
   ↓
3. User.banned_for = None (o'chiriladi)
   ↓
4. User.ban_until = None
   ↓
5. Audit log yoziladi
   ↓
6. User endi kirishlari mumkin
```

### Avtomatik Unban Oqimi:

```
1. Cron job → management command ishga tushadi
   ↓
2. ban_until <= now bo'lgan users topiladi
   ↓
3. Har bir user uchun unban_user() chaqiriladi
   ↓
4. Audit log yoziladi
   ↓
5. Next login-da user kirishlari mumkin
```

---

## Ishlash Misollar

### Misol 1: Admin dashboard-da ko'p noto'g'ri urinish bo'lsa, admin-ni ban qilish

```python
from users.models import CustomUser
from users.services import BanService

user = CustomUser.objects.get(email='admin@example.com')

# 5 ta noto'g'ri urinishdan keyin ban qilish
BanService.ban_user(
    user,
    duration_minutes=60,  # 1 soat
    reason='Admin dashboard-da 5 ta noto\'g\'ri parol urinishi',
    banned_for='admin_dashboard',
    banned_by=system_admin,
    is_permanent=False
)
```

### Misol 2: Telegram login-da ko'p urinish bo'lsa, ban qilish

```python
result = BanService.increment_failed_attempts(
    user,
    field='failed_telegram_attempts',
    limit=5,  # 5 ta urinish
    ban_page='telegram_check',
    ban_duration_minutes=60
)

if result['banned']:
    print(f"User banned: {result['attempts']}/{result['limit']}")
```

### Misol 3: Admin boshqa user-ni unban qilish

```python
admin = CustomUser.objects.filter(is_staff=True).first()
user_to_unban = CustomUser.objects.get(email='user@example.com')

BanService.unban_user(user_to_unban, actor=admin)
print(f"User {user_to_unban.email} unbanned by {admin.email}")
```

---

## Testing

### Manual Testing:

```bash
# Docker-da shell ochish
docker exec onlinepharmacy-web-1 python manage.py shell

# Test qilish
from users.models import CustomUser
from users.services import BanService

user = CustomUser.objects.first()

# Ban qilish
BanService.ban_user(user, duration_minutes=30, reason='Test', banned_for='test')

# Tekshirish
print(BanService.is_user_banned(user))  # True

# Ban info
print(BanService.get_ban_info(user))

# Unban qilish
BanService.unban_user(user)
print(BanService.is_user_banned(user))  # False
```

### HTTP Test:

```bash
# Not_allowed sahifasini test qilish
curl http://localhost/security/not-allowed/?next=/test

# Ban status tekshirish
curl http://localhost/api/users/1/ | grep banned_for
```

---

## Konfiguratsiya

### Settings-da Ban Sozlamalari:

```python
# config/settings.py

# Admin login ban sozlamalari
ADMIN_LOGIN_MAX_ATTEMPTS = 7  # 7 ta noto'g'ri urinish = ban
ADMIN_BAN_SECONDS = 3600  # 1 soat ban

# Ban Service sozlamalari (optional)
BAN_DEFAULT_DURATION_MINUTES = 60
BAN_TELEGRAM_LIMIT = 5
BAN_TELEGRAM_DURATION_MINUTES = 60
```

---

## Xatolar va Yechimlar

### Xatolik: "User model no field 'failed_telegram_attempts'"
**Sababi:** Model-da bu field yo'q  
**Yechimi:** BanService.ban_user() to'g'ri dan foydalaning, increment_failed_attempts() sharoitli

### Xatolik: "User still banned after unban"
**Sababi:** ban_until vaqti hali tugamagan  
**Yechimi:** management command chaladirib, yoki manually unban_user() chaqiring

---

## Audit Logging

Barcha ban/unban actions logging-ga yoziladi:

```
[BAN] User 2 (user@example.com) banned by admin@example.com for 'admin_dashboard' - Reason: 5 noto'g'ri parol - Duration: 60min

[UNBAN] User 2 (user@example.com) unbanned by admin@example.com (was banned for 'admin_dashboard')

[BLOCKED] User 5 (user@example.com) tried to access /dashboard/admin/ - Reason: Admin roli yo'q - Banned for: admin_dashboard
```

---

## Middleware Order

Settings.py-da middleware order muhim:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config.middleware.BanCheckMiddleware',  # Auth-dan KEYIN
    'config.middleware.CustomErrorMiddleware',
]
```

---

## Xulosa

Ban Service loyihaning asosiy qismlari:
1. ✅ BanService - asosiy logika
2. ✅ BanCheckMiddleware - request tekshiruvi
3. ✅ not_allowed view va template - UX
4. ✅ Management command - avtomatik ochish
5. ✅ Serializer - API integratsiyasi
6. ✅ Audit logging - tuzilishi

**Hamma narsasi to'liq va ishga tushdi!**

---

## Kontakt

Savollar bo'lsa, `users/services.py` va `config/middleware.py` fayllarini ko'rib chiqing.
