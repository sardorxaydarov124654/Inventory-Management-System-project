from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("login/", RedirectView.as_view(pattern_name="accounts:login", query_string=True)),  # eski havola
    path("register/", RedirectView.as_view(pattern_name="accounts:register", query_string=True)),
    path("", include("inventory.urls")),
    path("", include("stock.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
