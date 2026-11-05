# InvenTrack вЂ” Inventory Management System (Django)

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

## Kirish va roвЂyxatdan oвЂtish
- Saytga kirilganda avval **RoвЂyxatdan oвЂtish** boвЂlimi chiqadi (`/register/`); **Kirish** boвЂlimiga sahifa yangilanmasdan animatsiya bilan oвЂtiladi (`/login/`).
- RoвЂyxatdan oвЂtishni oвЂchirish: `ALLOW_REGISTRATION=0`.

## Til tanlash (uz / ru / en)
- Til tugmasi bosilganda alohida animatsiyali oyna ochiladi: tillar (uz, ru, en) kartochkalari, **eng koвЂp tanlanadigan tillar (foizlarda)** va **tavsiya etiladigan til** (avval brauzer tili, u qoвЂllab-quvvatlanmasa вЂ” eng koвЂp tanlangan til).
- Foizlar roвЂyxatdan oвЂtgan foydalanuvchilar va roвЂyxatdan oвЂtish sahifasida til tanlagan mehmonlar tanlovidan hisoblanadi (har kim bir marta sanaladi, yigвЂindisi 100%).
- RoвЂyxatdan oвЂtishda tanlangan til foydalanuvchining **asosiy tili** boвЂlib profilga saqlanadi; kirishda avtomatik qoвЂllanadi.
- Tarjimalar: `tools/translations.py`. Tahrirlagach `python tools/build_locale.py` ni ishga tushiring
  (`locale/*/django.po` va `.mo` fayllari qayta yaratiladi, gettext shart emas).
- Yangi til: `config/settings.py` dagi `LANGUAGES` ga qoвЂshing, `tools/translations.py` ga tarjima kiriting.

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
| Dashboard, mahsulotlar ro'yxati, qidiruv | вњ” | вњ” | вњ” |
| Chiqim qayd etish, o'z tarixini ko'rish | вњ” | вњ” | вњ” |
| Mahsulot / kategoriya / yetkazib beruvchi CRUD | вњ” | вњ” | вњ– |
| Kirim, operatsiyani bekor qilish, hisobotlar | вњ” | вњ” | вњ– |
| Foydalanuvchilarni boshqarish | вњ” | вњ– | вњ– |
