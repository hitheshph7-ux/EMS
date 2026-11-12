from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    mobile_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserRoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="user_assignments",
    )

    society = models.ForeignKey(
        "societies.Society",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_role_assignments",
    )

    board = models.ForeignKey(
        "societies.Board",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_role_assignments",
    )

    department_office = models.ForeignKey(
        "societies.DepartmentOffice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_role_assignments",
    )

    def __str__(self):
        return f"{self.user} - {self.role}"
