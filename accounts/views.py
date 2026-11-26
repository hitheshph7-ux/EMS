
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    LoginSerializer,
    UserProfileSerializer,
    SecureTokenRefreshSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
)

from .permissions import (
    PasswordChangeRequiredPermission,
    PasswordChangeAccessPermission,
)


class CurrentUserView(APIView):
    serializer_class = UserProfileSerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeRequiredPermission,
    ]

    @extend_schema(
        operation_id="current_user",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_login",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful or password change required."),
            400: OpenApiResponse(description="Invalid login request."),
            401: OpenApiResponse(description="Invalid username or password."),
            403: OpenApiResponse(description="Account is locked or inactive."),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data.get("username")
        mobile_number = serializer.validated_data.get("mobile_number")
        password = serializer.validated_data["password"]

        User = get_user_model()

        if mobile_number:
            account = User.objects.filter(
                mobile_number=mobile_number
            ).first()
        else:
            account = User.objects.filter(
                username=username
            ).first()

        if account is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if account.is_locked:
            return Response(
                {
                    "detail": "Account is locked after 5 failed login attempts."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user = authenticate(
            request,
            username=account.username,
            password=password,
        )

        if user is None:
            account.failed_login_attempts += 1

            if account.failed_login_attempts >= 5:
                account.is_locked = True

            account.save(
                update_fields=[
                    "failed_login_attempts",
                    "is_locked",
                ]
            )

            if account.is_locked:
                return Response(
                    {
                        "detail": "Account locked after 5 failed login attempts."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            return Response(
                {
                    "detail": "Invalid username or password.",
                    "remaining_attempts": 5 - account.failed_login_attempts,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.save(update_fields=["failed_login_attempts"])

        if user.must_change_password:
            refresh = RefreshToken.for_user(user)

            access = refresh.access_token
            access["password_change_only"] = True

            return Response(
                {
                    "detail": "Password change required.",
                    "must_change_password": True,
                    "access": str(access),
                },
                status=status.HTTP_200_OK,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "must_change_password": False,
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    serializer_class = SecureTokenRefreshSerializer

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="auth_refresh",
        request=SecureTokenRefreshSerializer,
        responses={
            200: OpenApiResponse(description="New access token generated."),
            401: OpenApiResponse(description="Invalid, expired, or blacklisted refresh token."),
        },
    )
    def post(self, request):
        serializer = SecureTokenRefreshSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)

            return Response(
                serializer.validated_data,
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {
                    "detail": "Invalid, expired, or blacklisted refresh token."
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    serializer_class = LogoutSerializer

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="auth_logout",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Successfully logged out."),
            400: OpenApiResponse(description="Missing, invalid, or expired refresh token."),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordChangeView(APIView):
    serializer_class = PasswordChangeSerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeAccessPermission,
    ]

    @extend_schema(
        operation_id="auth_password_change",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully."),
            400: OpenApiResponse(description="Password validation failed."),
        },
    )
    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response(
                {
                    "detail": "Current password and new password are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        if not user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as error:
            return Response(
                {"detail": error.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.must_change_password = False

        user.save(
            update_fields=[
                "password",
                "must_change_password",
            ]
        )

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK
        )
