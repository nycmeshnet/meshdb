import logging
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection, models, transaction

from meshapi.models.devices.device import Device
from meshapi.models.link import Link
from meshapi.models.los import LOS


class Command(BaseCommand):
    help = "Deletes duplicate history entries on history tables"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:

        field_query = f"({', '.join(field.name for field in Link._meta.fields)})"
        print(field_query)
        return

        for m in Link.objects.all():
            history_model = m.history.model
            table_name = history_model._meta.db_table

            # Delete history from each object. Atomic block makes it go faster
            with transaction.atomic():
                deleted_records = 0
                try:
                    history = m.history.all()
                    # If there's no history, bail
                    if not history:
                        continue
                    # This is the history object that last changed something
                    # XXX (wdn): I don't think I have a type I can put in here
                    # without some robot yelling at me
                    meaningful_history: list[Any] = []
                    for h in history:
                        # Grab the first history object we come across
                        if not meaningful_history:
                            meaningful_history.append(h)
                            continue
                        delta = meaningful_history[-1].diff_against(
                            h, foreign_keys_are_objs=False  # This makes foreign keys show up as UUIDs
                        )
                        # If there were fields that changed meaningfully, then
                        # track that by updating last_meaningful_history and
                        # keep going
                        if delta.changes or delta.changed_fields:
                            #logging.info(f"Preserving Change: {delta}")
                            meaningful_history.append(h)
                            continue

                        # Otherwise, delete the history object (just don't preserve it)
                        # h.delete()
                        deleted_records += 1

                    if not deleted_records:
                        continue

                    logging.info(f"Deleting {deleted_records} from {m.id}, {m}")

                    # Nuke history for this object
                    with connection.cursor() as c:
                        query = f"DELETE FROM {table_name} WHERE id = '{m.id}'"
                        #logging.info(query)
                        c.execute(query)

                    # Replace the history with meaningful history
                    for mh in meaningful_history:
                        mh.pk = None
                        mh.save()

                except Exception as e:
                    logging.exception(f"Could not get history for this link: {e}")
