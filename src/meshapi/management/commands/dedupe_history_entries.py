from argparse import ArgumentParser
import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db import models, transaction

from meshapi.models.devices.device import Device
from meshapi.models.link import Link


class Command(BaseCommand):
    help = "Deletes duplicate history entries on history tables"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        self.deduplicate_history(Link.objects.all())
        self.deduplicate_history(Device.objects.all())

    def deduplicate_history(self, model_objects: models.QuerySet):
        for m in model_objects:
            logging.info(f"{m.id}, {m}")

            # Delete history from each object
            # Atomic block makes it go faster
            with transaction.atomic():
                try:
                    history = m.history.all()
                    # If there's no history, bail
                    if not history:
                        continue
                    first_history = None
                    for h in history:
                        # Hacky way to preserve the first object
                        if not first_history:
                            first_history = h
                            continue
                        if not h.history_user_id:
                            #logging.info(f"Deleting history record with user_id = None: {h}")
                            h.delete()

                except Exception as e:
                    logging.exception(f"Could not get history for this link: {e}")
                    raise e

