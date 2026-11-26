from django.core.management.base import BaseCommand
from accounts.models import Role

class Command(BaseCommand):
    help = "Seed standard CEMS roles"

    def handle(self, *args, **options):
        roles = [
            "Employee",
            "Society Admin",
            "Society Secretary",
            "Department Officer",
            "Board User",
        ]

        for role_name in roles:
            Role.objects.get_or_create(name=role_name)

        self.stdout.write(
            self.style.SUCCESS("CEMS roles seeded successfully.")
        )