from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import Category, Product


def inventory_stats():
    """4 ta yuqori kartochka uchun statistikalar."""
    products = Product.objects.all()
    total = products.count()
    low = products.low().count()
    out = products.out().count()
    top = Category.objects.annotate(n=Count("products")).order_by("-n", "name").first()
    week_ago = timezone.now() - timedelta(days=7)

    def pct(x):
        return round(x * 100 / total) if total else 0

    return {
        "total": total,
        "low": low,
        "out": out,
        "low_pct": pct(low),
        "out_pct": pct(out),
        "new_week": products.filter(created_at__gte=week_ago).count(),
        "top_name": top.name if top else "вЂ”",
        "top_count": top.n if top else 0,
    }
