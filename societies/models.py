from django.db import models


class District(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class SocietyType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Society(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DORMANT = "DORMANT", "Dormant"
        UNDER_LIQUIDATION = (
            "UNDER_LIQUIDATION",
            "Under Liquidation",
        )

    registration_number = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(max_length=255)
    address = models.TextField()

    society_type = models.ForeignKey(
        SocietyType,
        on_delete=models.PROTECT,
        related_name="societies",
    )

    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="societies",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def __str__(self):
        return self.name

class Board(models.Model):
    name = models.CharField(max_length=100, unique =True)

    def __str__(self):
        return self.name

class DepartmentOffice(models.Model):
    name = models.CharField(max_length=150,unique=True)
    address = models.TextField()

    def __str__(self):
        return self.name