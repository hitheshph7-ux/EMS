
from rest_framework.permissions import BasePermission


class PasswordChangeRequiredPermission(BasePermission):
    """
    Prevent users who must change their password
    from accessing normal protected endpoints.
    """

    message = "You must change your password before accessing this resource."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return not user.must_change_password

class PasswordChangeAccessPermission(BasePermission):
    """
    Allow normal users to change their password.
    Users required to change their password must
    use a password-change-only access token.
    """

    message = "A valid password-change token is required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Normal authenticated users can change their password.
        if not user.must_change_password:
            return True

        # First-login users need a restricted token.
        token = request.auth

        return bool(
            token and token.get("password_change_only", False)
        )
