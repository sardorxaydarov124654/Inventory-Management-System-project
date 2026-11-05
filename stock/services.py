"""Ombor operatsiyalari: barcha o'zgarishlar tranzaksiya ichida bajariladi."""
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import Product

from .models import Notification, StockIn, StockMovement, StockOut


def check_alert(product):
    """Zaxira minimal darajadan kamaysa ogohlantirish yaratadi, tiklansa yopadi."""
    if product.quantity <= 0:
        kind, msg = Notification.OUT, _("“%(name)s” tugadi!") % {"name": product.name}
    elif product.quantity <= product.min_quantity:
        kind = Notification.LOW
        msg = _("“%(name)s” kam qoldi: %(qty)s %(unit)s (min: %(min)s)") % {
            "name": product.name, "qty": product.quantity, "unit": product.get_unit_display(), "min": product.min_quantity}
    else:
        Notification.objects.filter(product=product, is_read=False).update(is_read=True)
        return
    Notification.objects.get_or_create(product=product, kind=kind, is_read=False, defaults={"message": msg})


def _lock(product):
    return Product.objects.select_for_update().get(pk=product.pk)


@transaction.atomic
def register_stock_in(*, product, quantity, purchase_price, supplier, date, note, user):
    product = _lock(product)
    obj = StockIn.objects.create(
        product=product, supplier=supplier, quantity=quantity, purchase_price=purchase_price or 0,
        date=date, note=note, created_by=user,
    )
    product.quantity += quantity
    if purchase_price:
        product.cost_price = purchase_price
    if supplier and not product.supplier_id:
        product.supplier = supplier
    product.save()
    StockMovement.objects.create(
        product=product, movement_type=StockMovement.IN, change=quantity,
        balance_after=product.quantity, stock_in=obj, user=user, note=note[:255],
    )
    check_alert(product)
    return obj


@transaction.atomic
def register_stock_out(*, product, quantity, reason, unit_price, note, user):
    product = _lock(product)
    if quantity > product.quantity:
        raise ValidationError(_("Omborda faqat %(qty)s %(unit)s mavjud.") % {"qty": product.quantity, "unit": product.get_unit_display()})
    obj = StockOut.objects.create(
        product=product, quantity=quantity, reason=reason,
        unit_price=unit_price if unit_price is not None else product.price,
        note=note, created_by=user,
    )
    product.quantity -= quantity
    product.save()
    StockMovement.objects.create(
        product=product, movement_type=StockMovement.OUT, change=-quantity,
        balance_after=product.quantity, stock_out=obj, user=user, note=note[:255],
    )
    check_alert(product)
    return obj


@transaction.atomic
def cancel_operation(obj, user):
    """Operatsiyani o'chirmasdan bekor qiladi va qoldiqni qaytaradi."""
    obj = type(obj).objects.select_for_update().get(pk=obj.pk)
    if obj.is_cancelled:
        raise ValidationError(_("Bu operatsiya allaqachon bekor qilingan."))
    product = _lock(obj.product)
    if isinstance(obj, StockIn):
        if product.quantity < obj.quantity:
            raise ValidationError(_("Kirimni bekor qilib bo‘lmaydi: mahsulot qisman chiqarib yuborilgan."))
        product.quantity -= obj.quantity
        movement = dict(movement_type=StockMovement.CANCEL_IN, change=-obj.quantity, stock_in=obj)
    else:
        product.quantity += obj.quantity
        movement = dict(movement_type=StockMovement.CANCEL_OUT, change=obj.quantity, stock_out=obj)
    product.save()
    obj.is_cancelled = True
    obj.cancelled_at = timezone.now()
    obj.cancelled_by = user
    obj.save(update_fields=["is_cancelled", "cancelled_at", "cancelled_by"])
    StockMovement.objects.create(product=product, balance_after=product.quantity, user=user,
                                 note=_("Operatsiya bekor qilindi"), **movement)
    check_alert(product)
