from django.core.management.base import BaseCommand
from societies.models import District, SocietyType, Board

class Command(BaseCommand):
    help = "Seed CEMS master data"

    def handle(self,*args,**options):
        self.seed_districts()
        self.seed_society_types()
        self.seed_boards()

        self.stdout.write(
            self.style.SUCCESS("Master data seeded successfully. ")

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

        self.stdout.write("Districts seeded.")

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

        self.stdout.write("Society types seeded.")

    def seed_boards(self):
        boards = [
            "Pension",
            "Welfare",
            "Examination",
        ]

        for name in boards:
            Board.objects.get_or_create(name=name)

        self.stdout.write("Boards seeded.")
