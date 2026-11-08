from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=False,
        allow_blank=True
    )
    mobile_number = serializers.CharField(
        required=False,
        allow_blank=True
    )
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