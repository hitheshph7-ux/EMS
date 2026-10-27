
from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cen",
        "full_name",
        "date_of_birth",
        "gender",
        "mobile",
        "email",
        "status",
    )

    list_filter = (
        "status",
        "gender",
        "marital_status",
    )

    search_fields = (
        "full_name",
        "mobile",
        "email",
        "cen",
    )

    readonly_fields = (
        "cen",
        "created_at",
        "updated_at",
    )
