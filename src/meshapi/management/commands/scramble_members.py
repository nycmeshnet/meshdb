from random import randrange

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from meshapi.models import Install, Member
from meshapi.models.building import Building
from meshapi.models.devices.device import Device
from meshapi.models.link import Link
from meshapi.models.node import Node


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

    @transaction.atomic
    def handle(self, *args, **options):
        print("Scrambling database with fake information...")
        fake = Faker()
        if not options["skip_members"]:
            members = Member.objects.all()
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
                # print(f"{member.id} - {member.name}")

        if not options["skip_installs"]:
            print("Scrambling installs...")
            installs = Install.objects.all()
            for install in installs:
                install.unit = randrange(100)
                install.notes = fake.text()
                install.save()
                # print(install.install_number)

        print("Scrambling all other notes...")
        buildings = Building.objects.all()
        for building in buildings:
            building.notes = fake.text()
            building.save()
            # print(building)

        devices = Device.objects.all()
        for device in devices:
            device.notes = fake.text()
            device.save()
            # print(device)

        links = Link.objects.all()
        for link in links:
            link.notes = fake.text()
            link.save()
            # print(link)

        nodes = Node.objects.all()
        for node in nodes:
            node.notes = fake.text()
            node.save()
            # print(node)

        print("Done")
