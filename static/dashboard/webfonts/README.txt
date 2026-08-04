================================================================================
  OnlinePharmacy Dashboard — Poppins Webfont Setup
================================================================================

Bu papkaga Poppins shrift fayllarini joylashtiring. theme.css ularni
@font-face orqali yuklaydi.

--------------------------------------------------------------------------------
1. GOOGLE FONTSDAN YUKLAB OLISH
--------------------------------------------------------------------------------

Rasmiy Google Fonts sahifasi:
  https://fonts.google.com/specimen/Poppins

To'g'ridan-to'g'ri CSS (brauzerda oching, keyin woff2 URL larni oling):
  https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap

Yoki google-webfonts-helper (tavsiya etiladi):
  https://gwfh.mranftl.com/fonts/poppins?subsets=latin,latin-ext,cyrillic

Kerakli og'irliklar: 300 (Light), 400 (Regular), 500 (Medium), 600 (SemiBold), 700 (Bold)

--------------------------------------------------------------------------------
2. FAYLLARNI JOYLASHTIRISH
--------------------------------------------------------------------------------

Quyidagi struktura bo'lishi kerak:

  static/dashboard/webfonts/
  ├── README.txt          (bu fayl)
  └── poppins/
      ├── Poppins-Light.woff2       (font-weight: 300)
      ├── Poppins-Regular.woff2     (font-weight: 400)
      ├── Poppins-Medium.woff2      (font-weight: 500)
      ├── Poppins-SemiBold.woff2    (font-weight: 600)
      └── Poppins-Bold.woff2        (font-weight: 700)

Ixtiyoriy (eski brauzerlar uchun):
      ├── Poppins-Regular.woff
      └── Poppins-Bold.woff

--------------------------------------------------------------------------------
3. theme.css ICHIDAGI @font-face YO'LLARI
--------------------------------------------------------------------------------

theme.css dagi yo'llar quyidagicha sozlangan:

  url('../webfonts/poppins/Poppins-Light.woff2')
  url('../webfonts/poppins/Poppins-Regular.woff2')
  url('../webfonts/poppins/Poppins-Medium.woff2')
  url('../webfonts/poppins/Poppins-SemiBold.woff2')
  url('../webfonts/poppins/Poppins-Bold.woff2')

Agar fayl nomlari boshqacha bo'lsa, theme.css ichidagi @font-face bloklarini
mos ravishda yangilang. Masalan, faqat bitta Poppins-VariableFont.woff2
bo'lsa:

  @font-face {
    font-family: 'Poppins';
    src: url('../webfonts/poppins/Poppins-VariableFont.woff2') format('woff2-variations');
    font-weight: 300 700;
    font-style: normal;
    font-display: swap;
  }

--------------------------------------------------------------------------------
4. TEKSHIRISH
--------------------------------------------------------------------------------

1. Fayllarni poppins/ papkasiga nusxalang.
2. Django static collect:  python manage.py collectstatic
3. Brauzer DevTools → Network → filter "woff2" — 200 status tekshiring.
4. Agar shrift yuklanmasa, fallback: system-ui, sans-serif ishlatiladi.

--------------------------------------------------------------------------------
5. Eslatma
--------------------------------------------------------------------------------

base.html hozir Google Fonts CDN dan ham yuklaydi. To'liq offline ishlash uchun
HTML dagi Google Fonts <link> teglarini olib tashlang va faqat theme.css
@font-face ga tayaning.

================================================================================
