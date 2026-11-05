from datetime import timedelta

from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.mixins import ManagerMixin, StaffMixin, get_role
from inventory.models import Category, Product
from inventory.stats import inventory_stats
from stock.models import StockIn, StockMovement, StockOut

from .forms import ReportPeriodForm

MONEY = DecimalField(max_digits=16, decimal_places=2)


def daily_series(days):
    """So'nggi `days` kun uchun kunlik kirim/chiqim miqdorlari (Chart.js uchun)."""
    start = timezone.localdate() - timedelta(days=days - 1)

    def totals(model):
        rows = (model.objects.filter(is_cancelled=False, created_at__date__gte=start)
                .annotate(d=TruncDate("created_at")).values("d")
                .annotate(t=Sum("quantity")).order_by("d"))
        return {r["d"]: r["t"] for r in rows}

    ins, outs = totals(StockIn), totals(StockOut)
    dates = [start + timedelta(days=i) for i in range(days)]
    return {
        "labels": [d.strftime("%d.%m") for d in dates],
        "ins": [ins.get(d, 0) for d in dates],
        "outs": [outs.get(d, 0) for d in dates],
    }


class HomeView(StaffMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        ctx["stats"] = inventory_stats()
        ctx["today_in"] = StockIn.objects.filter(is_cancelled=False, created_at__date=today).aggregate(
            t=Sum("quantity"))["t"] or 0
        ctx["today_out"] = StockOut.objects.filter(is_cancelled=False, created_at__date=today).aggregate(
            t=Sum("quantity"))["t"] or 0
        ctx["total_units"] = Product.objects.aggregate(t=Sum("quantity"))["t"] or 0
        ctx["inventory_value"] = Product.objects.aggregate(
            v=Sum(F("quantity") * F("cost_price"), output_field=MONEY))["v"] or 0
        ctx["low_products"] = Product.objects.filter(is_active=True).exclude(
            quantity__gt=F("min_quantity")).order_by("quantity")[:6]
        movements = StockMovement.objects.select_related("product", "user")
        if get_role(self.request.user) == "employee":
            movements = movements.filter(user=self.request.user)
        ctx["recent"] = movements[:8]
        ctx["chart"] = daily_series(7)
        return ctx


class ReportsView(ManagerMixin, TemplateView):
    template_name = "dashboard/reports.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ReportPeriodForm(self.request.GET)
        days = form.days()
        start = timezone.localdate() - timedelta(days=days - 1)

        ins = StockIn.objects.filter(is_cancelled=False, created_at__date__gte=start)
        outs = StockOut.objects.filter(is_cancelled=False, created_at__date__gte=start)
        sales = outs.filter(reason=StockOut.SALE)

        in_tot = ins.aggregate(q=Sum("quantity"), c=Sum(F("quantity") * F("purchase_price"), output_field=MONEY))
        out_tot = outs.aggregate(q=Sum("quantity"))
        sale_tot = sales.aggregate(
            revenue=Sum(F("quantity") * F("unit_price"), output_field=MONEY),
            profit=Sum((F("unit_price") - F("product__cost_price")) * F("quantity"), output_field=MONEY),
        )

        by_product = (sales.order_by().values("product__name", "product__unit")
                      .annotate(qty=Sum("quantity"),
                                revenue=Sum(F("quantity") * F("unit_price"), output_field=MONEY),
                                profit=Sum((F("unit_price") - F("product__cost_price")) * F("quantity"),
                                           output_field=MONEY)))
        top = list(by_product.order_by("-qty")[:5])

        categories = (Category.objects
                      .annotate(v=Sum(F("products__quantity") * F("products__cost_price"), output_field=MONEY))
                      .filter(v__gt=0).order_by("-v"))

        ctx.update(
            period=form.cleaned_data.get("period") or "month" if form.is_valid() else "month",
            periods=ReportPeriodForm.PERIODS,
            in_qty=in_tot["q"] or 0, in_cost=in_tot["c"] or 0,
            out_qty=out_tot["q"] or 0,
            revenue=sale_tot["revenue"] or 0, profit=sale_tot["profit"] or 0,
            inventory_value=Product.objects.aggregate(
                v=Sum(F("quantity") * F("cost_price"), output_field=MONEY))["v"] or 0,
            top_products=top,
            least_products=list(by_product.order_by("qty")[:5]),
            profit_rows=list(by_product.order_by("-profit")[:10]),
            chart={
                "series": daily_series(max(days, 7)),
                "top": {"labels": [r["product__name"] for r in top], "values": [r["qty"] for r in top]},
                "cats": {"labels": [c.name for c in categories], "values": [float(c.v) for c in categories]},
            },
        )
        return ctx
