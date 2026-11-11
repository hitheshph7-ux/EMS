from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from EMS.models import (
    ACRRecord,
    AuditEntry,
    Designation,
    EmployeeServiceProfile,
    EmployeeServiceSnapshot,
    PayScale,
    ProbationRecord,
    ServiceEvent,
    TransferWorkflow,
)
from EMS.services import (
    ServiceBookService,
    accept_transfer,
    approve_event,
    cancel_event,
    relieve_transfer,
    set_event_lock,
    state_as_of,
    submit_event,
)


class ServiceBookDomainTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin = get_user_model().objects.create_user(
            username="service-book-admin", password="test-password", is_staff=True
        )
        self.junior = Designation.objects.create(code="JNR", name="Junior", level=1)
        self.senior = Designation.objects.create(code="SNR", name="Senior", level=2)
        self.scale = PayScale.objects.create(
            code="SB-1",
            min_pay=Decimal("25000"),
            max_pay=Decimal("30000"),
            increment_steps=[500, 1000],
            revision_order=1,
            effective_date=date(2020, 1, 1),
        )

    def create_event(self, event_type, effective_date, payload, cen="E-100"):
        return ServiceEvent.objects.create(
            employee_cen=cen,
            event_type=event_type,
            effective_date=effective_date,
            payload=payload,
        )

    def appoint(self, cen="E-100"):
        event = self.create_event(
            "APPOINTMENT",
            date(2020, 1, 1),
            {
                "designation_id": self.junior.pk,
                "pay_scale_id": self.scale.pk,
                "pay_amount": "25000.00",
                "society_cen": "S-1",
            },
            cen,
        )
        submit_event(event, actor=self.admin)
        return approve_event(event, actor=self.admin)

    def test_snapshot_is_derived_only_from_approved_events(self):
        draft = self.create_event(
            "APPOINTMENT",
            date(2020, 1, 1),
            {
                "designation_id": self.junior.pk,
                "pay_scale_id": self.scale.pk,
                "pay_amount": "25000",
                "society_cen": "S-1",
            },
        )

        snapshot = ServiceBookService.rebuild("E-100")
        self.assertIsNone(snapshot.designation_id)
        self.assertIsNone(state_as_of("E-100", date(2021, 1, 1))["designation_id"])

        submit_event(draft, actor=self.admin)
        approve_event(draft, actor=self.admin)
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.designation_id, self.junior.pk)
        self.assertEqual(snapshot.current_pay, Decimal("25000.00"))
        self.assertEqual(snapshot.society_cen, "S-1")

    def test_historical_state_uses_event_history_not_latest_snapshot(self):
        self.appoint()
        promotion = self.create_event(
            "PROMOTION", date(2022, 1, 1), {"designation_id": self.senior.pk}
        )
        submit_event(promotion, actor=self.admin)
        approve_event(promotion, actor=self.admin)

        self.assertEqual(
            ServiceBookService.state_as_of("E-100", date(2021, 12, 31))["designation_id"],
            self.junior.pk,
        )
        self.assertEqual(
            ServiceBookService.state_as_of("E-100", date(2022, 1, 1))["designation_id"],
            self.senior.pk,
        )
        self.assertEqual(EmployeeServiceSnapshot.objects.get(employee_cen="E-100").designation_id, self.senior.pk)

    def test_event_history_keeps_catalog_labels_as_approved(self):
        self.appoint()
        Designation.objects.filter(pk=self.junior.pk).update(
            name="Renamed later", description="Changed description", level=9
        )
        PayScale.objects.filter(pk=self.scale.pk).update(
            code="RENAMED-SCALE",
            min_pay=Decimal("26000"),
            max_pay=Decimal("50000"),
            increment_steps=[2000],
        )

        state = state_as_of("E-100", date(2021, 1, 1))
        self.assertEqual(state["designation_name"], "Junior")
        self.assertEqual(state["designation_description"], "")
        self.assertEqual(state["designation_level"], 1)
        self.assertEqual(state["pay_scale_code"], "SB-1")
        self.assertEqual(state["pay_scale_min_pay"], Decimal("25000.00"))
        self.assertEqual(state["pay_scale_max_pay"], Decimal("30000.00"))
        self.assertEqual(state["pay_scale_increment_steps"], [500, 1000])

    def test_rebuild_accepts_employee_object_with_cen_field(self):
        self.appoint()
        snapshot = ServiceBookService.rebuild(SimpleNamespace(CEN="E-100"))
        self.assertEqual(snapshot.employee_cen, "E-100")

    def test_promotion_requires_a_higher_designation_level(self):
        self.appoint()
        promotion = self.create_event(
            "PROMOTION", date(2021, 1, 1), {"designation_id": self.junior.pk}
        )
        submit_event(promotion, actor=self.admin)

        with self.assertRaises(ValidationError):
            approve_event(promotion, actor=self.admin)

    def test_increment_must_match_step_and_keep_pay_within_scale(self):
        self.appoint()
        invalid = self.create_event(
            "INCREMENT",
            date(2021, 1, 1),
            {
                "pay_scale_id": self.scale.pk,
                "increment_amount": "750",
                "new_pay": "25750",
            },
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

        valid = self.create_event(
            "INCREMENT",
            date(2021, 1, 1),
            {
                "pay_scale_id": self.scale.pk,
                "increment_amount": "500",
                "new_pay": "25500",
            },
        )
        submit_event(valid, actor=self.admin)
        approve_event(valid, actor=self.admin)
        self.assertEqual(state_as_of("E-100", date(2021, 1, 1))["current_pay"], Decimal("25500"))

    def test_pay_revision_and_designation_change_update_history(self):
        self.appoint()
        designation_change = self.create_event(
            "DESIGNATION_CHANGE",
            date(2021, 1, 1),
            {"designation_id": self.senior.pk},
        )
        submit_event(designation_change, actor=self.admin)
        approve_event(designation_change, actor=self.admin)
        pay_revision = self.create_event(
            "PAY_REVISION",
            date(2022, 1, 1),
            {"pay_scale_id": self.scale.pk, "pay_amount": "28000"},
        )
        submit_event(pay_revision, actor=self.admin)
        approve_event(pay_revision, actor=self.admin)

        state = state_as_of("E-100", date(2022, 1, 1))
        self.assertEqual(state["designation_id"], self.senior.pk)
        self.assertEqual(state["current_pay"], Decimal("28000"))

    def test_leave_suspension_reinstatement_and_termination_are_date_based(self):
        self.appoint()
        leave = self.create_event(
            "LEAVE",
            date(2021, 1, 1),
            {"start_date": "2021-01-01", "end_date": "2021-01-10"},
        )
        submit_event(leave, actor=self.admin)
        approve_event(leave, actor=self.admin)
        self.assertEqual(state_as_of("E-100", date(2021, 1, 5))["employment_status"], "ON_LEAVE")
        self.assertEqual(state_as_of("E-100", date(2021, 1, 11))["employment_status"], "ACTIVE")

        suspension = self.create_event(
            "SUSPENSION", date(2022, 1, 1), {"reason": "Administrative review"}
        )
        submit_event(suspension, actor=self.admin)
        approve_event(suspension, actor=self.admin)
        reinstatement = self.create_event(
            "REINSTATEMENT", date(2023, 1, 1), {"reason": "Review completed"}
        )
        submit_event(reinstatement, actor=self.admin)
        approve_event(reinstatement, actor=self.admin)
        termination = self.create_event(
            "TERMINATION", date(2024, 1, 1), {"reason": "Service ended"}
        )
        submit_event(termination, actor=self.admin)
        approve_event(termination, actor=self.admin)

        self.assertEqual(state_as_of("E-100", date(2022, 1, 1))["employment_status"], "SUSPENDED")
        self.assertEqual(state_as_of("E-100", date(2023, 1, 1))["employment_status"], "ACTIVE")
        self.assertEqual(state_as_of("E-100", date(2024, 1, 1))["employment_status"], "TERMINATED")

    def test_transfer_requires_relief_and_receiving_society_acceptance(self):
        self.appoint()
        transfer = self.create_event(
            "TRANSFER", date(2021, 1, 1), {"to_society_cen": "S-2"}
        )
        submit_event(transfer, actor=self.admin)
        workflow = TransferWorkflow.objects.get(event=transfer)
        self.assertEqual(workflow.from_society_cen, "S-1")
        with self.assertRaises(ValidationError):
            approve_event(transfer, actor=self.admin)

        relieve_transfer(workflow, actor=self.admin)
        accept_transfer(workflow, actor=self.admin)
        approve_event(transfer, actor=self.admin)
        self.assertEqual(state_as_of("E-100", date(2021, 1, 1))["society_cen"], "S-2")

    def test_probation_confirmation_requires_record_and_updates_snapshot(self):
        self.appoint()
        confirmation = self.create_event(
            "PROBATION_CONFIRMED", date(2021, 1, 1), {}
        )
        submit_event(confirmation, actor=self.admin)
        with self.assertRaises(ValidationError):
            approve_event(confirmation, actor=self.admin)

        probation = ProbationRecord(
            employee_cen="E-100",
            start_date=date(2020, 1, 1),
            expected_end_date=date(2021, 1, 1),
        )
        probation.full_clean()
        probation.save()
        approve_event(confirmation, actor=self.admin)
        self.assertEqual(
            ProbationRecord.objects.get(pk=probation.pk).status,
            ProbationRecord.Status.CONFIRMED,
        )

    def test_cancelled_probation_extension_restores_prior_record(self):
        self.appoint()
        probation = ProbationRecord(
            employee_cen="E-100",
            start_date=date(2020, 1, 1),
            expected_end_date=date(2021, 1, 1),
        )
        probation.full_clean()
        probation.save()
        extension = self.create_event(
            "PROBATION_EXTENDED",
            date(2021, 1, 1),
            {"new_end_date": "2021-06-01", "reason": "Additional review"},
        )
        submit_event(extension, actor=self.admin)
        approve_event(extension, actor=self.admin)
        self.assertEqual(
            ProbationRecord.objects.get(pk=probation.pk).expected_end_date,
            date(2021, 6, 1),
        )

        cancel_event(extension, actor=self.admin, reason="Entered in error")
        probation.refresh_from_db()
        self.assertEqual(probation.status, ProbationRecord.Status.ACTIVE)
        self.assertEqual(probation.expected_end_date, date(2021, 1, 1))

    def test_cancellation_preserves_history_and_never_deletes_event(self):
        event = self.appoint()
        cancel_event(event, actor=self.admin, reason="Entered in error")

        self.assertEqual(state_as_of("E-100", date(2020, 1, 1))["designation_id"], self.junior.pk)
        self.assertIsNone(state_as_of("E-100", date.today())["designation_id"])
        self.assertEqual(ServiceEvent.objects.get(pk=event.pk).status, ServiceEvent.Status.CANCELLED)
        with self.assertRaises(ValidationError):
            ServiceEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(ServiceEvent.objects.filter(pk=event.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="cancelled").exists())

    def test_approved_event_cannot_be_edited_and_lock_blocks_cancellation(self):
        event = self.appoint()
        set_event_lock(event, locked=True, actor=self.admin)
        with self.assertRaises(ValidationError):
            cancel_event(event, actor=self.admin, reason="Correction")
        set_event_lock(event, locked=False, actor=self.admin)
        event.payload["pay_amount"] = "26000"
        with self.assertRaises(ValidationError):
            event.save()

    def test_older_event_must_be_cancelled_after_later_events(self):
        appointment = self.appoint()
        promotion = self.create_event(
            "PROMOTION", date(2022, 1, 1), {"designation_id": self.senior.pk}
        )
        submit_event(promotion, actor=self.admin)
        approve_event(promotion, actor=self.admin)

        with self.assertRaises(ValidationError):
            cancel_event(appointment, actor=self.admin, reason="Correction")
        cancel_event(promotion, actor=self.admin, reason="Correction")
        cancel_event(appointment, actor=self.admin, reason="Correction")

    def test_event_json_is_validated_per_type(self):
        event = self.create_event("APPOINTMENT", date(2020, 1, 1), {"society_cen": "S-1"})
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_locked_acr_cannot_be_edited_until_unlocked(self):
        acr = ACRRecord.objects.create(
            employee_cen="E-100",
            period_start=date(2020, 1, 1),
            period_end=date(2020, 12, 31),
            rating="Excellent",
        )
        ACRRecord.objects.filter(pk=acr.pk).update(is_locked=True)
        acr.refresh_from_db()
        acr.rating = "Good"
        with self.assertRaises(ValidationError):
            acr.save()


class ServiceBookAPITests(APITestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin = get_user_model().objects.create_user(
            username="service-api-admin", password="test-password", is_staff=True
        )
        self.designation = Designation.objects.create(code="API", name="API Designation", level=1)
        self.scale = PayScale.objects.create(
            code="API-SCALE",
            min_pay=Decimal("25000"),
            max_pay=Decimal("40000"),
            increment_steps=[500],
            revision_order=1,
            effective_date=date(2020, 1, 1),
        )

    def test_module3_api_requires_staff_and_rejects_event_deletion(self):
        url = reverse("service-event-list")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(user=self.admin)
        create = self.client.post(
            url,
            {
                "employee_cen": "E-API",
                "event_type": "APPOINTMENT",
                "effective_date": "2020-01-01",
                "payload": {
                    "designation_id": self.designation.pk,
                    "pay_scale_id": self.scale.pk,
                    "pay_amount": "25000",
                    "society_cen": "S-API",
                },
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(self.client.delete(f"{url}{create.data['id']}/").status_code, 405)

    def test_employee_profile_api_is_staff_only_and_persists_real_details(self):
        url = reverse("employee-profile-list")
        payload = {
            "employee_cen": "E-PROFILE",
            "full_name": "Asha Employee",
            "date_of_birth": "1990-04-12",
            "department": "Operations",
            "email": "asha@example.test",
            "phone": "+91 9876543210",
        }

        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(url, payload, format="json")

        self.assertEqual(created.status_code, 201, created.data)
        profile = EmployeeServiceProfile.objects.get(employee_cen="E-PROFILE")
        self.assertEqual(profile.full_name, "Asha Employee")
        self.assertEqual(created.data["date_of_birth"], "1990-04-12")
        self.assertEqual(self.client.get(url, {"employee_cen": "E-PROFILE"}).data[0]["id"], profile.pk)

        updated = self.client.patch(
            reverse("employee-profile-detail", args=(profile.pk,)),
            {"department": "Finance"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["department"], "Finance")

    def test_api_approval_and_historical_state(self):
        self.client.force_authenticate(user=self.admin)
        create = self.client.post(
            reverse("service-event-list"),
            {
                "employee_cen": "E-API",
                "event_type": "APPOINTMENT",
                "effective_date": "2020-01-01",
                "payload": {
                    "designation_id": self.designation.pk,
                    "pay_scale_id": self.scale.pk,
                    "pay_amount": "25000",
                    "society_cen": "S-API",
                },
            },
            format="json",
        )
        event_url = reverse("service-event-detail", args=(create.data["id"],))
        self.assertEqual(self.client.post(f"{event_url}submit/").status_code, 200)
        self.assertEqual(self.client.post(f"{event_url}approve/").status_code, 200)
        signature = self.client.get(f"{event_url}signature/")
        self.assertEqual(signature.status_code, 200)
        self.assertEqual(signature.data["provider"], "dummy-sha256")
        response = self.client.get(
            reverse("service-state"), {"employee_cen": "E-API", "date": "2020-01-01"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["designation_id"], self.designation.pk)
        self.assertIn("event_ids", response.data)

    def test_acr_lock_endpoint_prevents_subsequent_edits(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse("acr-record-list"),
            {
                "employee_cen": "E-ACR",
                "period_start": "2020-01-01",
                "period_end": "2020-12-31",
                "rating": "Excellent",
                "details": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        detail = reverse("acr-record-detail", args=(response.data["id"],))
        self.assertEqual(self.client.post(f"{detail}lock/").status_code, 200)
        update = self.client.patch(detail, {"rating": "Good"}, format="json")
        self.assertEqual(update.status_code, 400)

    def test_scanned_document_upload_and_download_require_staff(self):
        self.client.force_authenticate(user=self.admin)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            upload = self.client.post(
                reverse("scanned-service-book-list"),
                {
                    "employee_cen": "E-DOC",
                    "title": "Original service book",
                    "file": SimpleUploadedFile("service-book.pdf", b"sample document"),
                },
                format="multipart",
            )
            self.assertEqual(upload.status_code, 201, upload.data)
            self.assertEqual(len(upload.data["sha256"]), 64)
            download = self.client.get(
                reverse("scanned-service-book-download", args=(upload.data["id"],))
            )
            self.assertEqual(download.status_code, 200)
            self.assertEqual(b"".join(download.streaming_content), b"sample document")
