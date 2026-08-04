# OnlinePharmacy - To'liq funksiyali elektron dorixona platformasi

Ushbu loyiha Django, Django REST Framework, PostgreSQL va Docker kabi zamonaviy texnologiyalar asosida qurilgan to'liq funksiyali elektron tijorat platformasidir. Tizim foydalanuvchilarni ro'yxatdan o'tkazish, mahsulotlar katalogini boshqarish, savatcha, buyurtmalar va to'lovlarni amalga oshirish imkoniyatlarini o'z ichiga oladi.

Platforma bir nechta foydalanuvchi rollarini (Mijoz, Sotuvchi, Yetkazib beruvchi, Admin) qo'llab-quvvatlaydi va har bir rol uchun maxsus funksionallikni taqdim etadi.

## Asosiy xususiyatlar

- **Ko'p rolli arxitektura:**
  - **Mijoz:** Mahsulotlarni ko'rish, qidirish, savatchaga qo'shish va buyurtma berish.
  - **Sotuvchi:** O'z mahsulotlarini boshqarish, buyurtmalarni ko'rish va statistikasini tahlil qilish.
  - **Yetkazib beruvchi (Deliverer):** O'ziga tayinlangan buyurtmalarni ko'rish, statusini yangilash va yetkazib berish jarayonini boshqarish.
  - **Admin:** Barcha tizimni to'liq boshqarish, foydalanuvchilar, mahsulotlar, buyurtmalar va faoliyat tarixini kuzatish.
- **Xavfsiz autentifikatsiya:**
  - JWT (JSON Web Tokens) orqali API xavfsizligi.
  - Email yoki Telegram orqali bir martalik parol (OTP) yuborish orqali parolsiz tizimga kirish.
- **Tahliliy Boshqaruv Paneli (Dashboard):**
  - Sotuvlar, foydalanuvchilar, mahsulotlar va buyurtmalar bo'yicha real vaqtda yangilanadigan statistik ma'lumotlar.
  - Interaktiv grafiklar va jadvallar.
- **Asinxron vazifalar:**
  - `Celery` va `Redis` yordamida email xabarlari va boshqa resurs talab qiladigan vazifalarni fonga o'tkazish.
