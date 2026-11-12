"""Muhim amallarni audit tarixiga yozish."""


def audit(user, action, target="", detail="", store=None):
    from .models import AuditLog

    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        store=store, action=action, target=str(target)[:200], detail=str(detail)[:255],
    )
