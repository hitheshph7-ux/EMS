
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse

from accounts.permissions import (
    PasswordChangeRequiredPermission,
    DepartmentOfficerReadOnlyPermission,
)
from accounts.audit import create_audit_log

from .models import District, SocietyType, Society
from .serializers import (
    DistrictSerializer,
    SocietyTypeSerializer,
    SocietySerializer,
)


class DistrictListView(APIView):
    serializer_class = DistrictSerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeRequiredPermission,
    ]

    @extend_schema(
        operation_id="district_list",
        responses={200: DistrictSerializer(many=True)},
    )
    def get(self, request):
        districts = District.objects.all().order_by("name")
        serializer = DistrictSerializer(districts, many=True)
        return Response(serializer.data)


class SocietyTypeListView(APIView):
    serializer_class = SocietyTypeSerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeRequiredPermission,
    ]

    @extend_schema(
        operation_id="society_type_list",
        responses={200: SocietyTypeSerializer(many=True)},
    )
    def get(self, request):
        society_types = SocietyType.objects.all().order_by("name")
        serializer = SocietyTypeSerializer(society_types, many=True)
        return Response(serializer.data)


class SocietyListCreateView(APIView):
    serializer_class = SocietySerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeRequiredPermission,
        DepartmentOfficerReadOnlyPermission,
    ]

    @extend_schema(
        operation_id="society_list",
        responses={200: SocietySerializer(many=True)},
    )
    def get(self, request):
        societies = Society.objects.all().order_by("name")
        serializer = SocietySerializer(societies, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="society_create",
        request=SocietySerializer,
        responses={
            201: SocietySerializer,
            400: OpenApiResponse(description="Invalid society data."),
        },
    )
    def post(self, request):
        serializer = SocietySerializer(data=request.data)

        if serializer.is_valid():
            society = serializer.save()

            create_audit_log(
                request,
                "CREATE",
                society,
                changes={
                    "created": serializer.data,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class SocietyDetailView(APIView):
    serializer_class = SocietySerializer

    permission_classes = [
        IsAuthenticated,
        PasswordChangeRequiredPermission,
        DepartmentOfficerReadOnlyPermission,
    ]

    def get_object(self, pk):
        try:
            return Society.objects.get(pk=pk)
        except Society.DoesNotExist:
            return None

    @extend_schema(
        operation_id="society_retrieve",
        responses={
            200: SocietySerializer,
            404: OpenApiResponse(description="Society not found."),
        },
    )
    def get(self, request, pk):
        society = self.get_object(pk)

        if society is None:
            return Response(
                {"error": "Society not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SocietySerializer(society)
        return Response(serializer.data)

    @extend_schema(
        operation_id="society_update",
        request=SocietySerializer,
        responses={
            200: SocietySerializer,
            400: OpenApiResponse(description="Invalid society data."),
            404: OpenApiResponse(description="Society not found."),
        },
    )
    def put(self, request, pk):
        society = self.get_object(pk)

        if society is None:
            return Response(
                {"error": "Society not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        old_data = SocietySerializer(society).data

        serializer = SocietySerializer(
            society,
            data=request.data
        )

        if serializer.is_valid():
            society = serializer.save()
            new_data = serializer.data

            changes = {
                field: {
                    "old": old_data.get(field),
                    "new": new_data.get(field),
                }
                for field in new_data
                if old_data.get(field) != new_data.get(field)
            }

            create_audit_log(
                request,
                "UPDATE",
                society,
                changes=changes,
            )

            return Response(new_data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        operation_id="society_delete",
        responses={
            200: OpenApiResponse(description="Society deleted successfully."),
            404: OpenApiResponse(description="Society not found."),
        },
    )
    def delete(self, request, pk):
        society = self.get_object(pk)

        if society is None:
            return Response(
                {"error": "Society not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        old_data = SocietySerializer(society).data

        create_audit_log(
            request,
            "DELETE",
            society,
            changes={
                "deleted": old_data,
            },
        )

        society.delete()

        return Response(
            {"message": "Society deleted successfully"},
            status=status.HTTP_200_OK
        )
