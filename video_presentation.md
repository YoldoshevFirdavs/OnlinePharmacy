# OnlinePharmacy — Video Presentation Script

**Loyiha nomi:** OnlinePharmacy
**Muallif:** Firdavs Yo'ldashev
**Davomiyligi:** ~15 minut
**Til:** O'zbek tili

---

## 1. Kirish (1–1.5 minut)

Assalomu alayikum, hurmatli ustozlar va do'stlar! Men Firdavs Yo'ldashev — bugun sizlarga o'zimning birinchi kurs loyiyam bo'lgan **OnlinePharmacy** platformasini taqdim etmoqchiman.

**OnlinePharmacy** — bu to'liq ishlaydigan onlayn dorixona veb-platformasi. Bu loyihada mijozlar dorilarni ko'rishi, savatchaga qo'shishi, buyurtma berishi va to'lov qilishi mumkin. Shuningdek, admin va sotuvchilar uchun maxsus boshqaruv paneli mavjud.

Loyihani yaratishda **Django 5.1**, **PostgreSQL**, **Celery**, **Redis**, **Docker** va boshqa zamonaviy texnologiyalardan foydalandim. Frontend qismi uchun **HTML**, **CSS3** va **JavaScript** ishlatilgan — hech qanday React yoki boshqa framework ishlatilmagan, barcha interfeys sof Django Templates va vanilla JavaScript bilan qurilgan.

Bugungi prezentatsiyada men:

- Loyiha g'oyasi va maqsadini
- Ishlatilgan texnologiyalarni
- Asosiy funksionallarni
- Deploy jarayoni va infratuzilmani
- Xavfsizlik yechimlarini
- Yakuniy xulosa va maslahatlarni

aytib beraman. Boshlaylik!

---

## 2. Loyiha G'oyasi (1.5–2 minut)

**OnlinePharmacy** — bu dorixona platformasi bo'lib, dori-darmonlarni onlayn sotish jarayonini to'liq raqamlashtiradi. Loyiha monolitik **Django** ilovasi sifatida qurilgan va bitta repozitoriyada barcha funksiyalarni o'z ichiga oladi.

Loyihaning asosiy maqsadi — real dorixona uchun ishlaydigan platforma yaratish. Bunda quyidagi rollar bor:

- **Mijozlar** — dorilarni ko'rish, savatchaga qo'shish, buyurtma berish
- **Adminlar** — barcha jarayonlarni boshqarish, foydalanuvchilarni nazorat qilish
- **Sotuvchilar** — mahsulotlarni boshqarish
- **Yetkazib beruvchilar** — buyurtmalarni yetkazib berish

Platformada **REST API** ham mavjud — bu kelajakda mobil ilova qo'shish imkoniyatini beradi. API **Django REST Framework** yordamida qurilgan va **Swagger** orqali hujjatlashtirilgan.

Loyiha tili **o'zbek** (uz-uz) qilib sozlangan, vaqt zonasi **Asia/Tashkent** ishlatilgan — ya'ni to'liq O'zbekiston bozoriga mo'ljallangan.

---

## 3. Texnologiyalar (2–2.5 minut)

Keling, loyihada ishlatilgan texnologiyalarni batafsil ko'rib chiqaylik. Barcha ma'lumotlar haqiqiy — `requirements.txt` va `settings.py` fayllaridan olingan.

### Backend

- **Django 5.1.1** — asosiy Python web framework. Loyihamizning yadrosini tashkil etadi
- **Django REST Framework 3.15.2** — REST API qurish uchun. Barcha API endpointlar shu kutubxona orqali ishlaydi
- **PostgreSQL 15** — ma'lumotlar bazasi. Docker orqali ishga tushuriladi
- **Celery 5.3.1 + Redis 7** — fon vazifalari uchun. Email yuborish, OTP kodlarini boshqarish kabi vazifalar Celery orqali asinxron bajariladi
- **Gunicorn** — production WSGI server. Django ilovasini ishlab chiqarish muhitida ishga tushiradi

### Autentifikatsiya va Xavfsizlik

- **SimpleJWT 5.5.1** — JWT token asosida xavfsiz autentifikatsiya
- **Djoser** — foydalanuvchilar ro'yxatdan o'tishi va boshqaruvi uchun
- **django-ratelimit** — API so'rovlarni cheklash, DDoS hujumlardan himoya
- **django-cors-headers** — CORS boshqaruvi

### Frontend

