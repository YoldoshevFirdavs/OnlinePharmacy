# OnlinePharmacy Xavfsizlik Tahlili (Security Review)

Ushbu hujjat OnlinePharmacy loyihasining xavfsizlik holatini tahlil qilish va topilgan zaifliklar hamda tavsiyalarni qayd etish uchun mo'ljallangan.

**Tahlil sanasi:** 2026-08-03

## Xulosa

Loyihada Django va Django REST Framework'ning standart xavfsizlik mexanizmlaridan unumli foydalanilgan. Xom SQL so'rovlari va `|safe` filtrining ishlatilmagani SQL Injection va XSS kabi keng tarqalgan hujumlardan yuqori darajada himoyalanganini ko'rsatadi. API endpoint'laridagi ruxsatlar bilan bog'liq dastlabki zaifliklar tuzatildi. Shunga qaramay, `production` muhiti uchun sozlamalarni yanada qattiqlashtirish va bog'liqliklarni (dependencies) yangilab turish tavsiya etiladi.

## 1. Sozlamalar va Konfiguratsiya (`config/settings.py`)

### 1.1. `SECRET_KEY` himoyasi
*   **Holat:** `SECRET_KEY` `.env` faylidan olinadi. Agar `.env` fayli yoki o'zgaruvchi mavjud bo'lmasa, standart, xavfsiz bo'lmagan kalit ishlatiladi.
*   **Risk:** **Yuqori.** Agar loyiha `DEBUG=False` rejimida, lekin `.env` faylisiz ishga tushirilsa, sessiyalar va boshqa imzolangan ma'lumotlar zaif kalit bilan himoyalanadi. Bu sessiyalarni o'g'irlash (session hijacking) hujumiga olib kelishi mumkin.
*   **Tavsiya:** `settings.py` da standart qiymatni olib tashlash va agar `SECRET_KEY` topilmasa, dasturni ishga tushmasdan xatolik berish (`raise ImproperlyConfigured`). Bu `production`da tasodifan zaif kalit bilan ishlashning oldini oladi.

### 1.2. `DEBUG` rejimi
*   **Holat:** `DEBUG` `.env` faylidan boshqariladi.
*   **Risk:** **O'rta.** Agar tasodifan `production`da `DEBUG=True` yoqilib qolsa, bu Django'ning batafsil xatolik sahifalari orqali tizim haqida muhim ma'lumotlar (sozlamalar, yo'llar, o'zgaruvchilar) sizib chiqishiga olib keladi.
*   **Tavsiya:** `production` muhitida `DEBUG` rejimini butunlay o'chirib qo'yishni ta'minlash uchun qo'shimcha tekshiruvlar qo'shish.

## 2. Kirish nuqtalari va ma'lumotlarni qayta ishlash

