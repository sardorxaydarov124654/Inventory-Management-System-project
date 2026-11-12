from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


def find_user(identifier):
    """Login (username) yoki email bo'yicha foydalanuvchini topadi."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    user = User.objects.filter(username__iexact=identifier).first()
    if user is None and "@" in identifier:
        matches = list(User.objects.filter(email__iexact=identifier)[:2])
        user = matches[0] if len(matches) == 1 else None
    return user


class EmailOrUsernameBackend(ModelBackend):
    """Tizimga login yoki email + parol orqali kirish."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = find_user(username)
        return super().authenticate(request, username=user.get_username() if user else username,
                                    password=password, **kwargs)
