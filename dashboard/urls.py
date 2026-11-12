from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.RoleHomeView.as_view(), name="home"),
    path("manager/dashboard/", views.ManagerDashboardView.as_view(), name="manager"),
    path("employee/dashboard/", views.EmployeeDashboardView.as_view(), name="employee"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
]
