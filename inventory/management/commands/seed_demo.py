"""Demo ma'lumotlar: python manage.py seed_demo"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserProfile
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

        users = {}
        for username, role, pw, lang in [("admin", "admin", "admin12345", "uz"), ("manager", "manager", "manager12345", "ru"),
                                        ("employee", "employee", "employee12345", "en")]:
            u, _ = User.objects.get_or_create(username=username, defaults={
                "first_name": username.capitalize(), "email": f"{username}@company.com",
                "is_superuser": role == "admin", "is_staff": role == "admin"})
            u.set_password(pw)
            u.save()
            UserProfile.objects.update_or_create(user=u, defaults={"role": role, "language": lang})
            users[role] = u

        suppliers = [Supplier.objects.create(company_name=n, phone="+998 90 123 45 67",
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
            category = cats[cat] = Category.objects.get_or_create(name=cat)[0]
            product = Product.objects.create(name=name, category=category, price=Decimal(price),
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

        from stock.models import Notification
        from stock.services import check_alert
        Notification.objects.all().delete()
        for p in Product.objects.all():
            check_alert(p)

        self.stdout.write(self.style.SUCCESS(
            "Tayyor! Loginlar: admin/admin12345, manager/manager12345, employee/employee12345"))
