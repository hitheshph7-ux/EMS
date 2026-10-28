
from django.urls import path
from . import views

app_name = "EMS"

urlpatterns = [
    path("employees/", views.employee_list, name="employee_list"),
]