- **Django Templates** — HTML shablonlar tizimi
- **Vanilla CSS3** — 18 ta CSS fayl: `main.css`, `shop.css`, `auth.css`, `cart.css`, `products.css`, `account.css` va boshqalar
- **Vanilla JavaScript** — 30 dan ortiq JS fayl: `auth.js`, `cart.js`, `shop.js`, `order.js`, `header.js` va boshqalar
- **Font Awesome** — ikonkalar uchun

Bu yerda e'tibor bering: biz hech qanday **React**, **Vue** yoki boshqa frontend framework ishlatmadik. Barcha interfeys sof **HTML**, **CSS** va **JavaScript** bilan qurilgan.

### DevOps va Monitoring

- **Docker va Docker Compose** — konteynerlashtirish
- **Nginx** — reverse proxy va statik fayllar uchun
- **GitHub Actions** — CI/CD pipeline (flake8, isort, black, pytest)
- **Prometheus + Grafana** — performance monitoring
- **Bugsink** — xatolarni kuzatish
- **WhiteNoise** — statik fayllarni production'da xizmat qilish

### Kod Sifati

- **Black** — kod formatlash (line-length=120)
- **isort** — importlarni tartiblash
- **Flake8** — linting va kod sifati tekshiruvi
- **pytest + pytest-django** — avtomatik testlash
- **coverage** — test coverage o'lchash
- **pre-commit** — commit oldidan avtomatik tekshiruvlar

---

## 4. Loyiha Arxitekturasi (1.5–2 minut)

Loyiha **8 ta Django app**dan tashkil topgan. Har birining o'z vazifasi bor:

