import logging
import sys
from argparse import ArgumentParser
from datetime import date, timedelta
from random import randint, randrange
from typing import Any, Optional, Tuple

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from meshapi.models import LOS, Install, Member
from meshapi.models.billing import InstallFeeBillingDatum
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
        parser.add_argument(
            "--skip-buildings",
            action="store_true",
            help="Skip scrambling buildings",
        )
        parser.add_argument(
            "--skip-devices",
            action="store_true",
            help="Skip scrambling devices",
        )
        parser.add_argument(
            "--skip-links",
            action="store_true",
            help="Skip scrambling links",
        )
        parser.add_argument(
            "--skip-nodes",
            action="store_true",
            help="Skip scrambling nodes",
        )
        parser.add_argument(
            "--skip-loses",
            action="store_true",
            help="Skip scrambling LOSes",
        )
        parser.add_argument(
            "--skip-users",
            action="store_true",
            help="Skip deleting all users",
        )
        parser.add_argument(
            "--skip-historical",
            action="store_true",
            help="Skip deleting all historical records",
        )
        parser.add_argument(
            "--skip-sessions",
            action="store_true",
            help="Skip truncating django_session table",
        )
        parser.add_argument(
            "--skip-billing",
            action="store_true",
            help="Skip truncating install fee billing data",
        )
        parser.add_argument(
            "--skip-explorer",
            action="store_true",
            help="Skip truncating explorer tables",
        )
        parser.add_argument(
            "--skip-silk",
            action="store_true",
            help="Skip truncating silk tables",
        )
        parser.add_argument(
            "--skip-admin-log",
            action="store_true",
            help="Skip truncating django_admin_log",
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
                    install.referral = fake.text()
                    install.stripe_subscription_id = ""
                    install.request_date, install.install_date, install.abandon_date = self.fuzz_dates(
                        install.request_date, install.install_date, install.abandon_date
                    )
                    install.save()

        logging.info("Scrambling all other notes and dates")

        if not options["skip_buildings"]:
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

        if not options["skip_devices"]:
            logging.info("Scrambling devices...")
            with transaction.atomic():
                devices = Device.objects.all()
                for device in devices:
                    device.notes = fake.text()
                    _, device.install_date, device.abandon_date = self.fuzz_dates(
                        date.today(), device.install_date, device.abandon_date
                    )
                    device.save()

        if not options["skip_links"]:
            logging.info("Scrambling links...")
            with transaction.atomic():
                links = Link.objects.all()
                for link in links:
                    link.notes = fake.text()
                    _, link.install_date, link.abandon_date = self.fuzz_dates(
                        date.today(), link.install_date, link.abandon_date
                    )
                    link.save()

        if not options["skip_nodes"]:
            logging.info("Scrambling nodes...")
            with transaction.atomic():
                nodes = Node.objects.all()
                for node in nodes:
                    node.notes = fake.text()
                    _, node.install_date, node.abandon_date = self.fuzz_dates(
                        date.today(), node.install_date, node.abandon_date
                    )
                    node.save()

        if not options["skip_loses"]:
            logging.info("Scrambling LOSes...")
            with transaction.atomic():
                LOSes = LOS.objects.all()
                for los in LOSes:
                    los.notes = fake.text()
                    los.save()

        if not options["skip_users"]:
            logging.info("Deleting all users...")
            with transaction.atomic():
                User.objects.all().delete()
                logging.info("All users deleted.")

        if not options["skip_historical"]:
            logging.info("Deleting all historical records...")
            with transaction.atomic():
                apps = __import__("django.apps", fromlist=["apps"])
                historical_models = [
                    model for model in apps.apps.get_models() if model.__name__.startswith("Historical")
                ]
                for model in historical_models:
                    count = model.objects.all().count()
                    model.objects.all().delete()
                    logging.info(f"Deleted {count} historical records from {model.__name__}")
                logging.info("All historical records deleted.")

        if not options["skip_sessions"]:
            logging.info("Truncating django_session table...")
            with transaction.atomic():
                from django.contrib.sessions.models import Session

                count = Session.objects.all().count()
                Session.objects.all().delete()
                logging.info(f"Deleted {count} session records.")

        if not options["skip_billing"]:
            logging.info("Truncating install fee billing data...")
            with transaction.atomic():
                count = InstallFeeBillingDatum.objects.all().count()
                InstallFeeBillingDatum.objects.all().delete()
                logging.info(f"Deleted {count} billing records.")

        if not options["skip_explorer"]:
            logging.info("Truncating explorer tables...")
            with transaction.atomic():
                apps = __import__("django.apps", fromlist=["apps"])
                explorer_models = [model for model in apps.apps.get_models() if model.__module__.startswith("explorer")]
                for model in explorer_models:
                    count = model.objects.all().count()
                    model.objects.all().delete()
                    logging.info(f"Deleted {count} records from {model.__name__}")
                logging.info("All explorer tables truncated.")

        if not options["skip_silk"]:
            logging.info("Truncating silk tables...")
            with transaction.atomic():
                apps = __import__("django.apps", fromlist=["apps"])
                silk_models = [model for model in apps.apps.get_models() if model.__module__.startswith("silk")]
                for model in silk_models:
                    count = model.objects.all().count()
                    model.objects.all().delete()
                    logging.info(f"Deleted {count} records from {model.__name__}")
                logging.info("All silk tables truncated.")

        if not options["skip_admin_log"]:
            logging.info("Truncating django_admin_log...")
            with transaction.atomic():
                from django.contrib.admin.models import LogEntry

                count = LogEntry.objects.all().count()
                LogEntry.objects.all().delete()
                logging.info(f"Deleted {count} admin log entries.")

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
