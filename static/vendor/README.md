# Vendor Files — Online Pharmacy Admin Dashboard

Place local vendor files here. They are served as Django static files.

## Directory Structure

```
static/vendor/
├── chartjs/
│   └── chart.min.js            ← Chart.js v4 UMD bundle
├── fontawesome/
│   └── css/
│       └── all.min.css         ← Font Awesome 6 Free CSS
└── webfonts/                   ← Font Awesome webfont files
    ├── fa-solid-900.woff2
    ├── fa-solid-900.ttf
    ├── fa-regular-400.woff2
    ├── fa-regular-400.ttf
    ├── fa-brands-400.woff2
    └── fa-brands-400.ttf
```

---

## Installation Commands

### Chart.js (via npm)
```powershell
npm install chart.js
Copy-Item node_modules/chart.js/dist/chart.umd.min.js static/vendor/chartjs/chart.min.js
```

### Font Awesome (via npm)
```powershell
npm install @fortawesome/fontawesome-free
Copy-Item node_modules/@fortawesome/fontawesome-free/css/all.min.css static/vendor/fontawesome/css/all.min.css
Copy-Item -Recurse node_modules/@fortawesome/fontawesome-free/webfonts/* static/vendor/webfonts/
```

### Or download manually
- Chart.js:      https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js
- Font Awesome:  https://fontawesome.com/download  (Free for Web → extract & copy)

---

## Font Awesome CSS — Local Font Path

After copying `all.min.css`, verify the `@font-face` `src` URLs reference the correct local path.
The default Font Awesome paths use `../webfonts/` which maps to `static/vendor/webfonts/` when
`all.min.css` lives at `static/vendor/fontawesome/css/all.min.css`. No path changes needed.

---

## Django STATICFILES_DIRS

Make sure `static/` is listed in `STATICFILES_DIRS` in `settings.py`:

```python
STATICFILES_DIRS = [BASE_DIR / 'static']
```
