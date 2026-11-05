# InvenTrack — Inventory Management System (Django)

## Ishga tushirish
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # demo ma'lumotlar (ixtiyoriy)
python manage.py runserver
```
Brauzerda: http://127.0.0.1:8000

Demo loginlar (seed_demo): `admin / admin12345`, `manager / manager12345`, `employee / employee12345`
O'zingizning admin hisobingiz uchun: `python manage.py createsuperuser`

## Kirish va ro‘yxatdan o‘tish
- Saytga kirilganda avval **Ro‘yxatdan o‘tish** bo‘limi chiqadi (`/register/`); **Kirish** bo‘limiga sahifa yangilanmasdan animatsiya bilan o‘tiladi (`/login/`).
- Ro‘yxatdan o‘tishni o‘chirish: `ALLOW_REGISTRATION=0`.

## Til tanlash (uz / ru / en)
- Til tugmasi bosilganda alohida animatsiyali oyna ochiladi: tillar (uz, ru, en) kartochkalari, **eng ko‘p tanlanadigan tillar (foizlarda)** va **tavsiya etiladigan til** (avval brauzer tili, u qo‘llab-quvvatlanmasa — eng ko‘p tanlangan til).
- Foizlar ro‘yxatdan o‘tgan foydalanuvchilar va ro‘yxatdan o‘tish sahifasida til tanlagan mehmonlar tanlovidan hisoblanadi (har kim bir marta sanaladi, yig‘indisi 100%).
- Ro‘yxatdan o‘tishda tanlangan til foydalanuvchining **asosiy tili** bo‘lib profilga saqlanadi; kirishda avtomatik qo‘llanadi.
- Tarjimalar: `tools/translations.py`. Tahrirlagach `python tools/build_locale.py` ni ishga tushiring
  (`locale/*/django.po` va `.mo` fayllari qayta yaratiladi, gettext shart emas).
- Yangi til: `config/settings.py` dagi `LANGUAGES` ga qo‘shing, `tools/translations.py` ga tarjima kiriting.

## PostgreSQL
Environment o'zgaruvchilari berilsa PostgreSQL ishlatiladi (aks holda SQLite):
`DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT`

## Render (deploy)
- Build Command: `./build.sh`
- Start Command: `gunicorn config.wsgi`
- Env: `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS=sizning-sayt.onrender.com`,
  `CSRF_TRUSTED_ORIGINS=https://sizning-sayt.onrender.com`, `DB_*`
- Valyuta belgisi: `CURRENCY` (standart `$`), sayt nomi: `SITE_NAME`

## Rollar
| Imkoniyat | Admin | Manager | Employee |
|---|---|---|---|
| Dashboard, mahsulotlar ro'yxati, qidiruv | ✔ | ✔ | ✔ |
| Chiqim qayd etish, o'z tarixini ko'rish | ✔ | ✔ | ✔ |
| Mahsulot / kategoriya / yetkazib beruvchi CRUD | ✔ | ✔ | ✖ |
| Kirim, operatsiyani bekor qilish, hisobotlar | ✔ | ✔ | ✖ |
| Foydalanuvchilarni boshqarish | ✔ | ✖ | ✖ |