| Django App | Vazifasi |
|---|---|
| **config/** | Loyiha sozlamalari, URL routing, middleware, Celery config |
| **users/** | Foydalanuvchi modeli, profil, autentifikatsiya, OTP, rollar |
| **pharmacy/** | Dorilar, kategoriyalar, mahsulot metadata, tarix |
| **orders/** | Buyurtma yaratish, savat, buyurtma holati |
| **dashboard/** | Admin va foydalanuvchi dashboard, statistika, boshqaruv |
| **security/** | Audit loglar, ban tizimi, device fingerprint, IP bloklash |
| **payments/** | Stripe to'lov integratsiyasi |
| **telegram_bot/** | Telegram bot orqali OTP autentifikatsiya |

Shuningdek, loyihada quyidagi sahifalar mavjud:

- **Bosh sahifa** (`main.html`) — asosiy landing page
- **Do'kon** (`shop.html`) — dorilar katalogi, qidiruv va filtr
- **Savatcha** (`cart.html`) — tanlangan mahsulotlar
- **Buyurtma** (`order.html`) — buyurtma berish
- **Hisob** (`account.html`) — foydalanuvchi profili
- **Kontakt**, **Maxfiylik siyosati**, **Foydalanish shartlari** sahifalari
- **Dashboard** — admin panel (20 dan ortiq sub-sahifa)

---

## 5. Funksionallar va Xususiyatlar (3–3.5 minut)

### Foydalanuvchi Autentifikatsiyasi

- Ro'yxatdan o'tish va tizimga kirish — **JWT token** bilan
- **Telegram OTP** — SMS o'rniga Telegram bot orqali 4 xonali tasdiqlash kodi yuboriladi. Bu `telegram_bot/runbot1.py` orqali ishlaydi va Docker'da alohida konteyner sifatida ishlaydi
- **Email tasdiqlash** — parol tiklash va hisobni tasdiqlash uchun
- **Admin deeplink autentifikatsiya** — maxsus admin kirish tizimi
- **Social auth** integratsiyasi — `social-auth-app-django` kutubxonasi orqali

### Dorilar Katalogi

- Kategoriyalar bo'yicha dorilarni ko'rish
- Qidiruv va filtrlash — `django-filter` kutubxonasi yordamida
- Mahsulot tafsilotlari sahifasi — to'liq qo'llanma (`product_full_guide.html`) bilan
- Mahsulotga izoh qoldirish tizimi (`product_comments.html`)
- Ko'rilgan dorilar tarixi — `UserHistoryViewSet` orqali

### Buyurtma Tizimi

- Savatchaga qo'shish va olib tashlash — `CartAddAPIView` API orqali
- Buyurtma yaratish — `CheckoutAPIView` orqali
- Buyurtma holati kuzatuvi
- Buyurtma tarixi

### To'lov Tizimi

- **Stripe** orqali onlayn to'lov — `stripe` kutubxonasi
- Stripe kalit va ommaviy kalitlar `.env` faylda saqlanadi
- To'lov holati monitoring

### Admin Dashboard

Admin panelda quyidagi imkoniyatlar mavjud:

- **Statistika** — daromad, buyurtmalar soni, faol foydalanuvchilar
- **Dorilarni boshqarish** — qo'shish, tahrirlash, o'chirish
- **Kategoriyalar boshqarish**
- **Foydalanuvchilar ro'yxati** va rollarni o'zgartirish
- **Buyurtmalarni nazorat qilish** va holat o'zgartirish
- **Yetkazib beruvchilarni boshqarish**
- **Audit log** — barcha harakatlarni ko'rish
- **Undo operatsiyalari** — o'chirilgan ma'lumotlarni qaytarish (`UndoLog`)
- **Ban tizimi** — foydalanuvchilarni bloklash

### Email Bildirishnomalar

- Buyurtma yaratilganda email yuborish
- To'lov tasdiqlanishi
- Parol tiklash linki
- **Celery** orqali asinxron yuboriladi — sahifa tezligiga ta'sir qilmaydi
- `django-templated-mail` kutubxonasi — chiroyli HTML email shablonlari

### Google AI Integratsiya

- **google-genai** kutubxonasi orqali Google AI Studio SDK integratsiyasi
- `.env` faylda `GOOGLE_AI_API_KEY` orqali sozlanadi

---

## 6. Xavfsizlik (1.5–2 minut)

Loyihada xavfsizlikka juda katta e'tibor berilgan:

### Autentifikatsiya Xavfsizligi

- **JWT tokenlar** — access token 30 daqiqa, refresh token 7 kun amal qiladi
- Token **rotation** — har safar yangi access token olganda refresh token yangilanadi
- **Blacklisting** — eski tokenlar o'chiriladi

### API Himoyasi

- **Rate Limiting** — anonim foydalanuvchilar uchun **20 so'rov/minut**, ro'yxatdan o'tganlar uchun **300 so'rov/minut**
- **CORS** — faqat ruxsat berilgan domenlardan so'rovlar qabul qilinadi
- **CSRF** himoyasi — barcha state-o'zgartiruvchi so'rovlar uchun

### Device Fingerprint Tizimi

Bu loyihaning noyob xususiyati — qurilma barmoq izi tizimi:

- Har bir qurilmani aniqlash va kuzatish
- **Rate threshold** — har bir qurilmadan sekundiga 10 ta so'rov cheklovi
- **Avtomatik ban** — limitdan oshganda 60 daqiqalik vaqtincha bloklash
- **IP bloklash** — 1 soatga IP manzilni bloklash
- **Sahifa yangilash limiti** — soatiga 20 marta
- Cookie xavfsizligi — `SameSite=Strict`, HTTPS cookie

### Audit Logging

- **Security** appda barcha muhim harakatlar qayd etiladi
- Log fayllarda maxfiy ma'lumotlar (OTP, parol, token) avtomatik maskirovka qilinadi — `SensitiveDataFilter`
- **RotatingFileHandler** — log fayllar 10 MB dan oshganda yangi fayl yaratiladi, 10 ta backup saqlanadi

### Production Xavfsizlik

- **HSTS** — 1 yil muddat bilan HTTPS majburlash
- **Secure cookies** — `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_SECURE=True`
- Admin login — maksimum **10 ta muvaffaqiyatsiz urinish**, keyin **1 soat ban**

---

## 7. Deploy Jarayoni va Infrastructure (2–2.5 minut)

### Lokal Ishga Tushirish

Loyihani lokal ishga tushirish juda oson — bitta buyruq:

```bash
docker compose up -d --build
```

Bu buyruq quyidagi servislarni ishga tushiradi:

| Servis | Vazifasi |
|---|---|
| **db** | PostgreSQL 15 — ma'lumotlar bazasi |
| **redis** | Redis 7 Alpine — kesh va Celery broker |
| **web** | Django + Gunicorn — asosiy ilova |
| **celery** | Celery worker — fon vazifalari |
| **auth_bot** | Telegram OTP bot |
| **prometheus** | Metrikalar yig'ish |
| **grafana** | Monitoring dashboardlar |

Keyin migratsiya va statik fayllarni yig'ish:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

### Production Deploy (AWS EC2)

Production muhitda loyiha **AWS EC2** serverida joylashtirilgan:

- **EC2 instance** — Linux server
- **Docker Compose** — `docker-compose.prod.yml` orqali
- **Gunicorn** — 3 ta worker, 60 soniya timeout, `max-requests=1000`
- **Nginx** — reverse proxy sifatida, SSL sertifikat bilan
- **Host path volumes** — statik va media fayllar to'g'ridan-to'g'ri EC2 hostda saqlanadi
- **entrypoint.sh** — avtomatik migratsiya va server ishga tushirish

### CI/CD Pipeline (GitHub Actions)

Har bir `push` va `pull_request`da avtomatik ravishda:

1. **Flake8** — sintaksis va stil xatolarini tekshirish
2. **isort** — importlar tartibini tekshirish
3. **Black** — kod formatlash tekshiruvi
4. **pytest** — barcha testlarni ishga tushirish

CI pipeline PostgreSQL va Redis servislarini GitHub Actions ichida ishga tushiradi va real ma'lumotlar bazasi bilan testlarni bajaradi.

### Monitoring Stack

- **Prometheus** — `/metrics/` endpointdan har 15 sekundda metrikalar yig'adi
- **Grafana** — vizualizatsiya va ogohlantirish dashboardlari (port 3000)
- **Bugsink** — xatolarni kuzatish va tizim salomatligi (port 8010)

---

## 8. Yakuniy Xulosa (1–1.5 minut)

**OnlinePharmacy** loyiyasi zamonaviy texnologiyalar bilan qurilgan to'liq ishlaydigan veb-platformadir. Xulosa qilib aytganda:

- ✅ **Django 5.1 + DRF** bilan kuchli backend yaratildi
- ✅ **HTML, CSS, JavaScript** bilan foydalanuvchiga qulay interfeys qurildi
- ✅ **JWT + Telegram OTP** bilan xavfsiz autentifikatsiya tizimi
- ✅ **Stripe** bilan onlayn to'lov integratsiyasi
- ✅ **Celery + Redis** bilan asinxron vazifalar (email, OTP)
- ✅ **Docker Compose** bilan bir buyruqda ishga tushirish
- ✅ **GitHub Actions** bilan avtomatik CI/CD
- ✅ **Prometheus + Grafana** bilan monitoring
- ✅ **Device fingerprint** va **audit logging** bilan chuqur xavfsizlik
- ✅ **AWS EC2**da production deploy

Loyiha 8 ta Django app, 18 ta CSS fayl, 30 dan ortiq JavaScript fayl, va 50 dan ortiq HTML shablondan iborat. Bu shunchaki o'quv loyiyasi emas — bu real production-level platforma.

---

## 9. Maslahat va Kelasi Qadamlar (1–1.5 minut)

Ushbu loyihadan o'rgangan tajribalarim asosida kelasi qadamlar va maslahatlar:

### Texnik Rivojlanish

- **Mobil ilova** — REST API tayyor, React Native yoki Flutter bilan mobil versiya qo'shish mumkin
- **WebSocket** integratsiyasi — real-time buyurtma kuzatuvi uchun
- **ElasticSearch** — dorilarni tezroq qidiruv uchun
- **Unit test coverage** ni oshirish — hozirgi testlarni kengaytirish

### Arxitektura

- **Microservices**ga o'tish — to'lov, buyurtma va autentifikatsiya alohida servislarga
- **Message queue** — Celery yordamida yanada murakkab fon vazifalar
- **CDN** — statik fayllarni tezroq tarqatish uchun

### Ish Jarayoni

- **Test-Driven Development** — dastlab testlarni yozish
- **Code Review** — jamoada kod tekshirish madaniyati
- **Hujjatlashtirish** — API Swagger bilan hujjatlashtirilgan, lekin batafsil texnik hujjatlar kerak

### O'rganish va O'sish

- **Django va DRF** — rasmiy hujjatlarni chuqurroq o'rganish
- **AWS** — EC2 dan tashqari RDS, S3, CloudFront bilan tanishish
- **DevOps** — Terraform, Ansible, Kubernetes bilan infratuzilmani kengaytirish

---

## 10. Yakuniy So'z

Ushbu loyiya men uchun birinchi katta loyiham bo'lib, backend, frontend, DevOps va xavfsizlik bo'yicha juda ko'p narsa o'rgatdi. **OnlinePharmacy** — bu shunchaki loyiha emas, balki texnologiyani amalda qo'llash va real muammolarni yechish tajribasidir.

**Sizning e'tiboringiz uchun rahmat!** Agar savollar bo'lsa, javob berishga tayyorman.

🙏 **Rahmat!**
