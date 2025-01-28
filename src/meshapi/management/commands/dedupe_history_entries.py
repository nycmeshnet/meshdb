from argparse import ArgumentParser
import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db import models, transaction

from meshapi.models.devices.device import Device
from meshapi.models.link import Link
from meshapi.models.los import LOS


class Command(BaseCommand):
    help = "Deletes duplicate history entries on history tables"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        self.deduplicate_history(Link.objects.all())
        self.deduplicate_history(Device.objects.all())
        self.deduplicate_history(LOS.objects.all())

    def deduplicate_history(self, model_objects: models.QuerySet):
        for m in model_objects:
            logging.info(f"{m.id}, {m}")
            # Delete history from each object. Atomic block makes it go faster
            with transaction.atomic():
                try:
                    history = m.history.all()
                    # If there's no history, bail
                    if not history:
                        continue
                    # This is the history object that last changed something
                    last_meaningful_history = None
                    for h in history:
                        # Grab the first history object we come across
                        if not last_meaningful_history:
                            last_meaningful_history = h
                            continue
                        delta = last_meaningful_history.diff_against(
                            h, 
                            foreign_keys_are_objs=False # This makes foreign keys show up as UUIDs
                        )
                        # If there were fields that changed meaningfully, then
                        # track that by updating last_meaningful_history and
                        # keep going
                        if delta.changes or delta.changed_fields:
                            logging.info(f"Preserving Change: {delta}")
                            last_meaningful_history = h
                            continue

                        # Otherwise, delete the history object
                        h.delete()

                except Exception as e:
                    logging.exception(f"Could not get history for this link: {e}")
                    raise e
            #input("Press any key.")
