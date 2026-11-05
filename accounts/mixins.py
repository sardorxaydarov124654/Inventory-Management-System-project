from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

ALL_ROLES = ("admin", "manager", "employee")
MANAGE_ROLES = ("admin", "manager")


def get_role(user):
    """Foydalanuvchi rolini qaytaradi (superuser doim admin)."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else "employee"


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
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "check"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "input select"
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = "input file"
            else:
                widget.attrs["class"] = "input"
