from django.contrib import admin

from .models import (
    District,
    SocietyType,
    Society,
    Board,
    DepartmentOffice,
)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(SocietyType)
class SocietyTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number", "name",
        "society_type", "district", "status",
    )
    list_filter = ("status", "district", "society_type")
    search_fields = ("registration_number", "name")


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(DepartmentOffice)
class DepartmentOfficeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "address")
    search_fields = ("name",)