- **Kesh mexanizmi:**
  - `Redis` yordamida tez-tez so'raladigan ma'lumotlarni (masalan, mahsulotlar ro'yxati) keshda saqlash orqali tizim tezligini oshirish.
- **To'liq Docker bilan integratsiya:**
  - `docker-compose` yordamida bir buyruq bilan butun loyihani (web-server, ma'lumotlar bazasi, Redis, Celery) ishga tushirish.
- **Production'ga tayyor (Production-Ready):**
  - `Nginx` (reverse proxy va statik fayllar uchun) va `Gunicorn` (WSGI server) bilan production muhitida ishlash uchun to'liq sozlangan.

## Texnologiyalar stekasi

- **Backend**: Django 5.1, Django REST Framework
- **Ma'lumotlar bazasi**: PostgreSQL 15
- **Kesh va Xabar navbati (Broker)**: Redis 7
- **Fon vazifalari**: Celery
- **API Hujjatlari**: drf-yasg (Swagger/OpenAPI)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Dashboard uchun)
- **Deployment**: Docker, Nginx, Gunicorn

## Loyiha tuzilishi

Loyiha modullarga ajratilgan arxitekturaga asoslangan bo'lib, har bir ilova o'zining aniq vazifasini bajaradi:

```
online-pharmacy/
├── config/              # Django loyihasining asosiy sozlamalari, URL'lar va ASGI/WSGI.
├── dashboard/           # Admin paneli uchun frontend va backend logikasi.
├── orders/              # Buyurtmalar, savatcha va ular bilan bog'liq amallar.
├── pharmacy/            # Mahsulotlar, kategoriyalar, sharhlar va boshqa farmatsevtika logikasi.
├── security/            # Xavfsizlikka oid modullar (AuditLog, middleware, ruxsatlar).
├── static/              # Global statik fayllar (CSS, JS, rasm).
├── templates/           # Global HTML andozalar.
├── telegram_bot/        # Telegram bot logikasi va webhook'lar.
├── users/               # Foydalanuvchilar, autentifikatsiya, OTP va profillar.
├── docker-compose.yml   # Development muhiti uchun Docker Compose fayli.
├── Dockerfile           # Asosiy Django ilovasi uchun Dockerfile.
├── requirements.txt     # Python kutubxonalari ro'yxati.
└── manage.py            # Django boshqaruv skripti.
```

## Tezkor ishga tushirish (Development)

1.  **Repozitoriyni kompyuterga yuklab oling:**
    ```bash
    git clone https://github.com/yourusername/online-pharmacy.git
    cd online-pharmacy
    ```

2.  **`.env` faylini yarating:**
    `.env.example` faylidan nusxa oling va ichidagi o'zgaruvchilarni o'zingizning sozlamalaringiz bilan to'ldiring. Bu faylda maxfiy kalitlar, ma'lumotlar bazasi parollari va boshqa muhim sozlamalar saqlanadi.
    ```bash
    cp .env.example .env
    ```

3.  **Docker konteynerlarini ishga tushiring:**
    Bu buyruq `Dockerfile` va `docker-compose.yml` fayllari asosida kerakli `image`larni quradi va barcha servislarni (web, db, redis, celery) ishga tushiradi.
    ```bash
    docker-compose up -d --build
    ```

4.  **Ma'lumotlar bazasi migratsiyalarini bajaring:**
    Bu buyruq `web` konteyneri ichida `manage.py migrate` buyrug'ini ishga tushirib, ma'lumotlar bazasi jadvallarini yaratadi.
    ```bash
    docker-compose exec web python manage.py migrate
    ```

5.  **Superfoydalanuvchi yarating:**
    Admin paneliga kirish uchun superuser yarating.
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

6.  **Sayt va API'ga kiring:**
    -   **Asosiy sayt:** `http://localhost:8000`
    -   **Admin paneli:** `http://localhost:8000/admin/`
    -   **API hujjatlari (Swagger):** `http://localhost:8000/api/v1/swagger/`

## Xavfsizlik (Security)

Loyihada zamonaviy veb-ilovalar uchun zarur bo'lgan ko'plab xavfsizlik choralari ko'rilgan va tahlil qilingan:

- **SQL Injection:** Barcha ma'lumotlar bazasi so'rovlari Django ORM orqali amalga oshiriladi. Bu parametrlarni avtomatik ravishda zararsizlantirib, SQL in'ektsiya hujumlaridan yuqori darajada himoya qiladi. Loyihada xom SQL so'rovlari (`.raw()`, `.extra()`) ishlatilmagan.

- **Cross-Site Scripting (XSS):** Django'ning standart andoza tizimi (`auto-escaping`) barcha o'zgaruvchilarni HTML'ga chiqarishdan oldin avtomatik ravishda zararsizlantiradi. `|safe` filtri ishlatilmaganligi sababli, foydalanuvchi kiritgan zararli skriptlarning ishga tushib ketish xavfi minimal darajada.

- **CSRF (Cross-Site Request Forgery):** Django'ning standart `CsrfViewMiddleware` himoyasi barcha `POST`, `PUT`, `DELETE` so'rovlari uchun yoqilgan. Bu so'rovlarning faqat sizning saytingizdan kelganiga ishonch hosil qiladi.

- **Fayl yuklash xavfsizligi:** Foydalanuvchi tomonidan yuklanadigan avatar fayllari `Pillow` kutubxonasi yordamida haqiqiy rasm ekanligi tekshiriladi. Bu faqat fayl kengaytmasiga emas, balki uning ichki tarkibiga asoslanadi va zararli skriptlarni rasm niqobi ostida yuklash xavfini kamaytiradi.

- **Ruxsatlar (Permissions):** API endpoint'lar `IsAuthenticated`, `IsAdminUser`, `IsOwnerOrAdmin` kabi qat'iy ruxsatlar bilan himoyalangan. Bu har bir foydalanuvchi faqat o'ziga tegishli ma'lumotlarni ko'ra olishi va o'zgartira olishini ta'minlaydi. Masalan, obunachilar ro'yxati faqat adminlarga ko'rinadi.

- **Parol xavfsizligi:** Parollar standart `PBKDF2` algoritmi yordamida xeshlangan holda saqlanadi. `AUTH_PASSWORD_VALIDATORS` orqali parollarning murakkabligi (uzunligi, sonlar, belgilar ishtiroki) tekshiriladi.

- **Brute-Force himoyasi:** Noto'g'ri autentifikatsiya urinishlari Redis yordamida sanaladi. Ma'lum bir chegaradan oshganda (masalan, 10 daqiqada 5 ta xato), foydalanuvchi akkaunti vaqtincha bloklanadi.

- **Xavfsizlik sarlavhalari (Security Headers):** Har bir HTTP javobga `Strict-Transport-Security` (HSTS), `X-Content-Type-Options`, `X-Frame-Options` kabi qo'shimcha xavfsizlik sarlavhalari qo'shiladi. Bu "clickjacking" va "MIME-sniffing" kabi brauzerga oid hujumlardan himoya qiladi.

## Testlash

Loyiha uchun yozilgan testlarni ishga tushirish:
```bash
# Barcha ilovalar uchun testlarni ishga tushirish
docker-compose exec web python manage.py test

# Faqat 'users' ilovasi uchun testlarni ishga tushirish
docker-compose exec web python manage.py test users
```

## Muhit o'zgaruvchilari (`.env` fayli)

Loyiha sozlamalari uchun `.env` faylida quyidagi o'zgaruvchilarni o'rnatish kerak:

```env
# Django sozlamalari
SECRET_KEY=your-super-secret-key-for-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost

# Ma'lumotlar bazasi (PostgreSQL)
DB_NAME=pharmacy_db
DB_USER=pharmacy_admin
DB_PASSWORD=your-strong-database-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Email (Gmail uchun misol)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password

# JWT
JWT_SECRET=another-super-secret-key-for-jwt

# CORS
CORS_ALLOWED_ORIGINS=https://yourfrontenddomain.com,http://localhost:3000
```

---
**Oxirgi yangilanish**: 2026-08-03
