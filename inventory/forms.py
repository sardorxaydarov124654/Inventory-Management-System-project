from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.mixins import StoreScopedFormMixin

from .models import Category, Product, Supplier


class CategoryForm(StoreScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["store", "name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        data = super().clean()
        name, store_id = data.get("name"), self.current_store_id(data)
        if name and store_id and Category.objects.filter(store_id=store_id, name__iexact=name).exclude(
                pk=self.instance.pk).exists():
            self.add_error("name", _("Bu kategoriya nomi allaqachon mavjud."))
        return data


class SupplierForm(StoreScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["store", "company_name", "phone", "email", "address"]


class ProductForm(StoreScopedFormMixin, forms.ModelForm):
    scoped_fields = ("category", "supplier")

    class Meta:
        model = Product
        fields = ["store", "name", "sku", "category", "supplier", "price", "cost_price", "unit",
                  "min_quantity", "image", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        data = super().clean()
        sku, store_id = data.get("sku"), self.current_store_id(data)
        if sku and store_id and Product.objects.filter(store_id=store_id, sku=sku).exclude(pk=self.instance.pk).exists():
            self.add_error("sku", _("Bu SKU allaqachon ishlatilgan."))
        return data
