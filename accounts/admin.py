from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UserProfile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_select_related = ("profile",)

    @admin.display(description=_("Rol"))
    def role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, "profile") else "—"

    def get_inline_instances(self, request, obj=None):
        # Yangi foydalanuvchi yaratishda profil signal orqali avtomatik yaratiladi
        return super().get_inline_instances(request, obj) if obj else []


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
