from django.contrib import admin

from EMS.models import (
    ACRRecord,
    AuditEntry,
    Designation,
    DigitalSignature,
    EmployeeServiceProfile,
    EmployeeServiceSnapshot,
    PayScale,
    ProbationRecord,
    RecruitmentRecord,
    ScannedServiceBook,
    ServiceEvent,
    TransferWorkflow,
)


class NoDeleteModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Designation)
class DesignationAdmin(NoDeleteModelAdmin):
    list_display = ("code", "name", "level", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(PayScale)
class PayScaleAdmin(NoDeleteModelAdmin):
    list_display = (
        "code",
        "min_pay",
        "max_pay",
        "revision_order",
        "effective_date",
        "is_active",
    )
    list_filter = ("effective_date", "is_active")
    search_fields = ("code",)
    ordering = ("revision_order", "effective_date", "code")


@admin.register(EmployeeServiceProfile)
class EmployeeServiceProfileAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "full_name", "department", "email", "phone")
    search_fields = ("employee_cen", "full_name", "department")


@admin.register(ServiceEvent)
class ServiceEventAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "event_type", "effective_date", "status", "is_locked")
    list_filter = ("event_type", "status", "is_locked")
    search_fields = ("employee_cen",)
    readonly_fields = tuple(field.name for field in ServiceEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmployeeServiceSnapshot)
class EmployeeServiceSnapshotAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "designation_name", "current_pay", "society_cen", "as_of_date")
    search_fields = ("employee_cen", "society_cen")
    readonly_fields = tuple(field.name for field in EmployeeServiceSnapshot._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProbationRecord)
class ProbationRecordAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "start_date", "expected_end_date", "status")
    list_filter = ("status",)
    search_fields = ("employee_cen",)


@admin.register(TransferWorkflow)
class TransferWorkflowAdmin(NoDeleteModelAdmin):
    list_display = ("event", "from_society_cen", "to_society_cen", "status")
    list_filter = ("status",)
    readonly_fields = tuple(field.name for field in TransferWorkflow._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RecruitmentRecord)
class RecruitmentRecordAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "recruitment_date", "recruitment_mode", "reference_number")
    search_fields = ("employee_cen", "reference_number")


@admin.register(ScannedServiceBook)
class ScannedServiceBookAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "title", "document_date", "uploaded_at")
    search_fields = ("employee_cen", "title")
    readonly_fields = ("sha256", "uploaded_at")


@admin.register(ACRRecord)
class ACRRecordAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "period_start", "period_end", "rating", "is_locked")
    list_filter = ("is_locked",)
    search_fields = ("employee_cen",)


@admin.register(AuditEntry)
class AuditEntryAdmin(NoDeleteModelAdmin):
    list_display = ("employee_cen", "object_type", "action", "actor", "occurred_at")
    list_filter = ("object_type", "action")
    search_fields = ("employee_cen", "object_id")
    readonly_fields = tuple(field.name for field in AuditEntry._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DigitalSignature)
class DigitalSignatureAdmin(NoDeleteModelAdmin):
    list_display = ("event", "provider", "signer", "signed_at")
    readonly_fields = tuple(field.name for field in DigitalSignature._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False
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
