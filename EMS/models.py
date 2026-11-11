import hashlib
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


EVENT_TYPES = (
    ("APPOINTMENT", "Appointment"),
    ("PROMOTION", "Promotion"),
    ("DESIGNATION_CHANGE", "Designation change"),
    ("INCREMENT", "Increment"),
    ("PAY_REVISION", "Pay revision"),
    ("TRANSFER", "Transfer"),
    ("PROBATION_CONFIRMED", "Probation confirmed"),
    ("PROBATION_EXTENDED", "Probation extended"),
    ("SUSPENSION", "Suspension"),
    ("REINSTATEMENT", "Reinstatement"),
    ("LEAVE", "Leave"),
    ("TERMINATION", "Termination"),
)


def validate_increment_steps(value):
    if not isinstance(value, list):
        raise ValidationError("Increment steps must be a list of numeric amounts.")

    for step in value:
        if isinstance(step, bool) or not isinstance(step, (int, float)):
            raise ValidationError("Each increment step must be a numeric amount.")
        if not Decimal(str(step)).is_finite():
            raise ValidationError("Increment steps must be finite numeric amounts.")


class Designation(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    level = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"


class PayScale(models.Model):
    code = models.CharField(max_length=50, unique=True)
    min_pay = models.DecimalField(max_digits=12, decimal_places=2)
    max_pay = models.DecimalField(max_digits=12, decimal_places=2)
    increment_steps = models.JSONField(default=list, validators=[validate_increment_steps])
    revision_order = models.PositiveIntegerField()
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("revision_order", "effective_date", "code")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_pay__lte=models.F("max_pay")),
                name="pay_scale_min_pay_lte_max_pay",
            ),
        ]

    def __str__(self):
        return self.code


class EmployeeServiceProfile(models.Model):
    employee_cen = models.CharField(max_length=64, unique=True)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    department = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("full_name", "employee_cen")

    def __str__(self):
        return f"{self.full_name} ({self.employee_cen})"


class ServiceEventQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Service events cannot be physically deleted.")


