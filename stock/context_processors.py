from django.conf import settings

from accounts.mixins import get_role


def layout(request):
    """Barcha shablonlar uchun umumiy o'zgaruvchilar."""
    ctx = {
        "SITE_NAME": settings.SITE_NAME,
        "CURRENCY": settings.CURRENCY,
        "ALLOW_REGISTRATION": settings.ALLOW_REGISTRATION,
        "section": request.path.strip("/").split("/")[0],
    }
    user = request.user
    if user.is_authenticated:
        from .models import Notification

        role = get_role(user)
        unread = Notification.objects.filter(is_read=False).select_related("product")
        ctx.update(
            role=role,
            is_admin=role == "admin",
            can_manage=role in ("admin", "manager"),
            unread_count=unread.count(),
            recent_notifications=list(unread[:6]),
        )
    return ctx
