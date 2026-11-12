import django.db.models.deletion
from django.db import migrations, models


def store_field(related):
    return models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name=related,
                             to="accounts.store", verbose_name="Do‘kon")


class Migration(migrations.Migration):
    dependencies = [("inventory", "0003_backfill_store")]

    operations = [
        migrations.AlterField(model_name="category", name="store", field=store_field("categories")),
        migrations.AlterField(model_name="supplier", name="store", field=store_field("suppliers")),
        migrations.AlterField(model_name="product", name="store", field=store_field("products")),
        migrations.AddConstraint(model_name="category", constraint=models.UniqueConstraint(
            fields=("store", "name"), name="uniq_category_store_name")),
        migrations.AddConstraint(model_name="product", constraint=models.UniqueConstraint(
            fields=("store", "sku"), name="uniq_product_store_sku")),
    ]
