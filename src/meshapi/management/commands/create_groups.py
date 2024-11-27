from argparse import ArgumentParser
from typing import Any

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates basic MeshDB groups"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        self.create_base_groups()
        self.create_extra_groups()

    def create_base_groups(self) -> None:
        models = [
            "building",
            "member",
            "install",
            "node",
            "device",
            "link",
            "los",
            "sector",
            "accesspoint",
        ]
        all_permissions = Permission.objects.all()

        admin, _ = Group.objects.get_or_create(name="Admin")
        installer, _ = Group.objects.get_or_create(name="Installer")
        read_only, _ = Group.objects.get_or_create(name="Read Only")

        for p in all_permissions:
            code = p.codename

            act, obj = code.split("_", maxsplit=1)

            # read_only
            if act == "view" and obj in models:
                read_only.permissions.add(p)

            # installer
            if (act in ["change", "add", "view"] and obj in models) or code == "assign_nn":
                installer.permissions.add(p)

            # admin
            if (
                obj in models
                or act == "view"
                or obj in ["user", "token", "tokenproxy", "celeryserializerhook"]
                or code == "assign_nn"
                or code == "update_panoramas"
            ):
                admin.permissions.add(p)

    def create_extra_groups(self) -> None:
        all_permissions = Permission.objects.all()

        # Loop again to make groups for specific actions
        explorer, _ = Group.objects.get_or_create(name="Explorer Access")

        for p in all_permissions:
            code = p.codename
            if "explorer_access" in code:
                explorer.permissions.add(p)
