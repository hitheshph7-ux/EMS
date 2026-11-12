
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, UserRoleAssignment, AuditLog
from societies.models import District, SocietyType, Society

User = get_user_model()


class SocietyModuleTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.district = District.objects.create(
            name="Thrissur"
        )

        self.society_type = SocietyType.objects.create(
            name="PACS"
        )

        self.society = Society.objects.create(
            registration_number="TEST-001",
            name="Test Cooperative Society",
            address="Thrissur, Kerala",
            society_type=self.society_type,
            district=self.district,
            status="ACTIVE",
        )

        self.user = User.objects.create_user(
            username="normaluser",
            password="StrongPass!123",
            must_change_password=False,
        )

        self.admin = User.objects.create_superuser(
    username="adminuser",
    password="StrongPass!123",
    email="admin@example.com",
    must_change_password=False,
)

    def test_district_list_requires_authentication(self):
        response = self.client.get("/api/masters/districts")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_view_districts(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/masters/districts")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_authenticated_user_can_view_society_types(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/masters/society-types")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_authenticated_user_can_view_societies(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/societies")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_superuser_can_create_society(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/societies",
            {
                "registration_number": "TEST-002",
                "name": "New Cooperative Society",
                "address": "Palakkad, Kerala",
                "society_type": self.society_type.id,
                "district": self.district.id,
                "status": "ACTIVE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Society.objects.filter(
                registration_number="TEST-002"
            ).exists()
        )

        audit = AuditLog.objects.filter(
            action="CREATE",
            model_name="Society",
        ).first()

        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin)

    def test_normal_user_cannot_create_society(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/societies",
            {
                "registration_number": "TEST-003",
                "name": "Unauthorized Society",
                "address": "Kerala",
                "society_type": self.society_type.id,
                "district": self.district.id,
                "status": "ACTIVE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_department_officer_is_read_only(self):
        role = Role.objects.create(name="Department Officer")

        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/societies",
            {
                "registration_number": "TEST-004",
                "name": "Officer Test Society",
                "address": "Kerala",
                "society_type": self.society_type.id,
                "district": self.district.id,
                "status": "ACTIVE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_retrieve_society(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            f"/api/societies/{self.society.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["registration_number"],
            "TEST-001",
        )

    def test_superuser_can_update_society(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.put(
            f"/api/societies/{self.society.id}",
            {
                "registration_number": "TEST-001",
                "name": "Updated Cooperative Society",
                "address": "Updated Address",
                "society_type": self.society_type.id,
                "district": self.district.id,
                "status": "ACTIVE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.society.refresh_from_db()
        self.assertEqual(
            self.society.name,
            "Updated Cooperative Society",
        )

        self.assertTrue(
            AuditLog.objects.filter(
                action="UPDATE",
                model_name="Society",
                actor=self.admin,
            ).exists()
        )

    def test_superuser_can_delete_society(self):
        self.client.force_authenticate(user=self.admin)

        society_id = self.society.id

        response = self.client.delete(
            f"/api/societies/{society_id}"
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Society.objects.filter(id=society_id).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                action="DELETE",
                model_name="Society",
                object_id=str(society_id),
                actor=self.admin,
            ).exists()
        )

    def test_society_not_found(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/societies/99999")

        self.assertEqual(response.status_code, 404)
