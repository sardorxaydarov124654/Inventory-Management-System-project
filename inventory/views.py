from django.utils.translation import gettext_lazy as _
import csv

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import ManagerMixin, QueryStringMixin, StaffMixin

from .forms import CategoryForm, ProductForm, SupplierForm
from .models import Category, Product, Supplier
from .stats import inventory_stats


class SafeDeleteView(ManagerMixin, DeleteView):
    """Bog'langan ma'lumotlari bor yozuvni o'chirishga yo'l qo'ymaydi."""
    template_name = "confirm_delete.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, _("Bu yozuvga bog‘langan ma’lumotlar bor, uni o‘chirib bo‘lmaydi. "
                                         "Mahsulotni o‘chirish o‘rniga nofaol qiling."))
            return redirect(self.success_url)
        messages.success(self.request, _("Yozuv o‘chirildi."))
        return response


# ---------------------------------------------------------------- Products
def filtered_products(request):
    qs = Product.objects.select_related("category", "supplier")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(sku__icontains=q)
            | Q(category__name__icontains=q) | Q(supplier__company_name__icontains=q)
        )
    category = request.GET.get("category", "")
    if category.isdigit():
        qs = qs.filter(category_id=category)
    return qs.filter_status(request.GET.get("status", ""))


class ProductListView(StaffMixin, QueryStringMixin, ListView):
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    paginate_by = 8

    def get_queryset(self):
        return filtered_products(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            stats=inventory_stats(),
            status=self.request.GET.get("status", ""),
            categories=Category.objects.all(),
            category=self.request.GET.get("category", ""),
        )
        return ctx


class ProductExportView(StaffMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="mahsulotlar.csv"'
        response.write("\ufeff")  # Excel uchun BOM
        writer = csv.writer(response)
        writer.writerow([_("Nomi"), "SKU", _("Kategoriya"), _("Yetkazib beruvchi"), _("Miqdor"), _("Birlik"),
                         _("Minimal zaxira"), _("Sotuv narxi"), _("Xarid narxi"), _("Holat")])
        for p in filtered_products(request):
            writer.writerow([p.name, p.sku, p.category or "", p.supplier or "", p.quantity,
                             p.get_unit_display(), p.min_quantity, p.price, p.cost_price, p.status_label])
        return response


class ProductCreateView(ManagerMixin, SuccessMessageMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:product_list")
    success_message = _("Mahsulot qo‘shildi. Zaxira qo‘shish uchun “Kirim” bo‘limidan foydalaning.")
    extra_context = {"title": _("Yangi mahsulot"), "subtitle": _("Mahsulot ma’lumotlarini kiriting")}


class ProductUpdateView(ManagerMixin, SuccessMessageMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:product_list")
    success_message = _("Mahsulot saqlandi.")
    extra_context = {"title": _("Mahsulotni tahrirlash"), "subtitle": _("Ma’lumotlarni yangilang")}


class ProductDeleteView(SafeDeleteView):
    model = Product
    success_url = reverse_lazy("inventory:product_list")


# -------------------------------------------------------------- Categories
class CategoryListView(ManagerMixin, QueryStringMixin, ListView):
    template_name = "inventory/category_list.html"
    context_object_name = "categories"
    paginate_by = 15

    def get_queryset(self):
        qs = Category.objects.annotate(product_count=Count("products")).order_by("name")
        q = self.request.GET.get("q", "").strip()
        return qs.filter(name__icontains=q) if q else qs


class CategoryCreateView(ManagerMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = _("Kategoriya qo‘shildi.")
    extra_context = {"title": _("Yangi kategoriya"), "subtitle": _("Mahsulotlarni guruhlash uchun")}


class CategoryUpdateView(ManagerMixin, SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = _("Kategoriya saqlandi.")
    extra_context = {"title": _("Kategoriyani tahrirlash"), "subtitle": ""}


class CategoryDeleteView(SafeDeleteView):
    model = Category
    success_url = reverse_lazy("inventory:category_list")


# --------------------------------------------------------------- Suppliers
class SupplierListView(ManagerMixin, QueryStringMixin, ListView):
    template_name = "inventory/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 15

    def get_queryset(self):
        qs = Supplier.objects.annotate(product_count=Count("products", distinct=True)).order_by("company_name")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(company_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
        return qs


class SupplierDetailView(ManagerMixin, DetailView):
    model = Supplier
    template_name = "inventory/supplier_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["products"] = self.object.products.all()
        ctx["history"] = self.object.stock_ins.select_related("product", "created_by")[:20]
        return ctx


class SupplierCreateView(ManagerMixin, SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:supplier_list")
    success_message = _("Yetkazib beruvchi qo‘shildi.")
    extra_context = {"title": _("Yangi yetkazib beruvchi"), "subtitle": _("Kompaniya ma’lumotlari")}


class SupplierUpdateView(ManagerMixin, SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "form.html"
    success_url = reverse_lazy("inventory:supplier_list")
    success_message = _("Ma’lumotlar saqlandi.")
    extra_context = {"title": _("Yetkazib beruvchini tahrirlash"), "subtitle": ""}


class SupplierDeleteView(SafeDeleteView):
    model = Supplier
    success_url = reverse_lazy("inventory:supplier_list")
