
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    mobile_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        username = attrs.get("username")
        mobile_number = attrs.get("mobile_number")

        if not username and not mobile_number:
            raise serializers.ValidationError(
                "Username or mobile number is required."
            )

        if username and mobile_number:
            raise serializers.ValidationError(
                "Provide either username or mobile number, not both."
            )

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "mobile_number",
            "is_active",
        ]
        read_only_fields = fields


class SecureTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)

        try:
            user = User.objects.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "User account does not exist."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive."
            )

        if user.is_locked:
            raise serializers.ValidationError(
                "This account is locked."
            )

        if user.must_change_password:
            raise serializers.ValidationError(
                "Change your password before refreshing your token."
            )

        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
