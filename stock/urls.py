from django.urls import path

from . import views

app_name = "stock"

urlpatterns = [
    path("stock-in/", views.StockInListView.as_view(), name="stockin_list"),
    path("stock-in/add/", views.StockInCreateView.as_view(), name="stockin_add"),
    path("stock-out/", views.StockOutListView.as_view(), name="stockout_list"),
    path("stock-out/add/", views.StockOutCreateView.as_view(), name="stockout_add"),
    path("movements/", views.MovementListView.as_view(), name="movement_list"),
    path("cancel/<str:kind>/<int:pk>/", views.cancel_view, name="cancel"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
]
