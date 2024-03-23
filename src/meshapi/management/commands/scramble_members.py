from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from faker import Faker
from random import randrange

from meshapi.models import Member, Install


# Uses faker to get fake names, emails, and phone numbers
# TODO: Instead of modifying real data, generate a completely fake database from
# scratch :)
class Command(BaseCommand):
    help = "Updates all members with fake name, email, and phone number. Clears notes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-members",
            action="store_true",
            help="Skip scrambling members",
        )
        parser.add_argument(
            "--skip-installs",
            action="store_true",
            help="Skip scrambling installs",
        )

    def handle(self, *args, **options):
        print("Scrambling members...")
        members = Member.objects.all()
        fake = Faker()
        if not options["skip_members"]:
            print("Scrambling members...")
            for member in members:
                member.name = fake.name()
                member.primary_email_address = f"{member.name.replace(' ', '').lower()}@gmail.com"
                member.stripe_email_address = ""
                member.additional_email_addresses = []
                member.phone_number = fake.phone_number()
                member.slack_handle = ""
                member.notes = fake.text()
                member.save()
                print(f"{member.id} - {member.name}")

        if not options["skip_installs"]:
            print("Scrambling installs...")
            installs = Install.objects.all()
            for install in installs:
                install.unit = randrange(100)
                install.save()
                print(install.install_number)

        print("Done")
