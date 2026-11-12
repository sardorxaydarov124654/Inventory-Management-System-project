from django.conf import settings
from django.urls import reverse

from accounts.mixins import get_role, get_store, scope


def nav_section(path):
    """Chap menyuda qaysi bo'lim faol ekanini aniqlaydi."""
    parts = path.strip("/").split("/")
    if parts[0] in ("", "manager", "employee"):
        return ""  # boshqaruv paneli
    if parts[0] == "accounts":
        return parts[1] if len(parts) > 1 and parts[1] in ("users", "team") else "accounts"
    return parts[0]


def layout(request):
    """Barcha shablonlar uchun umumiy o'zgaruvchilar."""
    ctx = {
        "SITE_NAME": settings.SITE_NAME,
        "CURRENCY": settings.CURRENCY,
        "ALLOW_REGISTRATION": settings.ALLOW_REGISTRATION,
        "section": nav_section(request.path),
    }
    user = request.user
    if user.is_authenticated:
        from .models import Notification

        role = get_role(user)
        unread = scope(Notification.objects.filter(is_read=False).select_related("product"), user, "product__store")
        ctx.update(
            role=role,
            is_admin=role == "admin",
            can_manage=role in ("admin", "manager"),
            has_store=role == "admin" or get_store(user) is not None,
            recent_notifications=list(unread[:6]),
            dashboard_url=reverse("dashboard:employee" if role == "employee" else "dashboard:manager"),
        )
        from accounts.models import StoreInvitation
        alerts = unread.count()
        invites, updates = [], []
        if role == "employee":  # Employee uchun: do'konga takliflar (Confirm / Reject)
            invites = list(StoreInvitation.objects.filter(invited_user=user, status=StoreInvitation.PENDING)
                           .select_related("store", "invited_by"))
        elif role == "manager" and get_store(user):  # Manager uchun: Employee javoblari
            updates = list(StoreInvitation.objects.filter(store=get_store(user), inviter_seen=False)
                           .exclude(status__in=[StoreInvitation.PENDING, StoreInvitation.CANCELLED])
                           .select_related("invited_user"))
        ctx.update(pending_invitations=invites, inviter_updates=updates,
                   unread_count=alerts + len(invites) + len(updates), alert_count=alerts)
        if role == "admin":
            from accounts.models import UserProfile
            ctx["pending_applications"] = UserProfile.objects.filter(
                role=UserProfile.MANAGER, status=UserProfile.PENDING).count()
    return ctx
