from argparse import ArgumentParser
from datetime import date, timedelta
from random import randint, randrange
from typing import Any, Optional, Tuple

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

    def add_arguments(self, parser: ArgumentParser) -> None:
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
    def handle(self, *args: Any, **options: Any) -> None:
        print("Scrambling database with fake information")
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

        if not options["skip_installs"]:
            print("Scrambling installs...")
            installs = Install.objects.all()
            for install in installs:
                install.unit = randrange(100)
                install.notes = fake.text()
                install.request_date, install.install_date, install.abandon_date = self.fuzz_dates(
                    install.request_date, install.install_date, install.abandon_date
                )
                install.save()

        print("Scrambling all other notes and dates")

        print("Scrambling buildings...")
        buildings = Building.objects.all()
        for building in buildings:
            building.notes = fake.text()
            # Fuzz the street address, if possible
            if building.street_address:
                address = building.street_address.split(" ")
                if len(address) > 0:
                    try:
                        fuzzed_street_number = str(int(address[0]) + randint(1, 20))
                        street_name = " ".join(address[1:])
                        building.street_address = f"{fuzzed_street_number} {street_name}"
                    except ValueError:
                        pass

            building.save()

        print("Scrambling devices...")
        devices = Device.objects.all()
        for device in devices:
            device.notes = fake.text()
            _, device.install_date, device.abandon_date = self.fuzz_dates(
                date.today(), device.install_date, device.abandon_date
            )
            device.save()

        print("Scrambling links...")
        links = Link.objects.all()
        for link in links:
            link.notes = fake.text()
            _, link.install_date, link.abandon_date = self.fuzz_dates(
                date.today(), link.install_date, link.abandon_date
            )
            link.save()

        print("Scrambling nodes...")
        nodes = Node.objects.all()
        for node in nodes:
            node.notes = fake.text()
            _, node.install_date, node.abandon_date = self.fuzz_dates(
                date.today(), node.install_date, node.abandon_date
            )
            node.save()

        print("Done")

    @staticmethod
    def fuzz_dates(
        request_date: date,
        install_date: Optional[date],
        abandon_date: Optional[date],
    ) -> Tuple[date, Optional[date], Optional[date]]:
        if request_date:
            # Make it happen sooner so that there's no way the request date is
            # now beyond the install/abandon date.
            request_date -= timedelta(days=randint(14, 100))

        if install_date:
            install_date += timedelta(days=randint(14, 100))

        if abandon_date:
            abandon_date += timedelta(days=randint(100, 200))

        return request_date, install_date, abandon_date
