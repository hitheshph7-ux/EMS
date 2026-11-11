from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAdminUser, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from EMS.models import (
    ACRRecord,
    AuditEntry,
    Designation,
    EmployeeServiceProfile,
    EmployeeServiceSnapshot,
    PayScale,
    ProbationRecord,
    RecruitmentRecord,
    ScannedServiceBook,
    ServiceEvent,
    TransferWorkflow,
    audit_change,
)
from EMS.serializers import (
    ACRRecordSerializer,
    AuditEntrySerializer,
    DesignationSerializer,
    EmployeeServiceProfileSerializer,
    EmployeeServiceSnapshotSerializer,
    PayScaleSerializer,
    ProbationRecordSerializer,
    RecruitmentRecordSerializer,
    ScannedServiceBookSerializer,
    ServiceEventSerializer,
    TransferWorkflowSerializer,
)
from EMS.services import (
    ServiceBookService,
    accept_transfer,
    approve_event,
    cancel_event,
    relieve_transfer,
    set_acr_lock,
    set_event_lock,
    submit_event,
)


class CatalogPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )


class CatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (CatalogPermission,)
    http_method_names = ("get", "post", "put", "patch", "head", "options")


class DesignationViewSet(CatalogViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer


class PayScaleViewSet(CatalogViewSet):
    queryset = PayScale.objects.all()
    serializer_class = PayScaleSerializer


def raise_api_validation(error):
    detail = error.message_dict if hasattr(error, "message_dict") else error.messages
    raise serializers.ValidationError(detail)


def audit_instance(instance, *, actor, action):
    cen = getattr(instance, "employee_cen", None)
    if cen is None and hasattr(instance, "event"):
        cen = instance.event.employee_cen
    if cen:
        audit_change(employee_cen=cen, instance=instance, action=action, actor=actor)


class Module3ViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    http_method_names = ("get", "post", "put", "patch", "head", "options")
    employee_filter = "employee_cen"

    def get_queryset(self):
        queryset = super().get_queryset()
        cen = self.request.query_params.get("employee_cen")
        return queryset.filter(**{self.employee_filter: cen}) if cen else queryset

    def perform_update(self, serializer):
        try:
            instance = serializer.save()
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        audit_instance(instance, actor=self.request.user, action="updated")


class EmployeeServiceProfileViewSet(Module3ViewSet):
    queryset = EmployeeServiceProfile.objects.all()
    serializer_class = EmployeeServiceProfileSerializer

    def perform_create(self, serializer):
        profile = serializer.save()
        audit_instance(profile, actor=self.request.user, action="created")


class ServiceEventViewSet(Module3ViewSet):
    queryset = ServiceEvent.objects.select_related("created_by", "approved_by")
    serializer_class = ServiceEventSerializer

    def perform_create(self, serializer):
        event = serializer.save(created_by=self.request.user)
        audit_instance(event, actor=self.request.user, action="created")

    def perform_update(self, serializer):
        super().perform_update(serializer)

    @action(detail=True, methods=("post",))
    def submit(self, request, pk=None):
        try:
            event = submit_event(self.get_object(), actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=("post",))
    def approve(self, request, pk=None):
        try:
            event = approve_event(self.get_object(), actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        try:
            event = cancel_event(
                self.get_object(), actor=request.user,
                reason=str(request.data.get("reason", "")),
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=("post",))
    def lock(self, request, pk=None):
        try:
            event = set_event_lock(self.get_object(), locked=True, actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=("post",))
    def unlock(self, request, pk=None):
        try:
            event = set_event_lock(self.get_object(), locked=False, actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=("get",))
    def signature(self, request, pk=None):
        event = self.get_object()
        if not hasattr(event, "digital_signature"):
            raise Http404("This event has no signature.")
        signature = event.digital_signature
        return Response(
            {
                "provider": signature.provider,
                "signer": signature.signer,
                "signature_value": signature.signature_value,
                "signed_at": signature.signed_at,
            }
        )


class SnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmployeeServiceSnapshot.objects.select_related("designation", "pay_scale")
    serializer_class = EmployeeServiceSnapshotSerializer
    permission_classes = (IsAdminUser,)
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        cen = self.request.query_params.get("employee_cen")
        return queryset.filter(employee_cen=cen) if cen else queryset


class ServiceStateView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        cen = request.query_params.get("employee_cen")
        requested_date = request.query_params.get("date")
        if not cen or not requested_date:
            raise serializers.ValidationError(
                {"detail": "Both employee_cen and date query parameters are required."}
            )
        try:
            as_of = date.fromisoformat(requested_date)
            if as_of.isoformat() != requested_date:
                raise ValueError
            state = ServiceBookService.state_as_of(cen, as_of)
        except (ValueError, DjangoValidationError) as exc:
            if isinstance(exc, DjangoValidationError):
                raise_api_validation(exc)
            raise serializers.ValidationError({"date": "Use YYYY-MM-DD format."})
        return Response(state)


class ProbationRecordViewSet(Module3ViewSet):
    queryset = ProbationRecord.objects.select_related("confirmation_event", "created_by")
    serializer_class = ProbationRecordSerializer

    def perform_create(self, serializer):
        record = serializer.save(created_by=self.request.user)
        audit_instance(record, actor=self.request.user, action="created")


class TransferWorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransferWorkflow.objects.select_related("event", "relieved_by", "accepted_by")
    serializer_class = TransferWorkflowSerializer
    permission_classes = (IsAdminUser,)
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        cen = self.request.query_params.get("employee_cen")
        return queryset.filter(event__employee_cen=cen) if cen else queryset

    @action(detail=True, methods=("post",))
    def relieve(self, request, pk=None):
        try:
            workflow = relieve_transfer(self.get_object(), actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(workflow).data)

    @action(detail=True, methods=("post",))
    def accept(self, request, pk=None):
        try:
            workflow = accept_transfer(self.get_object(), actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(self.get_serializer(workflow).data)


class RecruitmentRecordViewSet(Module3ViewSet):
    queryset = RecruitmentRecord.objects.select_related("appointment_event", "created_by")
    serializer_class = RecruitmentRecordSerializer

    def perform_create(self, serializer):
        record = serializer.save(created_by=self.request.user)
        audit_instance(record, actor=self.request.user, action="created")


class ScannedServiceBookViewSet(Module3ViewSet):
    queryset = ScannedServiceBook.objects.select_related("uploaded_by")
    serializer_class = ScannedServiceBookSerializer

    def perform_create(self, serializer):
        document = serializer.save(uploaded_by=self.request.user)
        audit_instance(document, actor=self.request.user, action="uploaded")

    @action(detail=True, methods=("get",))
    def download(self, request, pk=None):
        document = self.get_object()
        try:
            file_handle = document.file.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404("The scanned service-book file is unavailable.")
        filename = document.file.name.rsplit("/", 1)[-1]
        return FileResponse(file_handle, as_attachment=True, filename=filename)


class ACRRecordViewSet(Module3ViewSet):
    queryset = ACRRecord.objects.select_related("created_by")
    serializer_class = ACRRecordSerializer

    def perform_create(self, serializer):
        record = serializer.save(created_by=self.request.user)
        audit_instance(record, actor=self.request.user, action="created")

    @action(detail=True, methods=("post",))
    def lock(self, request, pk=None):
        return Response(ACRRecordSerializer(set_acr_lock(self.get_object(), locked=True, actor=request.user)).data)

    @action(detail=True, methods=("post",))
    def unlock(self, request, pk=None):
        return Response(ACRRecordSerializer(set_acr_lock(self.get_object(), locked=False, actor=request.user)).data)


class AuditEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEntry.objects.select_related("actor")
    serializer_class = AuditEntrySerializer
    permission_classes = (IsAdminUser,)
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        cen = self.request.query_params.get("employee_cen")
        return queryset.filter(employee_cen=cen) if cen else queryset
