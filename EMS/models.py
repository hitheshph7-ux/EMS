
from django.conf import settings
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

    # Basic employee details
    society = models.CharField(max_length=150, blank=True, default="")
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )

    # Sensitive identity information
    aadhaar = models.CharField(max_length=12, blank=True)
    pan = models.CharField(max_length=10, blank=True)

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
        return f"{self.cen or 'No CEN'} - {self.full_name}"

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


class EmployeeAddress(models.Model):

    class AddressType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        PRESENT = "PRESENT", "Present"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
    )
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default="India")

    class Meta:
        verbose_name_plural = "Employee addresses"

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_address_type_display()}"


class EmployeeQualification(models.Model):

    class QualificationType(models.TextChoices):
        EDUCATION = "EDUCATION", "Education"
        HDC = "HDC", "HDC"
        JDC = "JDC", "JDC"
        OTHER = "OTHER", "Other"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="qualifications",
    )
    qualification_type = models.CharField(
        max_length=15,
        choices=QualificationType.choices,
    )
    qualification_name = models.CharField(max_length=150)
    institution = models.CharField(max_length=200, blank=True)
    year_completed = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    grade_or_percentage = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.employee.full_name} - {self.qualification_name}"


class EmployeeFamilyMember(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="family_members",
    )
    name = models.CharField(max_length=150)
    relation = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    is_dependent = models.BooleanField(default=False)
    is_nominee = models.BooleanField(default=False)
    nominee_share = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return f"{self.name} - {self.employee.full_name}"


class EmployeeBankAccount(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    account_holder_name = models.CharField(max_length=150, blank=True)
    ifsc = models.CharField(max_length=11)
    account_number = models.CharField(max_length=34)

    def __str__(self):
        # Do not expose the full account number.
        return f"{self.employee.full_name} - {self.ifsc}"


class EmployeeDocument(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="employee_documents/")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_employee_documents",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_employee_documents",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.full_name} - {self.document_type}"
