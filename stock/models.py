from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from inventory.models import Product, Supplier


class StockIn(models.Model):
    """Mahsulot kirimi."""
    product = models.ForeignKey(Product, verbose_name=_("Mahsulot"), on_delete=models.PROTECT, related_name="stock_ins")
    supplier = models.ForeignKey(Supplier, verbose_name=_("Yetkazib beruvchi"), on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="stock_ins")
    quantity = models.PositiveIntegerField(_("Miqdor"), validators=[MinValueValidator(1)])
    purchase_price = models.DecimalField(_("Xarid narxi"), max_digits=12, decimal_places=2, default=0)
    date = models.DateField(_("Kirim sanasi"), default=timezone.localdate)
    note = models.TextField(_("Izoh"), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="stock_ins")
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(_("Bekor qilingan"), default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Kirim")
        verbose_name_plural = _("Kirimlar")

    def __str__(self):
        return f"+{self.quantity} {self.product}"

    @property
    def total(self):
        return self.quantity * self.purchase_price


class StockOut(models.Model):
    """Mahsulot chiqimi."""
    SALE, DAMAGED, RETURN, OTHER = "sale", "damaged", "return", "other"
    REASON_CHOICES = [
        (SALE, _("Sotuv")),
        (DAMAGED, _("Yaroqsiz / buzilgan")),
        (RETURN, _("Qaytarish")),
        (OTHER, _("Boshqa")),
    ]

    product = models.ForeignKey(Product, verbose_name=_("Mahsulot"), on_delete=models.PROTECT, related_name="stock_outs")
    quantity = models.PositiveIntegerField(_("Miqdor"), validators=[MinValueValidator(1)])
    reason = models.CharField(_("Sabab"), max_length=10, choices=REASON_CHOICES, default=SALE)
    unit_price = models.DecimalField(_("Sotuv narxi"), max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text=_("BoвЂsh qoldirsangiz, mahsulotning joriy narxi olinadi."))
    note = models.TextField(_("Izoh"), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="stock_outs")
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(_("Bekor qilingan"), default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Chiqim")
        verbose_name_plural = _("Chiqimlar")

    def __str__(self):
        return f"-{self.quantity} {self.product}"

    @property
    def total(self):
        return self.quantity * (self.unit_price or 0)


class StockMovement(models.Model):
    """Ombordagi har bir harakat tarixi (o'chirilmaydi)."""
    IN, OUT, CANCEL_IN, CANCEL_OUT = "in", "out", "cancel_in", "cancel_out"
    TYPE_CHOICES = [
        (IN, _("Kirim")),
        (OUT, _("Chiqim")),
        (CANCEL_IN, _("Kirim bekor qilindi")),
        (CANCEL_OUT, _("Chiqim bekor qilindi")),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(_("Turi"), max_length=10, choices=TYPE_CHOICES)
    change = models.IntegerField(_("OвЂzgarish"))
    balance_after = models.PositiveIntegerField(_("Qoldiq"))
    stock_in = models.ForeignKey(StockIn, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    stock_out = models.ForeignKey(StockOut, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="movements")
    note = models.CharField(_("Izoh"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("Harakat")
        verbose_name_plural = _("Ombor harakatlari")

    def __str__(self):
        return f"{self.product} {self.change:+d}"


class Notification(models.Model):
    LOW, OUT = "low", "out"
    KIND_CHOICES = [(LOW, _("Kam qolgan")), (OUT, _("Tugagan"))]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=5, choices=KIND_CHOICES)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Ogohlantirish")
        verbose_name_plural = _("Ogohlantirishlar")

    def __str__(self):
        return self.message
