import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView
from django.views.i18n import set_language as django_set_language

from . import invitations
from .audit import audit
from .forms import LoginForm, RegistrationForm, UserForm
from .languages import VISITOR_COOKIE
from .mixins import AdminMixin, QueryStringMixin, RoleRequiredMixin, get_store, role_home_url, role_required
from .models import LanguageChoice, StoreInvitation, UserProfile

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


def safe_next(request, default):
    target = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return default


# --------------------------------------------------------- Kirish / ro'yxatdan o'tish
class UserLoginView(LoginView):
    """Login yoki email + parol. Muvaffaqiyatli kirgach, rolga qarab tegishli sahifaga yo'naltiradi."""
    template_name = "accounts/auth.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return role_home_url(self.request.user)

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
        ctx.update(mode="login", login_form=ctx["form"], register_form=RegistrationForm())
        return ctx


class RegisterView(FormView):
    """Manager yoki Employee sifatida ro'yxatdan o'tish.
    Manager -> Pending (administrator tasdiqlaydi). Employee -> darhol kiradi, do'konga taklif orqali qo'shiladi."""
    template_name = "accounts/auth.html"
    form_class = RegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if not settings.ALLOW_REGISTRATION:
            raise Http404
        if request.user.is_authenticated:
            return redirect(role_home_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("type") in (UserProfile.MANAGER, UserProfile.EMPLOYEE):
            initial["account_type"] = self.request.GET["type"]
        return initial

    def form_valid(self, form):
        user = form.save()
        profile = UserProfile.objects.get(user=user)  # yangi nusxa (signal keshidagi eskisi emas)
        lang = translation.get_language()
        forget_visitor_vote(self.request)
        profile.language = lang
        profile.save()  # statistikadagi til tanlovini ham yangilaydi
        if profile.role == UserProfile.MANAGER:
            audit(user, "manager_registered", user.get_username(), profile.store.name, store=profile.store)
            self.request.session["pending_application"] = {"name": user.get_full_name() or user.get_username(),
                                                           "store": profile.store.name}
            return apply_language(redirect("accounts:pending"), lang)
        audit(user, "employee_registered", user.get_username())
        login(self.request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(self.request, _("Hisobingiz yaratildi. Menejer sizni do‘koniga taklif qilganda, xabar shu yerda chiqadi."))
        return apply_language(redirect("dashboard:employee"), lang)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(mode="register", register_form=ctx["form"], login_form=AuthenticationForm(self.request),
                   next=self.request.GET.get("next", ""))
        return ctx


class PendingView(TemplateView):
    """Manager arizasi yuborilgandan keyin: tasdiqlash kutilayotgani haqida sahifa."""
    template_name = "accounts/pending.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["application"] = self.request.session.get("pending_application")
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


# ------------------------------------------------ Foydalanuvchilar (faqat admin)
class UserListView(AdminMixin, QueryStringMixin, ListView):
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.select_related("profile", "profile__store").order_by("username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs


class UserFormMixin(AdminMixin):
    form_class = UserForm
    template_name = "form.html"
    success_url = reverse_lazy("accounts:user_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class UserCreateView(UserFormMixin, CreateView):
    extra_context = {"title": _("Yangi foydalanuvchi"), "subtitle": _("Xodim hisobini yarating va rolini belgilang")}

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(self.request.user, "user_created", self.object.get_username(), self.object.profile.get_role_display(),
              store=self.object.profile.store)
        messages.success(self.request, _("Foydalanuvchi qo‘shildi."))
        return response


class UserUpdateView(UserFormMixin, UpdateView):
    model = User
    extra_context = {"title": _("Foydalanuvchini tahrirlash"), "subtitle": _("Ma’lumotlar va rolni o‘zgartiring")}

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(self.request.user, "user_updated", self.object.get_username(), store=self.object.profile.store)
        messages.success(self.request, _("Foydalanuvchi ma’lumotlari saqlandi."))
        return response


@require_POST
@role_required("admin")
def toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, _("O‘zingizning hisobingizni o‘chira olmaysiz."))
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        audit(request.user, "user_toggled", user.get_username(), "active" if user.is_active else "inactive",
              store=user.profile.store)
        messages.success(request, _("Holat o‘zgartirildi."))
    return redirect("accounts:user_list")


# ------------------------------------------------ Jamoa: taklif qilish (manager)
class ManagerOnlyMixin(RoleRequiredMixin):
    allowed_roles = ("manager",)


class TeamView(ManagerOnlyMixin, QueryStringMixin, ListView):
    """Manager: do'kon xodimlari + ro'yxatdan o'tgan Employee larni login bo'yicha qidirib taklif qilish."""
    template_name = "accounts/team.html"
    context_object_name = "candidates"
    paginate_by = 8

    def get_queryset(self):
        qs = invitations.available_employees().select_related("profile").order_by("username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(username__icontains=q)  # login (username) bo'yicha qidirish
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        store = get_store(self.request.user)
        sent = StoreInvitation.objects.filter(store=store).select_related("invited_user")
        ctx.update(
            store=store,
            members=User.objects.filter(profile__store=store, profile__role=UserProfile.EMPLOYEE)
            .select_related("profile").order_by("username"),
            invited_ids=set(sent.filter(status=StoreInvitation.PENDING).values_list("invited_user_id", flat=True)),
            sent=sent.exclude(status=StoreInvitation.CANCELLED)[:10],
            total_available=invitations.available_employees().count(),
        )
        # Manager javoblarni ko'rdi: bildirishnomadan olib tashlanadi
        StoreInvitation.objects.filter(store=store, inviter_seen=False).update(inviter_seen=True)
        return ctx


@require_POST
@role_required("manager")
def invite_employee(request, pk):
    try:
        invitations.send_invitation(request.user, pk)
        messages.success(request, _("Taklif yuborildi. Foydalanuvchi uni o‘z panelida ko‘radi."))
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect(safe_next(request, reverse("accounts:team")))


@require_POST
@role_required("manager")
def cancel_invitation(request, pk):
    inv = get_object_or_404(StoreInvitation, pk=pk, store=get_store(request.user))
    try:
        invitations.cancel_invitation(request.user, inv)
        messages.success(request, _("Taklif bekor qilindi."))
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect("accounts:team")


@require_POST
@role_required("manager")
def remove_member(request, pk):
    employee = get_object_or_404(User, pk=pk, profile__store=get_store(request.user))
    try:
        invitations.remove_member(request.user, employee)
        messages.success(request, _("Xodim do‘kondan chiqarildi."))
    except ValidationError as e:
        messages.error(request, e.messages[0])
    return redirect("accounts:team")


# ------------------------------------------------ Employee: taklifga javob
@require_POST
@role_required("employee")
def respond_invitation(request, pk):
    """Confirm / Reject tugmalari."""
    inv = get_object_or_404(StoreInvitation, pk=pk, invited_user=request.user)
    accept = request.POST.get("action") == "confirm"
    if request.POST.get("action") not in ("confirm", "reject"):
        raise Http404
    try:
        invitations.respond_to_invitation(inv, request.user, accept)
    except ValidationError as e:
        messages.error(request, e.messages[0])
        return redirect(safe_next(request, reverse("dashboard:employee")))
    if accept:
        messages.success(request, _("Siz “%(store)s” do‘koniga qo‘shildingiz.") % {"store": inv.store.name})
        return redirect("dashboard:employee")
    messages.success(request, _("Taklif rad etildi."))
    return redirect(safe_next(request, reverse("dashboard:employee")))
