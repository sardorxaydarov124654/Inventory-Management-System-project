from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stock"
    verbose_name = _("Kirim-chiqim")
