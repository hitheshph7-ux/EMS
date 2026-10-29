from django.urls import path
from . import views

app_name = "EMS"

urlpatterns = [
    path("", views.employee_list, name="home"),
    path("employees/", views.employee_list, name="employee_list"),

    path("api/employees/", views.employee_api, name="employee_api"),
    path(
        "api/employees/<int:employee_id>/",
        views.employee_detail_api,
        name="employee_detail_api",
    ),
]