### 2.1. Fayl yuklash xavfsizligi
*   **Holat:** `users/serializers.py` dagi `UserSerializer` orqali avatar yuklashda faqat fayl kengaytmasi tekshirilardi.
*   **Risk:** **O'rta.** Tajovuzkor zararli skriptni `.jpg` kengaytmasi bilan nomlab, tizimni aldashga urinishi mumkin edi.
*   **Tuzatish (Qo'llanildi):** `users/serializers.py` fayliga `validate_image_file` nomli maxsus validator qo'shildi. Bu validator `Pillow` kutubxonasi yordamida faylning kontentini tekshirib, uning haqiqatan ham rasm ekanligini tasdiqlaydi.

### 2.2. API Endpoint Avtorizatsiyasi
*   **Holat:** Ba'zi `ViewSet`larda ruxsatlar (permissions) noto'g'ri yoki juda keng sozlangan edi.
*   **Risk:** **Yuqori.** Bu zaifliklar ma'lumotlarning sizib chiqishiga (barcha obunachilarning email manzillari) va ruxsatsiz o'zgartirishlarga (bir sotuvchining boshqasining profilini o'zgartirishi) olib kelishi mumkin edi.
*   **Tuzatish (Qo'llanildi):**
    *   **`SubscribedUserViewSet`:** `list`, `retrieve`, `destroy` amallari faqat adminlar (`IsAdminUser`) uchun cheklandi.
    *   **`SellerViewSet`:** `update` va `destroy` amallari uchun `IsOwnerOrAdmin` ruxsati qo'llanildi.
    *   **`UserProfileViewSet`:** Endi faqat tizimga kirgan foydalanuvchining o'zini tahrirlaydi.

## 3. In'ektsiya va skripting hujumlari

### 3.1. SQL Injection
*   **Holat:** Loyihada xom SQL so'rovlari (`.raw()`, `.extra()`) ishlatilmagan. Barcha so'rovlar Django ORM orqali amalga oshiriladi.
*   **Risk:** **Juda past.** ORM SQL Injection'dan ishonchli himoya qiladi.
*   **Tavsiya:** Yo'q. Joriy amaliyotni saqlab qolish kerak.

### 3.2. Cross-Site Scripting (XSS)
*   **Holat:** Andozalarda (`.html` fayllarda) `|safe` filtri ishlatilmagan. Django'ning standart auto-escaping mexanizmi faol.
*   **Risk:** **Past.** Foydalanuvchi kiritgan ma'lumotlar andozada ko'rsatilishidan oldin avtomatik zararsizlantiriladi.
*   **Tavsiya:** Yo'q. Joriy amaliyotni saqlab qolish kerak.

## 4. `security` ilovasining ichki tahlili

*   **`SafeErrorMiddleware`:**
    *   **Holat:** `DEBUG=False` rejimida barcha xatoliklarni ushlab, umumiy xabar qaytaradi.
    *   **Risk:** **Past.** Bu ma'lumot sizib chiqishining oldini oladi.
    *   **Tavsiya:** Xabar matnini "Login failed..." dan ko'ra umumiyroq, masalan, "So'rovni qayta ishlashda xatolik yuz berdi" ga o'zgartirish mumkin.

*   **`SecurityHeadersMiddleware`:**
    *   **Holat:** Muhim xavfsizlik sarlavhalarini (`HSTS`, `X-Content-Type-Options` va h.k.) javoblarga qo'shadi.
    *   **Risk:** **Yo'q.** Bu brauzer darajasidagi himoyani kuchaytiradi.
    *   **Tavsiya:** Yo'q.

*   **Brute-force himoyasi (`locks.py`):**
    *   **Holat:** Redis yordamida noto'g'ri urinishlarni sanaydi va akkauntlarni vaqtincha bloklaydi.
    *   **Risk:** **Past.** Mexanizm to'g'ri va ishonchli ko'rinadi.
    *   **Tavsiya:** Yo'q.

## 5. Bog'liqliklar (Dependencies) Xavfsizligi

*   **Versiyalarni qotirish:**
    *   **Holat:** `requirements.txt` faylida ba'zi kutubxonalarning versiyalari qotirib qo'yilmagan (masalan, `redis>=4.5.2`).
    *   **Risk:** **O'rta.** Bu `production` muhitida kutilmagan xatoliklarga yoki yangi zaifliklarga olib kelishi mumkin.
    *   **Tavsiya:** `pip freeze > requirements.txt` buyrug'i yordamida barcha kutubxonalarning aniq versiyalarini qotirib qo'yish.

*   **`python-telegram-bot==13.15`:**
    *   **Holat:** Bu versiya ancha eski.
    *   **Risk:** **Yuqori.** Eski versiyalarda ma'lum bo'lgan zaifliklar va xatoliklar bo'lishi mumkin.
    *   **Tavsiya:** Kutubxonani eng so'nggi stabil versiyaga yangilash va kodni moslashtirish. Bu katta o'zgarishlarni talab qilishi mumkin.

---

**Keyingi qadamlar:**
- `README.md` faylini kengaytirish.
