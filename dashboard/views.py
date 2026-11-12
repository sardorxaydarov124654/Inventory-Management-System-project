from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import ManagerMixin, RoleRequiredMixin, get_role, get_store, role_home_url, scope
from inventory.models import Category, Product
from inventory.stats import inventory_stats
from stock.models import StockIn, StockMovement, StockOut

from .forms import ReportPeriodForm

MONEY = DecimalField(max_digits=16, decimal_places=2)


def daily_series(days, user):
    """So'nggi `days` kun uchun kunlik kirim/chiqim miqdorlari (Chart.js uchun), faqat o'z do'koni bo'yicha."""
    start = timezone.localdate() - timedelta(days=days - 1)

    def totals(model):
        rows = (scope(model.objects.filter(is_cancelled=False, created_at__date__gte=start), user, "product__store")
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


class RoleHomeView(LoginRequiredMixin, View):
    """"/" — rolga qarab: Admin -> /admin/, Manager -> manager paneli, Employee -> employee paneli."""

    def get(self, request):
        return redirect(role_home_url(request.user))


class DashboardView(TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        employee = get_role(user) == "employee"
        today = timezone.localdate()
        ins = scope(StockIn.objects.filter(is_cancelled=False, created_at__date=today), user, "product__store")
        outs = scope(StockOut.objects.filter(is_cancelled=False, created_at__date=today), user, "product__store")
        if employee:  # xodim faqat o'z chiqimini ko'radi
            outs = outs.filter(created_by=user)
        products = scope(Product.objects.all(), user)
        movements = scope(StockMovement.objects.select_related("product", "user"), user, "product__store")
        if employee:
            movements = movements.filter(user=user)
        ctx.update(
            stats=inventory_stats(user),
            employee_view=employee,
            today_in=ins.aggregate(t=Sum("quantity"))["t"] or 0,
            today_out=outs.aggregate(t=Sum("quantity"))["t"] or 0,
            inventory_value=products.aggregate(v=Sum(F("quantity") * F("cost_price"), output_field=MONEY))["v"] or 0,
            low_products=products.filter(is_active=True).exclude(quantity__gt=F("min_quantity")).order_by("quantity")[:6],
            recent=movements[:8],
        )
        if not employee:
            ctx["chart"] = daily_series(7, user)
        return ctx


class ManagerDashboardView(ManagerMixin, DashboardView):
    """Manager (va admin) paneli: to'liq statistika va grafik."""


class EmployeeDashboardView(RoleRequiredMixin, DashboardView):
    """Employee paneli: cheklangan ko'rinish (moliyaviy ma'lumotlarsiz).
    Do'konga biriktirilmagan bo'lsa — takliflar (Confirm / Reject) ko'rsatiladi."""
    allowed_roles = ("employee",)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["no_store"] = get_store(self.request.user) is None
        ctx["store"] = get_store(self.request.user)
        return ctx


class ReportsView(ManagerMixin, TemplateView):
    template_name = "dashboard/reports.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ReportPeriodForm(self.request.GET)
        days = form.days()
        start = timezone.localdate() - timedelta(days=days - 1)

        user = self.request.user
        ins = scope(StockIn.objects.filter(is_cancelled=False, created_at__date__gte=start), user, "product__store")
        outs = scope(StockOut.objects.filter(is_cancelled=False, created_at__date__gte=start), user, "product__store")
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

        categories = (scope(Category.objects.all(), user)
                      .annotate(v=Sum(F("products__quantity") * F("products__cost_price"), output_field=MONEY))
                      .filter(v__gt=0).order_by("-v"))

        ctx.update(
            period=form.cleaned_data.get("period") or "month" if form.is_valid() else "month",
            periods=ReportPeriodForm.PERIODS,
            in_qty=in_tot["q"] or 0, in_cost=in_tot["c"] or 0,
            out_qty=out_tot["q"] or 0,
            revenue=sale_tot["revenue"] or 0, profit=sale_tot["profit"] or 0,
            inventory_value=scope(Product.objects.all(), user).aggregate(
                v=Sum(F("quantity") * F("cost_price"), output_field=MONEY))["v"] or 0,
            top_products=top,
            least_products=list(by_product.order_by("qty")[:5]),
            profit_rows=list(by_product.order_by("-profit")[:10]),
            chart={
                "series": daily_series(max(days, 7), user),
                "top": {"labels": [r["product__name"] for r in top], "values": [r["qty"] for r in top]},
                "cats": {"labels": [c.name for c in categories], "values": [float(c.v) for c in categories]},
            },
        )
        return ctx
