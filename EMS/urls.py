from django.urls import include, path
from rest_framework.routers import DefaultRouter

from EMS.api import (
    ACRRecordViewSet,
    AuditEntryViewSet,
    DesignationViewSet,
    EmployeeServiceProfileViewSet,
    PayScaleViewSet,
    ProbationRecordViewSet,
    RecruitmentRecordViewSet,
    ScannedServiceBookViewSet,
    ServiceEventViewSet,
    ServiceStateView,
    SnapshotViewSet,
    TransferWorkflowViewSet,
)

router = DefaultRouter()
router.register("designations", DesignationViewSet, basename="designation")
router.register("pay-scales", PayScaleViewSet, basename="pay-scale")
router.register("employee-profiles", EmployeeServiceProfileViewSet, basename="employee-profile")
router.register("service-events", ServiceEventViewSet, basename="service-event")
router.register("service-snapshots", SnapshotViewSet, basename="service-snapshot")
router.register("probation-records", ProbationRecordViewSet, basename="probation-record")
router.register("transfers", TransferWorkflowViewSet, basename="transfer")
router.register("recruitment-records", RecruitmentRecordViewSet, basename="recruitment-record")
router.register("scanned-service-books", ScannedServiceBookViewSet, basename="scanned-service-book")
router.register("acr-records", ACRRecordViewSet, basename="acr-record")
router.register("audit-history", AuditEntryViewSet, basename="audit-history")

urlpatterns = [
    path("", include(router.urls)),
    path("service-state/", ServiceStateView.as_view(), name="service-state"),
]
