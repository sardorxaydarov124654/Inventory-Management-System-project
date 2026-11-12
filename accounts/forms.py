from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .backends import find_user
from .mixins import StyledFormMixin
from .models import Store, UserProfile

User = get_user_model()


def unique_email(form, email):
    """Email takrorlanmasligini tekshiradi (katta-kichik harfga qaramasdan)."""
    if email and User.objects.filter(email__iexact=email).exclude(pk=form.instance.pk).exists():
        raise forms.ValidationError(_("Bu email bilan foydalanuvchi allaqachon mavjud."))
    return email


# ---------------------------------------------------------------- Kirish
class LoginForm(StyledFormMixin, AuthenticationForm):
    """Login yoki email + parol. Pending / Rejected akkauntlar uchun tushunarli xabar ko'rsatadi."""
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("Login yoki parol noto‘g‘ri."),
        "inactive": _("Hisobingiz faol emas."),
        "pending": _("Arizangiz hali ko‘rib chiqilmoqda. Administrator tasdiqlagach, tizimga kira olasiz."),
        "rejected": _("Arizangiz administrator tomonidan rad etilgan. Batafsil ma’lumot uchun administrator bilan bog‘laning."),
    }

    def clean(self):
        username, password = self.cleaned_data.get("username"), self.cleaned_data.get("password")
        if username and password:
            user = find_user(username)
            # Holat faqat parol to'g'ri bo'lganda ko'rsatiladi (akkaunt mavjudligi oshkor bo'lmasligi uchun)
            if user and not user.is_active and user.check_password(password):
                self.confirm_login_allowed(user)
        return super().clean()

    def confirm_login_allowed(self, user):
        profile = getattr(user, "profile", None)
        status = profile.status if profile else UserProfile.APPROVED
        if not user.is_superuser and status in (UserProfile.PENDING, UserProfile.REJECTED):
            raise forms.ValidationError(self.error_messages[status], code=status)
        super().confirm_login_allowed(user)


# ------------------------------------------------------ Ro'yxatdan o'tish
class RegistrationForm(StyledFormMixin, UserCreationForm):
    """Manager yoki Employee sifatida ro'yxatdan o'tish.
    Manager: do'kon / biznes nomi shart, ariza administrator tomonidan tasdiqlanadi.
    Employee: do'kon nomi so'ralmaydi; keyinroq menejer taklifini qabul qilib do'konga qo'shiladi.
    Rol va holat serverda belgilanadi (faqat manager / employee tanlanadi)."""
    ACCOUNT_TYPES = [(UserProfile.MANAGER, _("Manager")), (UserProfile.EMPLOYEE, _("Employee"))]
    account_type = forms.ChoiceField(label=_("Hisob turi"), choices=ACCOUNT_TYPES, widget=forms.RadioSelect,
                                     initial=UserProfile.MANAGER)
    business_name = forms.CharField(label=_("Do‘kon / biznes nomi"), max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        labels = {"first_name": _("Ism"), "last_name": _("Familiya"), "username": _("Login"), "email": _("Email")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True
        self.fields["password1"].label = _("Parol")
        self.fields["password2"].label = _("Parolni takrorlang")
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""
        self.order_fields(["account_type", "first_name", "last_name", "username", "email", "business_name",
                           "password1", "password2"])

    def clean_email(self):
        return unique_email(self, self.cleaned_data.get("email", "").strip())

    def clean(self):
        data = super().clean()
        if data.get("account_type") == UserProfile.MANAGER and not (data.get("business_name") or "").strip():
            self.add_error("business_name", _("Do‘kon / biznes nomini kiriting."))
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = user.is_superuser = False
        is_manager = self.cleaned_data["account_type"] == UserProfile.MANAGER
        user.is_active = not is_manager  # manager tasdiqlanmaguncha login qila olmaydi
        user.save()
        profile, _created = UserProfile.objects.get_or_create(user=user)
        if is_manager:
            profile.role, profile.status = UserProfile.MANAGER, UserProfile.PENDING
            profile.store = Store.objects.create(name=self.cleaned_data["business_name"].strip())
        else:  # Employee: do'kon yo'q, tasdiq shart emas
            profile.role, profile.status, profile.store = UserProfile.EMPLOYEE, UserProfile.APPROVED, None
        profile.save()
        return user


# ------------------------------------------------------ Foydalanuvchilar (admin)
class UserForm(StyledFormMixin, forms.ModelForm):
    """Administrator uchun: har qanday foydalanuvchini yaratish / tahrirlash."""
    password = forms.CharField(
        label=_("Parol"), widget=forms.PasswordInput(render_value=False), required=False,
        help_text=_("Tahrirlashda bo‘sh qoldirsangiz, parol o‘zgarmaydi."),
    )
    role = forms.ChoiceField(label=_("Rol"), choices=UserProfile.ROLE_CHOICES)
    store = forms.ModelChoiceField(label=_("Do‘kon"), queryset=Store.objects.all(), required=False)
    phone = forms.CharField(label=_("Telefon"), required=False)
    language = forms.ChoiceField(label=_("Til"), choices=[("", "—")] + list(settings.LANGUAGES), required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        labels = {"username": _("Login"), "first_name": _("Ism"), "last_name": _("Familiya"),
                  "email": _("Email"), "is_active": _("Faol")}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile, _created = UserProfile.objects.get_or_create(user=self.instance)
            self.fields["role"].initial = profile.role
            self.fields["phone"].initial = profile.phone
            self.fields["language"].initial = profile.language
            self.fields["store"].initial = profile.store_id
        else:
            self.fields["password"].required = True
            self.fields["is_active"].initial = True

    def clean_email(self):
        return unique_email(self, self.cleaned_data.get("email", "").strip())

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def clean(self):
        data = super().clean()
        if data.get("role") in (UserProfile.MANAGER, UserProfile.EMPLOYEE) and not data.get("store"):
            self.add_error("store", _("Menejer va xodim uchun do‘kon tanlash shart."))
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        role = self.cleaned_data["role"]
        if role == UserProfile.ADMIN:
            user.is_staff = True
        user.save()
        profile, _created = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.store = None if role == UserProfile.ADMIN else self.cleaned_data["store"]
        profile.phone = self.cleaned_data["phone"]
        profile.language = self.cleaned_data["language"]
        if _created:
            profile.status = UserProfile.APPROVED
        profile.save()
        return user
