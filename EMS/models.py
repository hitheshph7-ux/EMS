
from django.db import models, transaction


class CENCounter(models.Model):
    # Keep this row even if employee records are deleted.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    next_number = models.PositiveBigIntegerField(default=1)

    class Meta:
        verbose_name = "CEN Counter"
        verbose_name_plural = "CEN Counter"

    def __str__(self):
        return f"Next CEN number: {self.next_number}"


class Employee(models.Model):

    # Permanent Co-operative Employee Number
    cen = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        MARRIED = "MARRIED", "Married"
        DIVORCED = "DIVORCED", "Divorced"
        WIDOWED = "WIDOWED", "Widowed"

    class EmployeeStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_VERIFICATION = (
            "PENDING_VERIFICATION",
            "Pending Verification",
        )
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        RETIRED = "RETIRED", "Retired"
        RESIGNED = "RESIGNED", "Resigned"
        DECEASED = "DECEASED", "Deceased"

    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )
    mobile = models.CharField(max_length=15)
    email = models.EmailField(blank=True)

    community = models.CharField(max_length=100, blank=True)
    marital_status = models.CharField(
        max_length=10,
        choices=MaritalStatus.choices,
        blank=True,
    )

    status = models.CharField(
        max_length=25,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                old_cen = (
                    type(self).objects
                    .filter(pk=self.pk)
                    .values_list("cen", flat=True)
                    .first()
                )

                if old_cen and self.cen != old_cen:
                    raise ValueError(
                        "An assigned CEN cannot be changed."
                    )

            # Generate a CEN if this employee does not have one.
            if not self.cen:
                counter = (
                    CENCounter.objects
                    .select_for_update()
                    .get(pk=1)
                )

                self.cen = f"CEN{counter.next_number:06d}"
                counter.next_number += 1
                counter.save(update_fields=["next_number"])

            super().save(*args, **kwargs)