class ServiceEvent(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        CANCELLED = "CANCELLED", "Cancelled"

    employee_cen = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    effective_date = models.DateField(db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    designation = models.ForeignKey(
        Designation, null=True, blank=True, on_delete=models.PROTECT,
        related_name="service_events",
    )
    pay_scale = models.ForeignKey(
        PayScale, null=True, blank=True, on_delete=models.PROTECT,
        related_name="service_events",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    is_locked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_service_events",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_service_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_on = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    objects = ServiceEventQuerySet.as_manager()

    class Meta:
        ordering = ("effective_date", "approved_at", "pk")
        indexes = [models.Index(fields=("employee_cen", "status", "effective_date"))]

    def delete(self, *args, **kwargs):
        raise ValidationError("Service events cannot be physically deleted.")

    def clean(self):
        super().clean()
        from EMS.validators import validate_service_event

        validate_service_event(self)

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if previous.is_locked:
                raise ValidationError("Unlock the service event before changing it.")
            if self.status == self.Status.CANCELLED:
                raise ValidationError("Cancel service events through the cancellation workflow.")
            if self.status == self.Status.SUBMITTED and previous.status == self.Status.SUBMITTED:
                submitted_fields = ("employee_cen", "event_type", "effective_date", "payload")
                if any(getattr(previous, field) != getattr(self, field) for field in submitted_fields):
                    raise ValidationError("Submitted service events cannot be edited; cancel and recreate them.")
            if previous.status == self.Status.APPROVED:
                protected = (
                    "employee_cen", "event_type", "effective_date", "payload",
                    "designation_id", "pay_scale_id",
                    "status", "approved_by_id", "approved_at",
                )
                if any(getattr(previous, field) != getattr(self, field) for field in protected):
                    raise ValidationError("Approved event history is immutable.")
        if self.status == self.Status.SUBMITTED and (
            previous is None
            or previous.status != self.Status.DRAFT
            or self.submitted_at is None
        ):
            raise ValidationError("Submit draft service events through the submission workflow.")
        if self.status == self.Status.APPROVED and (
            previous is None
            or previous.status != self.Status.SUBMITTED
            or self.approved_by_id is None
            or self.approved_at is None
        ):
            raise ValidationError("Approve submitted service events through the approval workflow.")
        if self.status == self.Status.CANCELLED:
            raise ValidationError("Cancel service events through the cancellation workflow.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_cen}: {self.get_event_type_display()} ({self.effective_date})"


class EmployeeServiceSnapshot(models.Model):
    employee_cen = models.CharField(max_length=64, unique=True)
    designation = models.ForeignKey(
        Designation, null=True, blank=True, on_delete=models.PROTECT,
        related_name="employee_snapshots",
    )
    designation_code = models.CharField(max_length=50, blank=True)
    designation_name = models.CharField(max_length=255, blank=True)
    designation_description = models.TextField(blank=True)
    designation_level = models.PositiveIntegerField(null=True, blank=True)
    pay_scale = models.ForeignKey(
        PayScale, null=True, blank=True, on_delete=models.PROTECT,
        related_name="employee_snapshots",
    )
    pay_scale_code = models.CharField(max_length=50, blank=True)
    pay_scale_min_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pay_scale_max_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pay_scale_revision_order = models.PositiveIntegerField(null=True, blank=True)
    pay_scale_effective_date = models.DateField(null=True, blank=True)
    pay_scale_increment_steps = models.JSONField(default=list, blank=True)
    current_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    society_cen = models.CharField(max_length=64, blank=True)
    employment_status = models.CharField(max_length=24, default="ACTIVE")
    probation_status = models.CharField(max_length=24, blank=True)
    as_of_date = models.DateField(null=True, blank=True)
    rebuilt_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Service snapshot for {self.employee_cen}"


class ProbationRecord(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CONFIRMED = "CONFIRMED", "Confirmed"
        EXTENDED = "EXTENDED", "Extended"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    employee_cen = models.CharField(max_length=64, db_index=True)
    start_date = models.DateField()
    expected_end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    extension_reason = models.TextField(blank=True)
    confirmation_event = models.ForeignKey(
        ServiceEvent, null=True, blank=True, on_delete=models.PROTECT,
        related_name="probation_confirmations",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-start_date",)

    def clean(self):
        if self.employee_cen and self.start_date and not ServiceEvent.objects.filter(
            employee_cen=self.employee_cen,
            event_type="APPOINTMENT",
            status=ServiceEvent.Status.APPROVED,
            effective_date__lte=self.start_date,
        ).exists():
            raise ValidationError({"start_date": "Probation must follow an approved appointment."})
        if self.start_date and self.expected_end_date and self.expected_end_date < self.start_date:
            raise ValidationError({"expected_end_date": "Probation must end on or after it starts."})
        if self.actual_end_date and self.start_date and self.actual_end_date < self.start_date:
            raise ValidationError({"actual_end_date": "Actual end date cannot precede probation."})
        if self.status == self.Status.EXTENDED and not self.extension_reason.strip():
            raise ValidationError({"extension_reason": "An extension reason is required."})
        if self.status == self.Status.CONFIRMED and not self.confirmation_event_id:
            raise ValidationError({"confirmation_event": "Confirmation requires an approved event."})
        if self.employee_cen and self.status in (self.Status.ACTIVE, self.Status.EXTENDED):
            active_records = type(self).objects.filter(
                employee_cen=self.employee_cen,
                status__in=(self.Status.ACTIVE, self.Status.EXTENDED),
            )
            if self.pk:
                active_records = active_records.exclude(pk=self.pk)
            if active_records.exists():
                raise ValidationError({"employee_cen": "Employee already has an active probation record."})


class TransferWorkflow(models.Model):
    class Status(models.TextChoices):
        PENDING_RELIEF = "PENDING_RELIEF", "Awaiting relieving society"
        RELIEVED = "RELIEVED", "Relieved"
        ACCEPTED = "ACCEPTED", "Accepted by receiving society"
        CANCELLED = "CANCELLED", "Cancelled"

    event = models.OneToOneField(
        ServiceEvent, on_delete=models.PROTECT, related_name="transfer_workflow",
    )
    from_society_cen = models.CharField(max_length=64)
    to_society_cen = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_RELIEF)
    relieved_at = models.DateTimeField(null=True, blank=True)
    relieved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="relieved_transfers",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="accepted_transfers",
    )

    def clean(self):
        if self.from_society_cen == self.to_society_cen:
            raise ValidationError({"to_society_cen": "Receiving society must differ from the current society."})


class RecruitmentRecord(models.Model):
    employee_cen = models.CharField(max_length=64, db_index=True)
    recruitment_date = models.DateField()
    recruitment_mode = models.CharField(max_length=40)
    reference_number = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    appointment_event = models.ForeignKey(
        ServiceEvent, null=True, blank=True, on_delete=models.PROTECT,
        related_name="recruitment_records",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class ScannedServiceBook(models.Model):
    employee_cen = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    document_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to="service-books/%Y/%m/")
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "file"):
            digest = hashlib.sha256()
            for chunk in self.file.chunks():
                digest.update(chunk)
            self.sha256 = digest.hexdigest()
            self.file.seek(0)
        super().save(*args, **kwargs)


class ACRRecord(models.Model):
    employee_cen = models.CharField(max_length=64, db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    rating = models.CharField(max_length=40)
    details = models.JSONField(default=dict, blank=True)
    is_locked = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-period_start",)
        constraints = [
            models.UniqueConstraint(
                fields=("employee_cen", "period_start", "period_end"),
                name="unique_employee_acr_period",
            ),
        ]

    def clean(self):
        if self.period_end < self.period_start:
            raise ValidationError({"period_end": "ACR period end must be on or after its start."})

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if previous.is_locked:
                raise ValidationError("Unlock the ACR before changing it.")
        super().save(*args, **kwargs)


class AuditEntryQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Audit entries cannot be physically deleted.")


class AuditEntry(models.Model):
    employee_cen = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=40)
    object_id = models.CharField(max_length=64)
    action = models.CharField(max_length=40)
    changes = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at",)

    objects = AuditEntryQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Audit entries are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit entries cannot be physically deleted.")


class DigitalSignature(models.Model):
    event = models.OneToOneField(
        ServiceEvent, on_delete=models.PROTECT, related_name="digital_signature",
    )
    provider = models.CharField(max_length=80)
    signer = models.CharField(max_length=150)
    signature_value = models.CharField(max_length=128)
    signed_at = models.DateTimeField(default=timezone.now)


def audit_change(*, employee_cen, instance, action, actor=None, changes=None):
    return AuditEntry.objects.create(
        employee_cen=employee_cen,
        object_type=instance._meta.model_name,
        object_id=str(instance.pk),
        action=action,
        actor=actor,
        changes=changes or {},
    )
