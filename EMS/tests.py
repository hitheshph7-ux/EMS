
from datetime import date

from django.test import TestCase

from .models import Employee


class EmployeeModelTests(TestCase):

    def create_employee(self, **overrides):
        data = {
            "full_name": "Arun Test Employee",
            "date_of_birth": date(1998, 5, 12),
            "gender": Employee.Gender.MALE,
            "mobile": "9000000001",
            "email": "arun.test@example.com",
        }
        data.update(overrides)
        return Employee.objects.create(**data)

    def test_employee_gets_cen_automatically(self):
        employee = self.create_employee()

        self.assertEqual(employee.cen, "CEN000001")

    def test_each_employee_gets_a_unique_cen(self):
        first = self.create_employee()

        second = self.create_employee(
            full_name="Second Test Employee",
            mobile="9000000002",
            email="second.test@example.com",
        )

        self.assertEqual(first.cen, "CEN000001")
        self.assertEqual(second.cen, "CEN000002")
        self.assertNotEqual(first.cen, second.cen)

    def test_employee_details_can_be_updated(self):
        employee = self.create_employee()

        employee.full_name = "Arun Updated Employee"
        employee.save()
        employee.refresh_from_db()

        self.assertEqual(
            employee.full_name,
            "Arun Updated Employee",
        )

    def test_assigned_cen_cannot_be_changed(self):
        employee = self.create_employee(cen="CEN999999")

        employee.cen = "CEN888888"

        with self.assertRaisesMessage(
            ValueError,
            "An assigned CEN cannot be changed.",
        ):
            employee.save()

        employee.refresh_from_db()

        self.assertEqual(employee.cen, "CEN999999")

    def test_changing_status_does_not_change_cen(self):
        employee = self.create_employee()
        original_cen = employee.cen

        employee.status = "ACTIVE"
        employee.save()
        employee.refresh_from_db()

        self.assertEqual(employee.cen, original_cen)
        self.assertEqual(employee.status, "ACTIVE")
