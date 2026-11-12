from django import forms
from django.utils.translation import gettext as _
from django.utils import timezone

from accounts.mixins import StoreScopedFormMixin
from inventory.models import Product

from .models import StockIn, StockOut


class StockInForm(StoreScopedFormMixin, forms.ModelForm):
    scoped_fields = ("product", "supplier")

    class Meta:
        model = StockIn
        fields = ["product", "supplier", "quantity", "purchase_price", "date", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = self.fields["product"].queryset.filter(is_active=True)
        self.fields["date"].initial = timezone.localdate()

    def clean(self):
        data = super().clean()
        product, supplier = data.get("product"), data.get("supplier")
        if product and supplier and supplier.store_id != product.store_id:
            self.add_error("supplier", _("Bu obyekt boshqa do‘konga tegishli."))
        return data


class StockOutForm(StoreScopedFormMixin, forms.ModelForm):
    scoped_fields = ("product",)

    class Meta:
        model = StockOut
        fields = ["product", "quantity", "reason", "unit_price", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = self.fields["product"].queryset.filter(is_active=True, quantity__gt=0)

    def clean(self):
        data = super().clean()
        product, qty = data.get("product"), data.get("quantity")
        if product and qty and qty > product.quantity:
            self.add_error("quantity", _("Omborda faqat %(qty)s %(unit)s mavjud.") % {"qty": product.quantity, "unit": product.get_unit_display()})
        return data
