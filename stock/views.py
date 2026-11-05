from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView

from accounts.mixins import ManagerMixin, QueryStringMixin, StaffMixin, get_role, role_required

from .forms import StockInForm, StockOutForm
from .models import Notification, StockIn, StockMovement, StockOut
from .services import cancel_operation, register_stock_in, register_stock_out


class OperationCreateMixin:
    template_name = "form.html"

    def get_initial(self):
        initial = super().get_initial()
        product = self.request.GET.get("product")
        if product and product.isdigit():
            initial["product"] = int(product)
        return initial


class StockInCreateView(ManagerMixin, OperationCreateMixin, FormView):
    form_class = StockInForm
    success_url = reverse_lazy("stock:stockin_list")
    extra_context = {"title": _("Yangi kirim"), "subtitle": _("Omborga kelgan mahsulotni qayd eting")}

    def form_valid(self, form):
        register_stock_in(user=self.request.user, **form.cleaned_data)
        messages.success(self.request, _("Kirim qayd etildi, ombor qoldig‘i yangilandi."))
        return super().form_valid(form)


class StockOutCreateView(StaffMixin, OperationCreateMixin, FormView):
    form_class = StockOutForm
    success_url = reverse_lazy("stock:stockout_list")
    extra_context = {"title": _("Yangi chiqim"), "subtitle": _("Ombordan chiqayotgan mahsulotni qayd eting")}

    def form_valid(self, form):
        try:
            register_stock_out(user=self.request.user, **form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        messages.success(self.request, _("Chiqim qayd etildi, ombor qoldig‘i yangilandi."))
        return super().form_valid(form)


class OperationListView(QueryStringMixin, ListView):
    template_name = "stock/operation_list.html"
    context_object_name = "operations"
    paginate_by = 15
    kind = ""

    def get_queryset(self):
        qs = self.model.objects.select_related("product", "created_by")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q))
        if get_role(self.request.user) == "employee":
            qs = qs.filter(created_by=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kind"] = self.kind
        return ctx


class StockInListView(ManagerMixin, OperationListView):
    model = StockIn
    kind = "in"


class StockOutListView(StaffMixin, OperationListView):
    model = StockOut
    kind = "out"


class MovementListView(StaffMixin, QueryStringMixin, ListView):
    template_name = "stock/movement_list.html"
    context_object_name = "movements"
    paginate_by = 20

    def get_queryset(self):
        qs = StockMovement.objects.select_related("product", "user")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q))
        mtype = self.request.GET.get("type", "")
        if mtype in dict(StockMovement.TYPE_CHOICES):
            qs = qs.filter(movement_type=mtype)
        if get_role(self.request.user) == "employee":
            qs = qs.filter(user=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["type"] = self.request.GET.get("type", "")
        ctx["type_choices"] = StockMovement.TYPE_CHOICES
        return ctx


@require_POST
@role_required("admin", "manager")
def cancel_view(request, kind, pk):
    model = StockIn if kind == "in" else StockOut
    obj = get_object_or_404(model, pk=pk)
    try:
        cancel_operation(obj, request.user)
        messages.success(request, _("Operatsiya bekor qilindi, qoldiq tiklandi."))
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect("stock:stockin_list" if kind == "in" else "stock:stockout_list")


@require_POST
@role_required("admin", "manager", "employee")
def notifications_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)
    target = request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "/"
    return redirect(target)
