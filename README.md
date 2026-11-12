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

Demo loginlar: pastdagi "Manager ro‘yxatdan o‘tishi" bo‘limiga qarang
O'zingizning admin hisobingiz uchun: `python manage.py createsuperuser`

## Ro‘yxatdan o‘tish: Manager yoki Employee
Saytga kirilganda ro‘yxatdan o‘tish bo‘limi chiqadi (`/accounts/register/`). Hisob turi tanlanadi:
- **Manager** — "Do‘kon / biznes nomi" majburiy. Ariza **Pending** bo‘ladi, administrator Django Admin → *Manager arizalari* da Approve / Reject qiladi. Tasdiqlanmaguncha login qila olmaydi. Manager uchun alohida do‘kon (ombor) yaratiladi.
- **Employee** — do‘kon nomi so‘ralmaydi (qolgan hamma maydonlar to‘ldiriladi). Tasdiq shart emas: darhol kiradi, lekin hech qaysi do‘konga biriktirilmagan bo‘ladi va do‘kon ma’lumotlarini ko‘rmaydi.
- Rol va holat faqat serverda belgilanadi (admin tanlab bo‘lmaydi).

## Xodimni do‘konga taklif qilish
Manager endi xodim akkauntini o‘zi yaratmaydi (bunday akkaunt bilan xodim o‘z parolini bilmasdi). O‘rniga:
1. Employee o‘zi ro‘yxatdan o‘tadi va login (username) ini menejerga aytadi.
2. Manager → **Xodimlar** bo‘limi (`/accounts/team/`): ro‘yxatdan o‘tgan, hali do‘konga biriktirilmagan Employee lar ro‘yxati. **Login (username) bo‘yicha qidirish** bor. Tanlangan xodimga **Taklif qilish** bosiladi.
3. Employee o‘z panelida va yuqoridagi qo‘ng‘iroq belgisida taklif xabarini ko‘radi: yashil **Confirm** va qizil **Reject** tugmalari.
4. Confirm → employee manager do‘koniga qo‘shiladi (boshqa takliflar bekor qilinadi). Reject → taklif rad etiladi.
5. Manager javobni qo‘ng‘iroq belgisida va "Yuborilgan takliflar" ro‘yxatida ko‘radi. Taklifni bekor qilish va xodimni do‘kondan chiqarish mumkin (akkaunt o‘chmaydi, qayta taklif qilish mumkin).
- Admin foydalanuvchilarni `/accounts/users/` va Django Admin orqali boshqaradi.
- Demo (`seed_demo`): `admin/admin12345`, `manager/manager12345` (FreshCart), `employee/employee12345`, `manager2/manager12345` (Tech House), `pending_manager/pending12345` (tasdiq kutmoqda), `freelancer1..3 / freelancer12345` (do‘konsiz Employee; freelancer1 ga taklif yuborilgan).

## Qo‘shimcha
- Barcha ma’lumotlar **do‘konga qarab ajratilgan**: manager va xodim faqat o‘z do‘konini ko‘radi, admin hammasini.
- Muhim amallar (ariza, tasdiqlash, taklif, javob, kirim, chiqim, bekor qilish) **Audit tarixi** da saqlanadi (Django Admin).
- Eski bazangiz bo‘lsa: `python manage.py migrate` — mavjud ma’lumotlar "Asosiy do‘kon" ga biriktiriladi.
- Ommaviy ro‘yxatdan o‘tishni o‘chirish: `ALLOW_REGISTRATION=0`.

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
| Foydalanuvchilarni boshqarish | ✔ (hammasi) | ✖ | ✖ |
| Xodimlarni taklif qilish / do‘kondan chiqarish | ✖ | ✔ (o‘z do‘koni) | ✖ |
| Taklifga javob berish (Confirm / Reject) | ✖ | ✖ | ✔ |
| Manager arizalarini tasdiqlash | ✔ | ✖ | ✖ |
