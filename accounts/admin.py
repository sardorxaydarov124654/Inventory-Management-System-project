from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .audit import audit
from .models import AuditLog, ManagerApplication, Store, StoreInvitation, UserProfile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = "user"
    fields = ("role", "store", "phone", "language", "status")
    readonly_fields = ("status",)  # holat faqat "Manager arizalari" bo'limidan o'zgartiriladi


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "role", "store", "is_active")
    list_select_related = ("profile", "profile__store")

    @admin.display(description=_("Rol"))
    def role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, "profile") else "—"

    @admin.display(description=_("Do‘kon"))
    def store(self, obj):
        return obj.profile.store if hasattr(obj, "profile") else "—"

    def get_inline_instances(self, request, obj=None):
        # Yangi foydalanuvchi yaratishda profil signal orqali avtomatik yaratiladi
        return super().get_inline_instances(request, obj) if obj else []


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(ManagerApplication)
class ManagerApplicationAdmin(admin.ModelAdmin):
    """Manager arizalari: status bo'yicha filtr, Approve / Reject amallari. Faqat Manager roli ko'rinadi."""
    list_display = ("user", "full_name", "email", "store", "status", "applied_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "store__name")
    list_select_related = ("user", "store", "reviewed_by")
    actions = ["approve", "reject"]
    readonly_fields = ("user", "role", "store", "status", "reviewed_by", "reviewed_at", "phone", "language")
    fields = readonly_fields

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=UserProfile.MANAGER)

    def has_add_permission(self, request):
        return False

    @admin.display(description=_("Ism"))
    def full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

    @admin.display(description=_("Ariza sanasi"), ordering="user__date_joined")
    def applied_at(self, obj):
        return obj.user.date_joined

    def _review(self, request, queryset, status, active):
        count = 0
        for profile in queryset.filter(role=UserProfile.MANAGER).select_related("user", "store"):
            profile.status, profile.reviewed_by, profile.reviewed_at = status, request.user, timezone.now()
            profile.save()
            profile.user.is_active = active
            profile.user.save(update_fields=["is_active"])
            audit(request.user, f"manager_{status}", profile.user.get_username(), profile.store, store=profile.store)
            count += 1
        return count

    @admin.action(description=_("Tanlangan arizalarni tasdiqlash (Approve)"))
    def approve(self, request, queryset):
        n = self._review(request, queryset, UserProfile.APPROVED, True)
        self.message_user(request, _("Tasdiqlandi: %(n)s ta ariza.") % {"n": n}, messages.SUCCESS)

    @admin.action(description=_("Tanlangan arizalarni rad etish (Reject)"))
    def reject(self, request, queryset):
        n = self._review(request, queryset, UserProfile.REJECTED, False)
        self.message_user(request, _("Rad etildi: %(n)s ta ariza.") % {"n": n}, messages.WARNING)


@admin.register(StoreInvitation)
class StoreInvitationAdmin(admin.ModelAdmin):
    list_display = ("store", "invited_user", "invited_by", "status", "created_at", "responded_at")
    list_filter = ("status", "store")
    search_fields = ("invited_user__username", "store__name")

    def has_add_permission(self, request):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "user", "target", "detail", "store")
    list_filter = ("action", "store")
    search_fields = ("target", "detail", "user__username")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
