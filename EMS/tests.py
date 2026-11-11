from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from EMS.factories import DesignationFactory, PayScaleFactory
from EMS.models import Designation


class HomePageTests(TestCase):
    def test_home_page_renders_service_book_management_workspace(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "EMS/home.html")
        for label in (
            "CEMS",
            "Service book",
            "Employee details",
            "Service history",
            "Designation & pay",
            "Recruitment & joining",
            "Probation details",
            "Scanned service book",
            "ACR records",
            "Designations & pay scales",
            "Drafts & approvals",
            "Staff sign in",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)
        self.assertContains(response, "service_book.js")
        self.assertContains(response, 'id="event-form"')
        self.assertContains(response, 'id="profile-form"')

    def test_staff_session_receives_service_book_workspace(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="service-book-ui-staff",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-staff="true"')
        self.assertContains(response, "/admin/logout/")
        self.assertNotContains(response, "Staff sign-in required")


class CatalogModelTests(TestCase):
    def test_designation_factory_creates_active_designation(self):
        designation = DesignationFactory()

        self.assertTrue(designation.is_active)
        self.assertEqual(str(designation), f"{designation.code} - {designation.name}")

    def test_designation_code_is_unique(self):
        designation = DesignationFactory()

        with self.assertRaises(IntegrityError), transaction.atomic():
            DesignationFactory(code=designation.code)

    def test_pay_scale_factory_creates_expected_values(self):
        pay_scale = PayScaleFactory()

        self.assertEqual(pay_scale.min_pay, 25000)
        self.assertEqual(pay_scale.increment_steps, [500, 750])
        self.assertEqual(str(pay_scale), pay_scale.code)

    def test_pay_scale_code_is_unique(self):
        pay_scale = PayScaleFactory()

        with self.assertRaises(IntegrityError), transaction.atomic():
            PayScaleFactory(code=pay_scale.code)

    def test_pay_scale_rejects_non_list_increment_steps(self):
        pay_scale = PayScaleFactory.build(increment_steps=500)

        with self.assertRaises(ValidationError):
            pay_scale.full_clean()

    def test_pay_scale_rejects_non_numeric_increment_steps(self):
        pay_scale = PayScaleFactory.build(increment_steps=[500, "750"])

        with self.assertRaises(ValidationError):
            pay_scale.full_clean()

    def test_pay_scale_rejects_boolean_increment_steps(self):
        pay_scale = PayScaleFactory.build(increment_steps=[True])

        with self.assertRaises(ValidationError):
            pay_scale.full_clean()

    def test_pay_scale_rejects_non_finite_increment_steps(self):
        for step in (float("inf"), float("nan")):
            with self.subTest(step=step):
                pay_scale = PayScaleFactory.build(increment_steps=[step])

                with self.assertRaises(ValidationError):
                    pay_scale.full_clean()

    def test_pay_scale_rejects_minimum_above_maximum(self):
        pay_scale = PayScaleFactory.build(min_pay=50000, max_pay=25000)

        with self.assertRaises(ValidationError):
            pay_scale.full_clean()

    def test_pay_scale_database_constraint_rejects_minimum_above_maximum(self):
        pay_scale = PayScaleFactory.build(min_pay=50000, max_pay=25000)

        with self.assertRaises(IntegrityError), transaction.atomic():
            pay_scale.save()


class CatalogAPITests(APITestCase):
    designation_url = "/api/designations/"
    pay_scale_url = "/api/pay-scales/"

    def test_catalogs_are_readable_without_authentication(self):
        designation = DesignationFactory()
        pay_scale = PayScaleFactory()

        designation_response = self.client.get(self.designation_url)
        pay_scale_response = self.client.get(self.pay_scale_url)

        self.assertEqual(designation_response.status_code, 200)
        self.assertEqual(designation_response.data[0]["id"], designation.id)
        self.assertEqual(pay_scale_response.status_code, 200)
        self.assertEqual(pay_scale_response.data[0]["id"], pay_scale.id)
        self.assertEqual(pay_scale_response.data[0]["increment_steps"], [500, 750])

    def test_anonymous_users_cannot_modify_catalogs(self):
        payload = {"code": "NEW", "name": "New designation"}

        response = self.client.post(self.designation_url, payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Designation.objects.filter(code="NEW").exists())

    def test_non_staff_users_cannot_modify_catalogs(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="employee", password="test")
        self.client.force_authenticate(user=user)

        response = self.client.post(
            self.designation_url,
            {"code": "NEW", "name": "New designation"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_users_can_create_and_update_catalogs(self):
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_user(
            username="catalog-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        create_response = self.client.post(
            self.designation_url,
            {
                "code": "SEC",
                "name": "Secretary",
                "description": "Administrative designation",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        designation_id = create_response.data["id"]
        update_response = self.client.patch(
            f"{self.designation_url}{designation_id}/",
            {"description": "Updated description"},
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["description"], "Updated description")

    def test_staff_users_can_create_valid_pay_scale(self):
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_user(
            username="pay-scale-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.post(
            self.pay_scale_url,
            {
                "code": "PS-1",
                "min_pay": "25000.00",
                "max_pay": "50000.00",
                "increment_steps": [500, 750],
                "revision_order": 1,
                "effective_date": "2026-01-01",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["increment_steps"], [500, 750])

    def test_api_rejects_duplicate_designation_code(self):
        DesignationFactory(code="DUP")
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_user(
            username="duplicate-code-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.post(
            self.designation_url,
            {"code": "DUP", "name": "Duplicate"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.data)

    def test_api_rejects_malformed_increment_steps(self):
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_user(
            username="malformed-scale-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.post(
            self.pay_scale_url,
            {
                "code": "PS-MALFORMED",
                "min_pay": "25000.00",
                "max_pay": "50000.00",
                "increment_steps": [500, "750"],
                "revision_order": 1,
                "effective_date": "2026-01-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("increment_steps", response.data)

    def test_pay_scale_api_rejects_minimum_above_maximum(self):
        from django.contrib.auth import get_user_model

        admin_user = get_user_model().objects.create_user(
            username="invalid-pay-scale-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.post(
            self.pay_scale_url,
            {
                "code": "PS-INVALID",
                "min_pay": "50000.00",
                "max_pay": "25000.00",
                "increment_steps": [500],
                "revision_order": 1,
                "effective_date": "2026-01-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum pay", str(response.data))

    def test_catalogs_do_not_expose_delete_operations(self):
        from django.contrib.auth import get_user_model

        designation = DesignationFactory()
        admin_user = get_user_model().objects.create_user(
            username="delete-test-admin",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.delete(f"{self.designation_url}{designation.id}/")

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Designation.objects.filter(pk=designation.pk).exists())
