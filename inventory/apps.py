from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = _("Ombor")
