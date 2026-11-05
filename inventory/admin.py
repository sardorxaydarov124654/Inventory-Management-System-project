from django.contrib import admin

from .models import Category, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone", "email", "address")
    search_fields = ("company_name", "phone", "email")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "supplier", "quantity", "min_quantity", "price", "is_active")
    list_filter = ("category", "supplier", "is_active")
    search_fields = ("name", "sku")
    readonly_fields = ("quantity", "created_at", "updated_at")
