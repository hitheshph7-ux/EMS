
from django.core.management.base import BaseCommand

from societies.models import (
    District,
    SocietyType,
    Board,
    Society,
)


class Command(BaseCommand):
    help = "Seed CEMS master data and 10 sample societies"

    def handle(self, *args, **options):
        self.seed_districts()
        self.seed_society_types()
        self.seed_boards()
        self.seed_societies()

        self.stdout.write(
            self.style.SUCCESS(
                "CEMS master data and sample societies seeded successfully."
            )
        )

    def seed_districts(self):
        districts = [
            "Thiruvananthapuram",
            "Kollam",
            "Pathanamthitta",
            "Alappuzha",
            "Kottayam",
            "Idukki",
            "Ernakulam",
            "Thrissur",
            "Palakkad",
            "Malappuram",
            "Kozhikode",
            "Wayanad",
            "Kannur",
            "Kasaragod",
        ]

        for name in districts:
            District.objects.get_or_create(name=name)

        self.stdout.write("14 districts seeded.")

    def seed_society_types(self):
        society_types = [
            "PACS",
            "Urban Co-operative Bank",
            "Housing",
            "Consumer",
            "Labour",
            "Dairy",
        ]

        for name in society_types:
            SocietyType.objects.get_or_create(name=name)

        self.stdout.write("6 society types seeded.")

    def seed_boards(self):
        boards = [
            "Pension",
            "Welfare",
            "Examination",
        ]

        for name in boards:
            Board.objects.get_or_create(name=name)

        self.stdout.write("3 boards seeded.")

    def seed_societies(self):
        sample_societies = [
            ("CEMS-DEMO-001", "Demo PACS Thiruvananthapuram", "PACS", "Thiruvananthapuram"),
            ("CEMS-DEMO-002", "Demo Urban Bank Kollam", "Urban Co-operative Bank", "Kollam"),
            ("CEMS-DEMO-003", "Demo Housing Society Pathanamthitta", "Housing", "Pathanamthitta"),
            ("CEMS-DEMO-004", "Demo Consumer Society Alappuzha", "Consumer", "Alappuzha"),
            ("CEMS-DEMO-005", "Demo Labour Society Kottayam", "Labour", "Kottayam"),
            ("CEMS-DEMO-006", "Demo Dairy Society Idukki", "Dairy", "Idukki"),
            ("CEMS-DEMO-007", "Demo PACS Ernakulam", "PACS", "Ernakulam"),
            ("CEMS-DEMO-008", "Demo Urban Bank Thrissur", "Urban Co-operative Bank", "Thrissur"),
            ("CEMS-DEMO-009", "Demo Housing Society Palakkad", "Housing", "Palakkad"),
            ("CEMS-DEMO-010", "Demo Consumer Society Kozhikode", "Consumer", "Kozhikode"),
        ]

        for registration_number, name, type_name, district_name in sample_societies:
            society_type = SocietyType.objects.get(name=type_name)
            district = District.objects.get(name=district_name)

            Society.objects.get_or_create(
                registration_number=registration_number,
                defaults={
                    "name": name,
                    "society_type": society_type,
                    "district": district,
                    "address": f"Demo address, {district_name}, Kerala",
                    "status": Society.Status.ACTIVE,
                },
            )

        self.stdout.write("10 sample societies seeded.")
