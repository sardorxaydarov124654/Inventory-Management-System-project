from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class Store(models.Model):
    """Do'kon / biznes. Mahsulotlar, kategoriyalar va yetkazib beruvchilar shu do'konga biriktiriladi."""
    name = models.CharField(_("Do‘kon / biznes nomi"), max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Do‘kon")
        verbose_name_plural = _("Do‘konlar")

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    ROLE_CHOICES = [
        (ADMIN, _("Administrator")),
        (MANAGER, _("Menejer")),
        (EMPLOYEE, _("Xodim")),
    ]
    PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
    STATUS_CHOICES = [
        (PENDING, _("Kutilmoqda")),
        (APPROVED, _("Tasdiqlangan")),
        (REJECTED, _("Rad etilgan")),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(_("Rol"), max_length=10, choices=ROLE_CHOICES, default=EMPLOYEE)
    phone = models.CharField(_("Telefon"), max_length=20, blank=True)
    language = models.CharField(_("Til"), max_length=5, choices=settings.LANGUAGES, blank=True,
                                help_text=_("Tizimga kirganda avtomatik tanlanadigan til."))
    store = models.ForeignKey(Store, verbose_name=_("Do‘kon"), null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="members")
    # Ariza holati faqat server tomonidan belgilanadi (foydalanuvchi formasidan olinmaydi)
    status = models.CharField(_("Holat"), max_length=10, choices=STATUS_CHOICES, default=APPROVED)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Foydalanuvchi profili")
        verbose_name_plural = _("Foydalanuvchi profillari")

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"


class ManagerApplication(UserProfile):
    """Django Admin da Manager arizalarini ko'rish va tasdiqlash uchun proxy model."""

    class Meta:
        proxy = True
        verbose_name = _("Manager arizasi")
        verbose_name_plural = _("Manager arizalari")


class StoreInvitation(models.Model):
    """Manager o'z do'koniga ro'yxatdan o'tgan Employee ni taklif qiladi; Employee tasdiqlaydi yoki rad etadi."""
    PENDING, ACCEPTED, REJECTED, CANCELLED = "pending", "accepted", "rejected", "cancelled"
    STATUS_CHOICES = [
        (PENDING, _("Kutilmoqda")),
        (ACCEPTED, _("Qabul qilindi")),
        (REJECTED, _("Rad etildi")),
        (CANCELLED, _("Bekor qilindi")),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="invitations")
    invited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_invitations")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    inviter_seen = models.BooleanField(default=True)  # Employee javobini manager ko'rdimi

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("Do‘konga taklif")
        verbose_name_plural = _("Do‘konga takliflar")
        constraints = [
            models.UniqueConstraint(fields=["store", "invited_user"], condition=models.Q(status="pending"),
                                    name="uniq_pending_invitation_per_store"),
        ]

    def __str__(self):
        return f"{self.store} -> {self.invited_user} ({self.status})"


class AuditLog(models.Model):
    """Muhim amallar tarixi (manager tasdiqlash, ombor operatsiyalari va h.k.)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(_("Amal"), max_length=40)
    target = models.CharField(_("Obyekt"), max_length=200, blank=True)
    detail = models.CharField(_("Tafsilot"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("Audit yozuvi")
        verbose_name_plural = _("Audit tarixi")

    def __str__(self):
        return f"{self.action}: {self.target}"


class LanguageChoice(models.Model):
    """Til tanlovlari statistikasi uchun: har bir mehmon (v...) yoki foydalanuvchi (u...) uchun bitta yozuv."""
    voter = models.CharField(max_length=40, unique=True)
    language = models.CharField(max_length=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Til tanlovi"
        verbose_name_plural = "Til tanlovlari"

    def __str__(self):
        return f"{self.voter}: {self.language}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            role=UserProfile.ADMIN if instance.is_superuser else UserProfile.EMPLOYEE,
        )


@receiver(post_save, sender=UserProfile)
def sync_profile_choice(sender, instance, **kwargs):
    """Profildagi til o'zgarsa, statistikadagi tanlov ham yangilanadi."""
    voter = f"u{instance.user_id}"
    if instance.language:
        LanguageChoice.objects.update_or_create(voter=voter, defaults={"language": instance.language})
    else:
        LanguageChoice.objects.filter(voter=voter).delete()


@receiver(post_delete, sender=UserProfile)
def drop_profile_choice(sender, instance, **kwargs):
    LanguageChoice.objects.filter(voter=f"u{instance.user_id}").delete()


@receiver([post_save, post_delete], sender=LanguageChoice)
def reset_language_stats(sender, **kwargs):
    from .languages import STATS_KEY
    cache.delete(STATS_KEY)
