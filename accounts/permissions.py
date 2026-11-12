from rest_framework.permissions import BasePermission, SAFE_METHODS


class PasswordChangeRequiredPermission(BasePermission):
    message = "You must change your password before accessing this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not user.must_change_password
        )


class PasswordChangeAccessPermission(BasePermission):
    message = "A valid password-change token is required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.must_change_password:
            return True

        token = request.auth
        return bool(token and token.get("password_change_only", False))


def user_has_role(user, role_name):
    return user.role_assignments.filter(
        role__name=role_name
    ).exists()


def user_has_society_access(user, society_id):
    return user.role_assignments.filter(
        society_id=society_id
    ).exists()


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and not user.must_change_password
            and user_has_role(user, "Employee")
        )


class IsSocietyAdminOrSecretary(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and not user.must_change_password
            and (
                user_has_role(user, "Society Admin")
                or user_has_role(user, "Society Secretary")
            )
        )


class IsDepartmentOfficer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and not user.must_change_password
            and user_has_role(user, "Department Officer")
        )


class IsBoardUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and not user.must_change_password
            and user_has_role(user, "Board User")
        )


class DepartmentOfficerReadOnlyPermission(BasePermission):
    """
    Department Officers are read-only.
    Only Django superusers can modify Society master data.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.must_change_password:
            return False

        if user_has_role(user, "Department Officer"):
            return request.method in SAFE_METHODS

        if request.method in SAFE_METHODS:
            return True

        return user.is_superuser
