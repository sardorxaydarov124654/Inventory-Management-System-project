from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

ALL_ROLES = ("admin", "manager", "employee")
MANAGE_ROLES = ("admin", "manager")


def get_role(user):
    """Foydalanuvchi rolini qaytaradi (superuser doim admin). Tasdiqlanmagan akkauntlar roli yo'q."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    if profile is None:
        return "employee"
    return profile.role if profile.status == "approved" else None


def get_store(user):
    """Foydalanuvchining do'koni (admin uchun None)."""
    if not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    return profile.store if profile else None


def scope(qs, user, lookup="store"):
    """Ma'lumotlarni do'konga qarab ajratish: admin hammasini ko'radi, boshqalar faqat o'z do'konini."""
    role = get_role(user)
    if role == "admin":
        return qs
    store = get_store(user)
    if role and store:
        return qs.filter(**{lookup: store})
    return qs.none()


def role_home_url(user):
    """Login'dan keyin rolga qarab yo'naltirish manzili."""
    from django.urls import reverse
    role = get_role(user)
    if role == "admin":
        return reverse("admin:index")
    if role == "manager":
        return reverse("dashboard:manager")
    return reverse("dashboard:employee")


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ALL_ROLES

    def test_func(self):
        return get_role(self.request.user) in self.allowed_roles


class StaffMixin(RoleRequiredMixin):
    allowed_roles = ALL_ROLES


class ManagerMixin(RoleRequiredMixin):
    allowed_roles = MANAGE_ROLES


class AdminMixin(RoleRequiredMixin):
    allowed_roles = ("admin",)


class QueryStringMixin:
    """Paginatsiya havolalarida filtrlarni saqlab qolish uchun."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["qs"] = params.urlencode()
        ctx["q"] = self.request.GET.get("q", "").strip()
        return ctx


class StyledFormMixin:
    """Barcha form maydonlariga CSS klasslarini qo'shadi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "check"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "input select"
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = "input file"
            else:
                widget.attrs["class"] = "input"


class StoreScopedFormMixin(StyledFormMixin):
    """Do'konga bog'langan formalar: faqat o'z do'koni ma'lumotlari tanlanadi, do'kon serverda belgilanadi.
    Admin esa do'konni o'zi tanlaydi."""
    scoped_fields = ()  # masalan ("category", "supplier", "product")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.is_admin = bool(user) and get_role(user) == "admin"
        self.store = None if self.is_admin or not user else get_store(user)
        if "store" in self.fields:
            if self.is_admin:
                self.fields["store"].required = True
            else:
                del self.fields["store"]
                if not self.instance.pk and self.store:
                    self.instance.store = self.store
        for name in self.scoped_fields:
            if name in self.fields and user is not None:
                self.fields[name].queryset = scope(self.fields[name].queryset, user)

    def current_store_id(self, data):
        if self.store:
            return self.store.pk
        chosen = data.get("store")
        return chosen.pk if chosen else getattr(self.instance, "store_id", None)

    def clean(self):
        data = super().clean()
        store_id = self.current_store_id(data)
        for name in self.scoped_fields:
            obj = data.get(name)
            if obj is not None and store_id and getattr(obj, "store_id", store_id) != store_id:
                from django.utils.translation import gettext as _
                self.add_error(name, _("Bu obyekt boshqa do‘konga tegishli."))
        return data
