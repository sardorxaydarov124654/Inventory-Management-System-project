from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth import get_user_model
import uuid

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.http import Http404
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.i18n import set_language as django_set_language
from django.views.generic import FormView
from django.db.models import Q
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from .forms import RegisterForm, UserForm
from .languages import VISITOR_COOKIE
from .models import LanguageChoice, UserProfile
from .mixins import AdminMixin, QueryStringMixin, role_required

User = get_user_model()


def visitor_id(request):
    return request.COOKIES.get(VISITOR_COOKIE) or uuid.uuid4().hex


def forget_visitor_vote(request):
    """Mehmon hisob yaratgach yoki kirgach, uning tanlovi foydalanuvchi tanloviga qo'shiladi (ikki marta sanalmaydi)."""
    vid = request.COOKIES.get(VISITOR_COOKIE)
    if vid:
        LanguageChoice.objects.filter(voter=f"v{vid}").delete()


def apply_language(response, lang):
    """Tanlangan tilni cookie ga yozadi (keyingi so'rovlarda LocaleMiddleware o'qiydi)."""
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, max_age=settings.LANGUAGE_COOKIE_AGE,
                        samesite=settings.LANGUAGE_COOKIE_SAMESITE, secure=settings.LANGUAGE_COOKIE_SECURE)
    return response


class UserLoginView(LoginView):
    template_name = "accounts/auth.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Kirishda foydalanuvchining saqlangan tili qo'llanadi; bo'lmasa joriy til saqlanadi."""
        response = super().form_valid(form)
        forget_visitor_vote(self.request)
        profile, _created = UserProfile.objects.get_or_create(user=self.request.user)
        if not profile.language:
            profile.language = translation.get_language()
            profile.save(update_fields=["language"])
        return apply_language(response, profile.language)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(mode="login", login_form=ctx["form"], register_form=RegisterForm())
        return ctx


class RegisterView(FormView):
    template_name = "accounts/auth.html"
    form_class = RegisterForm
    success_url = reverse_lazy("dashboard:home")

    def dispatch(self, request, *args, **kwargs):
        if not settings.ALLOW_REGISTRATION:
            raise Http404
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        lang = translation.get_language()
        forget_visitor_vote(self.request)
        UserProfile.objects.update_or_create(user=user, defaults={"language": lang})
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, _("Hisobingiz yaratildi. Xush kelibsiz!"))
        return apply_language(redirect(self.get_success_url()), lang)

    def get_success_url(self):
        target = self.request.POST.get("next") or self.request.GET.get("next") or ""
        if target and url_has_allowed_host_and_scheme(target, allowed_hosts={self.request.get_host()}):
            return target
        return str(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(mode="register", register_form=ctx["form"], login_form=AuthenticationForm(self.request),
                   next=self.request.POST.get("next") or self.request.GET.get("next") or "")
        return ctx


@require_POST
def set_language(request):
    """Tilni almashtiradi; tizimga kirgan bo'lsa, profilga ham saqlaydi."""
    response = django_set_language(request)
    lang = request.POST.get("language", "")
    if lang in dict(settings.LANGUAGES):
        if request.user.is_authenticated:
            UserProfile.objects.update_or_create(user=request.user, defaults={"language": lang})
        else:  # mehmon (ro'yxatdan o'tayotgan) tanlovi ham statistikaga kiradi
            vid = visitor_id(request)
            LanguageChoice.objects.update_or_create(voter=f"v{vid}", defaults={"language": lang})
            response.set_cookie(VISITOR_COOKIE, vid, max_age=settings.LANGUAGE_COOKIE_AGE, httponly=True, samesite="Lax")
    return response


class UserListView(AdminMixin, QueryStringMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.select_related("profile").order_by("username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs


class UserCreateView(AdminMixin, SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = "form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = _("Foydalanuvchi qo‘shildi.")
    extra_context = {"title": _("Yangi foydalanuvchi"), "subtitle": _("Xodim hisobini yarating va rolini belgilang")}


class UserUpdateView(AdminMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = "form.html"
    success_url = reverse_lazy("accounts:user_list")
    success_message = _("Foydalanuvchi ma’lumotlari saqlandi.")
    extra_context = {"title": _("Foydalanuvchini tahrirlash"), "subtitle": _("Ma’lumotlar va rolni o‘zgartiring")}


@require_POST
@role_required("admin")
def toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, _("O‘zingizning hisobingizni o‘chira olmaysiz."))
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, _("Holat o‘zgartirildi."))
    return redirect("accounts:user_list")
