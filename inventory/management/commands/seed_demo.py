"""Demo ma'lumotlar: python manage.py seed_demo"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Store, UserProfile
from inventory.models import Category, Product, Supplier
from stock.models import StockIn, StockMovement, StockOut
from stock.services import register_stock_in, register_stock_out

User = get_user_model()

SUPPLIERS = ["Fresh Farms Co.", "Dairy Best", "Golden Bakery", "Sunny Farm", "Green Valley", "Premium Meats"]
# nomi, kategoriya, narx, xarid, birlik, yetkazib beruvchi, minimal, yakuniy qoldiq
PRODUCTS = [
    ("Organik banan", "Mevalar", "2.99", "1.90", "kg", 0, 100, 245),
    ("Yangi sut", "Sut mahsulotlari", "3.99", "2.70", "l", 1, 150, 120),
    ("Bug‘doy noni", "Nonvoyxona", "2.49", "1.40", "pcs", 2, 50, 0),
    ("Tuxum", "Sut mahsulotlari", "5.99", "4.10", "dozen", 3, 100, 89),
    ("Cherri pomidor", "Sabzavotlar", "4.99", "3.20", "kg", 4, 80, 178),
    ("Tovuq filesi", "Go‘sht", "8.99", "6.40", "kg", 5, 100, 124),
    ("Grek yogurti", "Sut mahsulotlari", "4.49", "2.90", "pcs", 1, 60, 0),
    ("Olma", "Mevalar", "1.99", "1.20", "kg", 0, 80, 210),
    ("Sabzi", "Sabzavotlar", "1.49", "0.80", "kg", 4, 60, 55),
    ("Mineral suv 1.5L", "Ichimliklar", "0.99", "0.55", "pcs", 0, 120, 340),
]


class Command(BaseCommand):
    help = "Demo foydalanuvchilar, mahsulotlar va operatsiyalarni yaratadi"

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write(self.style.WARNING("Ma’lumotlar bor, seed o‘tkazib yuborildi."))
            return
        random.seed(7)

        store = Store.objects.create(name="FreshCart Market")
        store2 = Store.objects.create(name="Tech House")
        users = {}
        # (login, rol, parol, til, do'kon, holat)
        for username, role, pw, lang, st, status in [
            ("admin", "admin", "admin12345", "uz", None, "approved"),
            ("manager", "manager", "manager12345", "ru", store, "approved"),
            ("employee", "employee", "employee12345", "en", store, "approved"),
            ("manager2", "manager", "manager12345", "uz", store2, "approved"),
        ]:
            u, _ = User.objects.get_or_create(username=username, defaults={
                "first_name": username.capitalize(), "email": f"{username}@company.com",
                "is_superuser": role == "admin", "is_staff": role == "admin"})
            u.set_password(pw)
            u.save()
            UserProfile.objects.update_or_create(user=u, defaults={"role": role, "language": lang, "store": st,
                                                                    "status": status})
            users[username] = u
        users["admin_"] = users["admin"]
        # Ro'yxatdan o'tgan, lekin hali do'konga biriktirilmagan Employee lar (manager taklif qiladi)
        for uname, fn in [("freelancer1", "Jasur"), ("freelancer2", "Malika"), ("freelancer3", "Dilshod")]:
            fu = User.objects.create_user(uname, f"{uname}@mail.uz", "freelancer12345", first_name=fn, last_name="Karimov")
            UserProfile.objects.update_or_create(user=fu, defaults={"role": "employee", "status": "approved",
                                                                     "store": None, "language": "uz"})
        from accounts.models import StoreInvitation
        StoreInvitation.objects.create(store=store, invited_user=User.objects.get(username="freelancer1"),
                                       invited_by=users["manager"])

        # Tasdiqlash kutayotgan manager (admin uchun demo)
        pend = User.objects.create_user("pending_manager", "pending@company.com", "pending12345",
                                         first_name="Pending", last_name="Manager", is_active=False)
        UserProfile.objects.update_or_create(user=pend, defaults={
            "role": "manager", "status": "pending", "store": Store.objects.create(name="Green Valley Shop")})

        suppliers = [Supplier.objects.create(store=store, company_name=n, phone="+998 90 123 45 67",
                                             email=f"info@{n.split()[0].lower()}.uz", address="Toshkent")
                     for n in SUPPLIERS]
        cats = {}
        now = timezone.now()

        def backdate(obj, days_ago):
            ts = now - timedelta(days=days_ago, hours=random.randint(0, 8))
            type(obj).objects.filter(pk=obj.pk).update(created_at=ts)
            StockMovement.objects.filter(**{("stock_in" if isinstance(obj, StockIn) else "stock_out"): obj}
                                         ).update(created_at=ts)

        for name, cat, price, cost, unit, sup, minq, final in PRODUCTS:
            category = cats[cat] = Category.objects.get_or_create(store=store, name=cat)[0]
            product = Product.objects.create(store=store, name=name, category=category, price=Decimal(price),
                                             cost_price=Decimal(cost), unit=unit, supplier=suppliers[sup],
                                             min_quantity=minq)
            out_days = sorted(random.sample(range(0, 14), 8), reverse=True)
            outs = [random.randint(4, 18) for _ in out_days]
            restock = (min(final // 2, 60) // 2) * 2 if final else 0
            initial = final - restock + sum(outs)

            backdate(register_stock_in(product=product, quantity=initial, purchase_price=Decimal(cost),
                                       supplier=suppliers[sup], date=now.date() - timedelta(days=14),
                                       note="Boshlang‘ich zaxira", user=users["manager"]), 14)
            for day, q in zip(out_days, outs):
                backdate(register_stock_out(product=product, quantity=q, reason="sale", unit_price=None,
                                            note="", user=random.choice([users["employee"], users["manager"]])), day)
            if restock:
                for day in (9, 4):
                    backdate(register_stock_in(product=product, quantity=restock // 2, purchase_price=Decimal(cost),
                                               supplier=suppliers[sup], date=now.date() - timedelta(days=day),
                                               note="Qo‘shimcha yetkazib berish", user=users["manager"]), day)
            # Backdate qilingan operatsiyalar tartibi sababli qoldiqni aniq belgilaymiz
            Product.objects.filter(pk=product.pk).update(quantity=final)

        # Ikkinchi do'kon: ma'lumotlar do'konlar orasida aralashmasligini ko'rsatish uchun
        sup2 = Supplier.objects.create(store=store2, company_name="Samsung Distribution", phone="+998 90 555 00 11")
        cat2 = Category.objects.create(store=store2, name="Elektronika")
        for name, price, cost, qty in [("Smartfon A15", "199.00", "150.00", 25), ("Quloqchin Buds", "49.00", "30.00", 8)]:
            p2 = Product.objects.create(store=store2, name=name, category=cat2, supplier=sup2, price=Decimal(price),
                                        cost_price=Decimal(cost), unit="pcs", min_quantity=10)
            register_stock_in(product=p2, quantity=qty, purchase_price=Decimal(cost), supplier=sup2,
                              date=now.date(), note="Boshlang‘ich zaxira", user=users["manager2"])

        from stock.models import Notification
        from stock.services import check_alert
        Notification.objects.all().delete()
        for p in Product.objects.all():
            check_alert(p)

        self.stdout.write(self.style.SUCCESS(
            "Tayyor! Loginlar: admin/admin12345, manager/manager12345 (FreshCart), employee/employee12345, "
            "manager2/manager12345 (Tech House). pending_manager/pending12345 — tasdiq kutmoqda. "
            "freelancer1..3 / freelancer12345 — do‘konsiz Employee (freelancer1 ga taklif yuborilgan)."))
