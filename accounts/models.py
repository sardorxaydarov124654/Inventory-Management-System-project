from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    ROLE_CHOICES = [
        (ADMIN, _("Administrator")),
        (MANAGER, _("Menejer")),
        (EMPLOYEE, _("Xodim")),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(_("Rol"), max_length=10, choices=ROLE_CHOICES, default=EMPLOYEE)
    phone = models.CharField(_("Telefon"), max_length=20, blank=True)
    language = models.CharField(_("Til"), max_length=5, choices=settings.LANGUAGES, blank=True,
                                help_text=_("Tizimga kirganda avtomatik tanlanadigan til."))

    class Meta:
        verbose_name = _("Foydalanuvchi profili")
        verbose_name_plural = _("Foydalanuvchi profillari")

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            role=UserProfile.ADMIN if instance.is_superuser else UserProfile.EMPLOYEE,
        )


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
