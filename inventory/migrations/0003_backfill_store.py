from django.db import migrations


def backfill(apps, schema_editor):
    """Eski ma'lumotlar (do'kon tushunchasi yo'q edi) bitta standart do'konga biriktiriladi."""
    Store = apps.get_model("accounts", "Store")
    Profile = apps.get_model("accounts", "UserProfile")
    Category, Supplier, Product = (apps.get_model("inventory", n) for n in ("Category", "Supplier", "Product"))
    staff = Profile.objects.filter(role__in=["manager", "employee"], store__isnull=True)
    if not (Category.objects.exists() or Supplier.objects.exists() or Product.objects.exists() or staff.exists()):
        return
    store = Store.objects.first() or Store.objects.create(name="Asosiy do‘kon")
    Category.objects.filter(store__isnull=True).update(store=store)
    Supplier.objects.filter(store__isnull=True).update(store=store)
    Product.objects.filter(store__isnull=True).update(store=store)
    staff.update(store=store)


class Migration(migrations.Migration):
    dependencies = [("inventory", "0002_store_fields"), ("accounts", "0004_store_status_audit")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
