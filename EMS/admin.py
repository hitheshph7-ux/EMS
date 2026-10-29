
from django.contrib import admin
from .models import (
    Employee,
    EmployeeAddress,
    EmployeeBankAccount,
    EmployeeDocument,
    EmployeeFamilyMember,
    EmployeeQualification,
    CENCounter,
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cen",
        "full_name",
        "society",
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
        "society",
    )

    search_fields = (
        "cen",
        "full_name",
        "mobile",
        "email",
        "aadhaar",
        "pan",
        "society",
    )

    readonly_fields = (
        "cen",
        "created_at",
        "updated_at",
    )

    ordering = ("id",)


@admin.register(EmployeeAddress)
class EmployeeAddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "address_type",
        "city",
        "district",
        "state",
        "postal_code",
    )

    list_filter = ("address_type", "state", "district")

    search_fields = (
        "employee__cen",
        "employee__full_name",
        "city",
        "district",
        "postal_code",
    )


@admin.register(EmployeeQualification)
class EmployeeQualificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "qualification_type",
        "qualification_name",
        "institution",
        "year_completed",
    )

    list_filter = ("qualification_type", "year_completed")

    search_fields = (
        "employee__cen",
        "employee__full_name",
        "qualification_name",
        "institution",
    )


@admin.register(EmployeeFamilyMember)
class EmployeeFamilyMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "name",
        "relation",
        "date_of_birth",
        "is_dependent",
        "is_nominee",
        "nominee_share",
    )

    list_filter = ("relation", "is_dependent", "is_nominee")

    search_fields = (
        "employee__cen",
        "employee__full_name",
        "name",
        "relation",
    )


@admin.register(EmployeeBankAccount)
class EmployeeBankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "account_holder_name",
        "ifsc",
    )

    search_fields = (
        "employee__cen",
        "employee__full_name",
        "account_holder_name",
        "ifsc",
        "account_number",
    )


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee",
        "document_type",
        "uploaded_by",
        "verified_by",
        "is_verified",
        "uploaded_at",
        "verified_at",
    )

    list_filter = ("document_type", "is_verified")

    search_fields = (
        "employee__cen",
        "employee__full_name",
        "document_type",
    )

    readonly_fields = ("uploaded_at", "verified_at")


@admin.register(CENCounter)
class CENCounterAdmin(admin.ModelAdmin):
    list_display = ("id", "next_number")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
