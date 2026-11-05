from django import forms

from accounts.mixins import StyledFormMixin

from .models import Category, Product, Supplier


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class SupplierForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["company_name", "phone", "email", "address"]


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "category", "supplier", "price", "cost_price", "unit",
                  "min_quantity", "image", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
