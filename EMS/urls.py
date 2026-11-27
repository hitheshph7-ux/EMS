from django.urls import include, path
from rest_framework.routers import DefaultRouter

from EMS.api import (
    ACRRecordViewSet,
    AuditEntryViewSet,
    DesignationViewSet,
    EmployeeRecordsView,
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
    path("employee-records/", EmployeeRecordsView.as_view(), name="employee-records"),
    path("", include(router.urls)),
    path("service-state/", ServiceStateView.as_view(), name="service-state"),
]

from django.urls import path
from . import views

app_name = "EMS"

urlpatterns = [

    # ==========================================
    # 1. EMPLOYEE LIST
    # ==========================================

    path(
        "",
        views.employee_list,
        name="home",
    ),

    path(
        "employees/",
        views.employee_list,
        name="employee_list",
    ),

    # ==========================================
    # 2. EMPLOYEE PROFILE
    # ==========================================

    path(
        "employees/<int:employee_id>/",
        views.employee_detail,
        name="employee_detail",
    ),

    # ==========================================
    # 3. EMPLOYEE APIs
    # ==========================================

    path(
        "api/employees/",
        views.employee_api,
        name="employee_api",
    ),

    path(
        "api/employees/<int:employee_id>/",
        views.employee_detail_api,
        name="employee_detail_api",
    ),

    # ==========================================
    # 4. EMPLOYEE ADDRESS MANAGEMENT
    # ==========================================

    path(
        "employees/<int:employee_id>/addresses/add/",
        views.employee_address_add,
        name="employee_address_add",
    ),

]
