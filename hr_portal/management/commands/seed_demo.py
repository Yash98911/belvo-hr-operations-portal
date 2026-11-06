from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from hr_portal.models import AttendanceEntry, LeaveEntry, Onboarding, Person


class Command(BaseCommand):
    help = "Create a small set of fictional demo records for a local walkthrough."

    def handle(self, *args, **options):
        examples = [
            {
                "full_name": "Aarav Mehta",
                "role_department": "Product · Design",
                "reporting_person": "Mira Shah",
                "start_date": date.today() + timedelta(days=3),
                "person_status": Person.Status.ONBOARDING,
                "onboarding_status": Onboarding.Status.IN_PROGRESS,
            },
            {
                "full_name": "Diya Kapoor",
                "role_department": "Engineering · Platform",
                "reporting_person": "Rohan Iyer",
                "start_date": date.today() - timedelta(days=45),
                "person_status": Person.Status.ACTIVE,
                "onboarding_status": Onboarding.Status.COMPLETED,
            },
        ]
        people = {}
        for item in examples:
            person, _ = Person.objects.get_or_create(
                full_name=item["full_name"],
                defaults={
                    "role_department": item["role_department"],
                    "reporting_person": item["reporting_person"],
                    "start_date": item["start_date"],
                    "status": item["person_status"],
                },
            )
            people[item["full_name"]] = person
            onboarding_defaults = {
                "status": item["onboarding_status"],
                "assigned_hr_owner": "Belvo HR",
                "due_date": item["start_date"] + timedelta(days=7),
                "details_collected": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "documents_received": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "nda_issued_signed": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "joining_communication": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "access_requested": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "introduction_completed": item["onboarding_status"] == Onboarding.Status.COMPLETED,
                "onboarding_marked_complete": item["onboarding_status"] == Onboarding.Status.COMPLETED,
            }
            Onboarding.objects.get_or_create(person=person, defaults=onboarding_defaults)

        self.stdout.write(self.style.SUCCESS(f"Demo data ready for {len(people)} fictional people."))
