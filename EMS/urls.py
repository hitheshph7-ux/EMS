
from django.urls import path
from . import views

app_name = "EMS"

urlpatterns = [

    # ==========================================
    # 1. EMPLOYEE LIST
    # ==========================================

    path(
        "",
        views.employee_list,
        name="home",
    ),

    path(
        "employees/",
        views.employee_list,
        name="employee_list",
    ),

    # ==========================================
    # 2. EMPLOYEE PROFILE
    # ==========================================

    path(
        "employees/<int:employee_id>/",
        views.employee_detail,
        name="employee_detail",
    ),

    # ==========================================
    # 3. EMPLOYEE APIs
    # ==========================================

    path(
        "api/employees/",
        views.employee_api,
        name="employee_api",
    ),

    path(
        "api/employees/<int:employee_id>/",
        views.employee_detail_api,
        name="employee_detail_api",
    ),

    # ==========================================
    # 4. EMPLOYEE ADDRESS MANAGEMENT
    # ==========================================

    path(
        "employees/<int:employee_id>/addresses/add/",
        views.employee_address_add,
        name="employee_address_add",
    ),

]
