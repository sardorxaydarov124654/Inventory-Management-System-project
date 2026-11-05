from django.utils.translation import gettext_lazy as _
import uuid

from django.db import models
from django.db.models import F


class Category(models.Model):
    name = models.CharField(_("Nomi"), max_length=100, unique=True)
    description = models.TextField(_("Tavsif"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Kategoriya")
        verbose_name_plural = _("Kategoriyalar")

    def __str__(self):
        return self.name


class Supplier(models.Model):
    company_name = models.CharField(_("Kompaniya nomi"), max_length=150)
    phone = models.CharField(_("Telefon"), max_length=30, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    address = models.CharField(_("Manzil"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company_name"]
        verbose_name = _("Yetkazib beruvchi")
        verbose_name_plural = _("Yetkazib beruvchilar")

    def __str__(self):
        return self.company_name


class ProductQuerySet(models.QuerySet):
    def out(self):
        return self.filter(quantity__lte=0)

    def low(self):
        return self.filter(quantity__gt=0, quantity__lte=F("min_quantity"))

    def in_stock(self):
        return self.filter(quantity__gt=F("min_quantity"))

    def filter_status(self, status):
        return {"ok": self.in_stock, "low": self.low, "out": self.out}.get(status, lambda: self)()


class Product(models.Model):
    UNIT_CHOICES = [
        ("pcs", _("dona")),
        (_("kg"), _("kg")),
        ("l", "L"),
        ("dozen", _("o‘nlik")),
        ("box", _("quti")),
        (_("m"), _("m")),
    ]

    name = models.CharField(_("Nomi"), max_length=200)
    sku = models.CharField(_("SKU / kod"), max_length=40, unique=True, blank=True,
                           help_text=_("Bo‘sh qoldirsangiz, avtomatik yaratiladi."))
    category = models.ForeignKey(Category, verbose_name=_("Kategoriya"), on_delete=models.PROTECT,
                                 related_name="products", null=True, blank=True)
    supplier = models.ForeignKey(Supplier, verbose_name=_("Yetkazib beruvchi"), on_delete=models.SET_NULL,
                                 related_name="products", null=True, blank=True)
    description = models.TextField(_("Tavsif"), blank=True)
    image = models.ImageField(_("Rasm"), upload_to="products/", blank=True, null=True)
    price = models.DecimalField(_("Sotuv narxi"), max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(_("Xarid narxi"), max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(_("O‘lchov birligi"), max_length=10, choices=UNIT_CHOICES, default="pcs")
    quantity = models.PositiveIntegerField(_("Miqdor"), default=0, editable=False)
    min_quantity = models.PositiveIntegerField(_("Minimal zaxira"), default=10)
    is_active = models.BooleanField(_("Faol"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = _("Mahsulot")
        verbose_name_plural = _("Mahsulotlar")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = "SKU-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.quantity <= 0:
            return "out"
        if self.quantity <= self.min_quantity:
            return "low"
        return "ok"

    @property
    def status_label(self):
        return {"ok": _("Mavjud"), "low": _("Kam qolgan"), "out": _("Tugagan")}[self.status]

    @property
    def stock_percent(self):
        """Progress bar uchun foiz (minimal zaxiraning 2 baravari = 100%)."""
        full = max(self.min_quantity * 2, 1)
        return int(min(100, self.quantity * 100 / full))

    @property
    def stock_value(self):
        return self.quantity * self.cost_price
