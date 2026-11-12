from rest_framework import serializers

from .models import District, SocietyType, Society


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name"]


class SocietyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocietyType
        fields = ["id", "name"]


class SocietySerializer(serializers.ModelSerializer):
    class Meta:
        model = Society
        fields = [
            "id",
            "registration_number",
            "name",
            "address",
            "society_type",
            "district",
            "status",
        ]