
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, UserRoleAssignment

User = get_user_model()


class AccountAuthenticationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.password = "StrongPass!123"

        self.user = User.objects.create_user(
            username="testuser",
            mobile_number="9876543210",
            password=self.password,
            must_change_password=False,
        )

    def test_login_with_username(self):
        response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_mobile_number(self):
        response = self.client.post(
            "/api/auth/login",
            {
                "mobile_number": "9876543210",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_login_with_wrong_password(self):
        response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_account_locks_after_five_failed_attempts(self):
        for attempt in range(5):
            response = self.client.post(
                "/api/auth/login",
                {
                    "username": "testuser",
                    "password": "WrongPassword123!",
                },
                format="json",
            )

        self.user.refresh_from_db()

        self.assertTrue(self.user.is_locked)
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertEqual(response.status_code, 403)

    def test_locked_account_cannot_login(self):
        self.user.is_locked = True
        self.user.save()

        response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_successful_login_resets_failed_attempts(self):
        self.user.failed_login_attempts = 2
        self.user.save()

        response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_first_login_requires_password_change(self):
        self.user.must_change_password = True
        self.user.save()

        response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["must_change_password"])
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_password_change_with_temporary_token(self):
        self.user.must_change_password = True
        self.user.save()

        login_response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/auth/password/change",
            {
                "current_password": self.password,
                "new_password": "NewStrongPass!456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(
            self.user.check_password("NewStrongPass!456")
        )

    def test_current_user_profile(self):
        login_response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {login_response.data['access']}"
            )
        )

        response = self.client.get("/api/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "testuser")

    def test_current_user_requires_authentication(self):
        response = self.client.get("/api/me")

        self.assertEqual(response.status_code, 401)

    def test_refresh_token(self):
        login_response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        response = self.client.post(
            "/api/auth/refresh",
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(
            "/api/auth/login",
            {
                "username": "testuser",
                "password": self.password,
            },
            format="json",
        )

        refresh_token = login_response.data["refresh"]

        logout_response = self.client.post(
            "/api/auth/logout",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(logout_response.status_code, 200)

        refresh_response = self.client.post(
            "/api/auth/refresh",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, 401)

    def test_role_assignment(self):
        role = Role.objects.create(name="Employee")

        assignment = UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
        )

        self.assertEqual(assignment.user, self.user)
        self.assertEqual(assignment.role.name, "Employee")
