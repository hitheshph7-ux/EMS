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
