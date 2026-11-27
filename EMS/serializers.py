from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from EMS.models import (
    ACRRecord,
    AuditEntry,
    Designation,
    EmployeeServiceProfile,
    EmployeeServiceSnapshot,
    PayScale,
    ProbationRecord,
    RecruitmentRecord,
    ScannedServiceBook,
    ServiceEvent,
    TransferWorkflow,
)


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ("id", "code", "name", "description", "level", "is_active")
        read_only_fields = ("id",)


class PayScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayScale
        fields = (
            "id", "code", "min_pay", "max_pay", "increment_steps",
            "revision_order", "effective_date", "is_active",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        min_pay = attrs.get("min_pay", getattr(self.instance, "min_pay", None))
        max_pay = attrs.get("max_pay", getattr(self.instance, "max_pay", None))
        if min_pay is not None and max_pay is not None and min_pay > max_pay:
            raise serializers.ValidationError(
                {"max_pay": "Maximum pay must be greater than or equal to minimum pay."}
            )
        return attrs


class EmployeeServiceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeServiceProfile
        fields = (
            "id", "employee_cen", "full_name", "date_of_birth", "email",
            "phone", "department", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ServiceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceEvent
        fields = (
            "id", "employee_cen", "event_type", "effective_date", "payload",
            "designation", "pay_scale", "status", "is_locked", "created_by", "approved_by", "created_at",
            "submitted_at", "approved_at", "cancelled_at", "cancelled_on",
            "cancellation_reason",
        )
        read_only_fields = (
            "id", "designation", "pay_scale", "status", "is_locked", "created_by", "approved_by", "created_at",
            "submitted_at", "approved_at", "cancelled_at", "cancelled_on",
            "cancellation_reason",
        )

    def validate(self, attrs):
        event = ServiceEvent(**attrs)
        if self.instance:
            event = self.instance
            for key, value in attrs.items():
                setattr(event, key, value)
        try:
            event.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


class EmployeeServiceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeServiceSnapshot
        fields = (
            "id", "employee_cen", "designation", "designation_code", "designation_name",
            "designation_description", "designation_level", "pay_scale", "pay_scale_code",
            "pay_scale_min_pay", "pay_scale_max_pay", "pay_scale_revision_order",
            "pay_scale_effective_date", "pay_scale_increment_steps", "current_pay", "society_cen",
            "employment_status", "probation_status", "as_of_date", "rebuilt_at",
        )
        read_only_fields = fields


class ProbationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProbationRecord
        fields = (
            "id", "employee_cen", "start_date", "expected_end_date", "actual_end_date",
            "status", "extension_reason", "confirmation_event", "created_by", "created_at",
        )
        read_only_fields = ("id", "status", "actual_end_date", "confirmation_event", "created_by", "created_at")

    def validate(self, attrs):
        record = self.instance or ProbationRecord()
        for key, value in attrs.items():
            setattr(record, key, value)
        try:
            record.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


class TransferWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferWorkflow
        fields = (
            "id", "event", "from_society_cen", "to_society_cen", "status",
            "relieved_at", "relieved_by", "accepted_at", "accepted_by",
        )
        read_only_fields = fields


class RecruitmentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentRecord
        fields = (
            "id", "employee_cen", "recruitment_date", "recruitment_mode",
            "reference_number", "details", "appointment_event", "created_by", "created_at",
        )
        read_only_fields = ("id", "created_by", "created_at")

    def validate(self, attrs):
        event = attrs.get("appointment_event", getattr(self.instance, "appointment_event", None))
        cen = attrs.get("employee_cen", getattr(self.instance, "employee_cen", None))
        if event and (event.employee_cen != cen or event.event_type != "APPOINTMENT"):
            raise serializers.ValidationError(
                {"appointment_event": "Recruitment must refer to this employee's appointment event."}
            )
        return attrs


class ScannedServiceBookSerializer(serializers.ModelSerializer):
    file = serializers.FileField(use_url=False)

    class Meta:
        model = ScannedServiceBook
        fields = (
            "id", "employee_cen", "title", "document_date", "file",
            "sha256", "uploaded_by", "uploaded_at",
        )
        read_only_fields = ("id", "sha256", "uploaded_by", "uploaded_at")


class ACRRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ACRRecord
        fields = (
            "id", "employee_cen", "period_start", "period_end", "rating",
            "details", "is_locked", "created_by", "created_at",
        )
        read_only_fields = ("id", "is_locked", "created_by", "created_at")

    def validate(self, attrs):
        record = self.instance or ACRRecord()
        for key, value in attrs.items():
            setattr(record, key, value)
        try:
            record.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = ("id", "employee_cen", "object_type", "object_id", "action", "changes", "actor", "occurred_at")
        read_only_fields = fields
