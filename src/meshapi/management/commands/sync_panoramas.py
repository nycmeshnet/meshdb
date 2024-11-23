from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from meshapi.util.panoramas import sync_github_panoramas


class Command(BaseCommand):
    help = "Syncs panoramas to MeshDB"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        print("Syncing panoramas from GitHub...")
        panoramas_saved, warnings = sync_github_panoramas()
        print(f"Saved {panoramas_saved} panoramas. Got {len(warnings)} warnings.")
        print(f"warnings:\n{warnings}")
