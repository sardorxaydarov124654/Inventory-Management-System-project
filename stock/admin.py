from django.contrib import admin

from .models import Notification, StockIn, StockMovement, StockOut


@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "purchase_price", "supplier", "date", "created_by", "is_cancelled")
    list_filter = ("is_cancelled", "date", "supplier")
    search_fields = ("product__name",)
    readonly_fields = ("created_by", "created_at", "cancelled_at", "cancelled_by")

    def has_add_permission(self, request):
        return False  # qoldiq buzilmasligi uchun operatsiyalar faqat sayt orqali qayd etiladi


@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "reason", "unit_price", "created_by", "created_at", "is_cancelled")
    list_filter = ("is_cancelled", "reason")
    search_fields = ("product__name",)
    readonly_fields = ("created_by", "created_at", "cancelled_at", "cancelled_by")

    def has_add_permission(self, request):
        return False  # qoldiq buzilmasligi uchun operatsiyalar faqat sayt orqali qayd etiladi


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "change", "balance_after", "user", "created_at")
    list_filter = ("movement_type",)
    search_fields = ("product__name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read")
