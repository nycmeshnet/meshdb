import logging
import sys
from argparse import ArgumentParser
from datetime import date, timedelta
from random import randint, randrange
from typing import Any, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from meshapi.models import LOS, Install, Member
from meshapi.models.building import Building
from meshapi.models.devices.device import Device
from meshapi.models.link import Link
from meshapi.models.node import Node

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


# Uses faker to get fake names, emails, and phone numbers
class Command(BaseCommand):
    help = "Updates all members with fake name, email, and phone number. Clears notes."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--noinput", action="store_true", help="Tells Django to NOT prompt the user for input of any kind."
        )
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

    def handle(self, *args: Any, **options: Any) -> None:
        logging.info("Scrambling database with fake information")

        # Confirm with user
        if not options["noinput"]:
            should_continue = input("WARNING: This is destructive. Are you sure? (y/N): ")
            logging.info(should_continue)
            if should_continue.lower() != "yes" and should_continue.lower() != "y":
                logging.warning("Operation cancelled.")
                return

        logging.info("Continuing with scramble operation!!!")

        fake = Faker()
        if not options["skip_members"]:
            logging.info("Scrambling members...")
            with transaction.atomic():
                members = Member.objects.all()
                for member in members:
                    member.name = fake.name()
                    member.primary_email_address = f"{member.name.replace(' ', '').lower()}@gmail.com"
                    member.stripe_email_address = ""
                    member.additional_email_addresses = []
                    member.phone_number = fake.phone_number()
                    member.additional_phone_numbers = [] if randint(0, 100) > 0 else [fake.phone_number()]
                    member.slack_handle = ""
                    member.notes = fake.text()
                    member.save()

        if not options["skip_installs"]:
            logging.info("Scrambling installs...")
            with transaction.atomic():
                installs = Install.objects.all()
                for install in installs:
                    install.unit = randrange(100)
                    install.notes = fake.text()
                    install.request_date, install.install_date, install.abandon_date = self.fuzz_dates(
                        install.request_date, install.install_date, install.abandon_date
                    )
                    install.save()

        logging.info("Scrambling all other notes and dates")

        logging.info("Scrambling buildings...")
        with transaction.atomic():
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

        logging.info("Scrambling devices...")
        with transaction.atomic():
            devices = Device.objects.all()
            for device in devices:
                device.notes = fake.text()
                _, device.install_date, device.abandon_date = self.fuzz_dates(
                    date.today(), device.install_date, device.abandon_date
                )
                device.save()

        logging.info("Scrambling links...")
        with transaction.atomic():
            links = Link.objects.all()
            for link in links:
                link.notes = fake.text()
                _, link.install_date, link.abandon_date = self.fuzz_dates(
                    date.today(), link.install_date, link.abandon_date
                )
                link.save()

        logging.info("Scrambling nodes...")
        with transaction.atomic():
            nodes = Node.objects.all()
            for node in nodes:
                node.notes = fake.text()
                _, node.install_date, node.abandon_date = self.fuzz_dates(
                    date.today(), node.install_date, node.abandon_date
                )
                node.save()

        logging.info("Scrambling LOSes...")
        with transaction.atomic():
            LOSes = LOS.objects.all()
            for los in LOSes:
                los.notes = fake.text()
                los.save()

        logging.info("Done")

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
