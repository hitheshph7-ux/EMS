from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Role, UserRoleAssignment, AuditLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username", "mobile_number", "email",
        "is_staff", "is_active", "is_locked",
        "must_change_password",
    )
    search_fields = ("username", "mobile_number", "email")

    fieldsets = UserAdmin.fieldsets + (
        ("CEMS Account Details", {
            "fields": (
                "mobile_number",
                "failed_login_attempts",
                "is_locked",
                "must_change_password",
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("CEMS Account Details", {
            "fields": ("mobile_number",)
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "user", "role", "society", "board", "department_office"
    )
    list_filter = ("role",)
    search_fields = ("user__username", "user__mobile_number", "role__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "actor", "action", "model_name",
        "object_id", "ip_address", "timestamp",
    )
    list_filter = ("action", "model_name")
    search_fields = ("model_name", "object_id", "actor__username")
    readonly_fields = (
        "actor", "action", "model_name", "object_id",
        "changes", "ip_address", "timestamp",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
