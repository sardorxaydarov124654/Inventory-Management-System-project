from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/manager/", views.RegisterView.as_view(), name="register_manager"),
    path("manager/pending/", views.PendingView.as_view(), name="pending"),
    path("language/", views.set_language, name="set_language"),
    # admin
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/add/", views.UserCreateView.as_view(), name="user_add"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
    path("users/<int:pk>/toggle/", views.toggle_active, name="user_toggle"),
    # manager: jamoa va takliflar
    path("team/", views.TeamView.as_view(), name="team"),
    path("team/invite/<int:pk>/", views.invite_employee, name="invite"),
    path("team/invitations/<int:pk>/cancel/", views.cancel_invitation, name="invitation_cancel"),
    path("team/members/<int:pk>/remove/", views.remove_member, name="member_remove"),
    # employee: taklifga javob
    path("invitations/<int:pk>/respond/", views.respond_invitation, name="invitation_respond"),
]
