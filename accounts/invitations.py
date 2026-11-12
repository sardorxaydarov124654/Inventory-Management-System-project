"""Do'konga taklif qilish: yuborish, javob berish, bekor qilish, do'kondan chiqarish."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .audit import audit
from .mixins import get_role, get_store
from .models import StoreInvitation, UserProfile

User = get_user_model()


def available_employees():
    """Taklif qilish mumkin bo'lgan Employee lar: ro'yxatdan o'tgan, hali hech qaysi do'konga biriktirilmagan."""
    return User.objects.filter(is_active=True, profile__role=UserProfile.EMPLOYEE,
                               profile__status=UserProfile.APPROVED, profile__store__isnull=True)


@transaction.atomic
def send_invitation(manager, employee_id):
    store = get_store(manager)
    if get_role(manager) != "manager" or store is None:
        raise ValidationError(_("Taklif yuborish uchun do‘konli menejer bo‘lishingiz kerak."))
    employee = available_employees().select_for_update().filter(pk=employee_id).first()
    if employee is None:
        raise ValidationError(_("Bu foydalanuvchini taklif qilib bo‘lmaydi."))
    if StoreInvitation.objects.filter(store=store, invited_user=employee, status=StoreInvitation.PENDING).exists():
        raise ValidationError(_("Bu foydalanuvchiga taklif allaqachon yuborilgan."))
    invitation = StoreInvitation.objects.create(store=store, invited_user=employee, invited_by=manager)
    audit(manager, "invitation_sent", employee.get_username(), store.name, store=store)
    return invitation


@transaction.atomic
def respond_to_invitation(invitation, user, accept):
    """Employee taklifga javob beradi (Confirm / Reject)."""
    invitation = StoreInvitation.objects.select_for_update().select_related("store").get(pk=invitation.pk)
    if invitation.invited_user_id != user.pk or invitation.status != StoreInvitation.PENDING:
        raise ValidationError(_("Bu taklif endi amal qilmaydi."))
    profile = UserProfile.objects.select_for_update().get(user=user)
    if accept and profile.store_id:
        invitation.status = StoreInvitation.CANCELLED
        invitation.save(update_fields=["status"])
        raise ValidationError(_("Siz allaqachon do‘konga biriktirilgansiz."))
    invitation.status = StoreInvitation.ACCEPTED if accept else StoreInvitation.REJECTED
    invitation.responded_at, invitation.inviter_seen = timezone.now(), False
    invitation.save(update_fields=["status", "responded_at", "inviter_seen"])
    if accept:
        profile.store = invitation.store
        profile.save()
        # Boshqa kutilayotgan takliflar endi kerak emas
        StoreInvitation.objects.filter(invited_user=user, status=StoreInvitation.PENDING).update(
            status=StoreInvitation.CANCELLED)
    audit(user, "invitation_accepted" if accept else "invitation_rejected", invitation.store.name,
          user.get_username(), store=invitation.store)
    return invitation


def cancel_invitation(manager, invitation):
    store = get_store(manager)
    if store is None or invitation.store_id != store.pk or invitation.status != StoreInvitation.PENDING:
        raise ValidationError(_("Bu taklif endi amal qilmaydi."))
    invitation.status = StoreInvitation.CANCELLED
    invitation.save(update_fields=["status"])
    audit(manager, "invitation_cancelled", invitation.invited_user.get_username(), store=store)


def remove_member(manager, employee):
    """Employee ni do'kondan chiqaradi (akkaunt o'chmaydi, qayta taklif qilish mumkin)."""
    store = get_store(manager)
    profile = employee.profile
    if store is None or profile.store_id != store.pk or profile.role != UserProfile.EMPLOYEE:
        raise ValidationError(_("Bu foydalanuvchini do‘kondan chiqarib bo‘lmaydi."))
    profile.store = None
    profile.save()
    audit(manager, "employee_removed", employee.get_username(), store=store)
