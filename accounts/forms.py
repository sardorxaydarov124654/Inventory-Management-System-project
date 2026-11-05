from django.utils.translation import gettext_lazy as _
from django import forms
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .mixins import StyledFormMixin
from .models import UserProfile

User = get_user_model()


class UserForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(
        label=_("Parol"), widget=forms.PasswordInput(render_value=False), required=False,
        help_text=_("Tahrirlashda boвЂsh qoldirsangiz, parol oвЂzgarmaydi."),
    )
    role = forms.ChoiceField(label=_("Rol"), choices=UserProfile.ROLE_CHOICES)
    phone = forms.CharField(label=_("Telefon"), required=False)
    language = forms.ChoiceField(label=_("Til"), choices=settings.LANGUAGES, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        labels = {
            "username": _("Login"),
            "first_name": _("Ism"),
            "last_name": _("Familiya"),
            "email": _("Email"),
            "is_active": _("Faol"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile, _ = UserProfile.objects.get_or_create(user=self.instance)
            self.fields["role"].initial = profile.role
            self.fields["phone"].initial = profile.phone
            self.fields["language"].initial = profile.language
        else:
            self.fields["password"].required = True
            self.fields["is_active"].initial = True

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data["role"]
        profile.phone = self.cleaned_data["phone"]
        profile.language = self.cleaned_data["language"]
        profile.save()
        return user


class RegisterForm(StyledFormMixin, UserCreationForm):
    """Ommaviy ro'yxatdan o'tish (yangi foydalanuvchi "Xodim" roli bilan yaratiladi)."""
    email = forms.EmailField(label=_("Email"), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        labels = {"username": _("Login"), "first_name": _("Ism"), "last_name": _("Familiya")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = _("Parol")
        self.fields["password2"].label = _("Parolni takrorlang")
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""
