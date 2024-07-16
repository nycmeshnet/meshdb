from argparse import ArgumentParser
from typing import Any

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates basic MeshDB groups"

    def add_arguments(self, parser: ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        models = [
            "building",
            "member",
            "install",
            "node",
            "device",
            "link",
            "sector",
        ]
        all_permissions = Permission.objects.all()

        admin, _ = Group.objects.get_or_create(name="Admin")
        installer, _ = Group.objects.get_or_create(name="Installer")
        read_only, _ = Group.objects.get_or_create(name="Read Only")

        for p in all_permissions:
            code = p.codename
            act, obj = code.split("_")

            # read_only
            if act == "view" and obj in models:
                read_only.permissions.add(p)

            # installer
            if (
                (act == "change" and (obj in ["install", "member", "device", "sector", "link"]))
                or (act == "view" and obj in models)
                or code == "assign_nn"
            ):
                installer.permissions.add(p)

            # admin
            if (
                obj in models
                or act == "view"
                or obj in ["user", "token", "tokenproxy", "celeryserialzerhook"]
                or code == "assign_nn"
            ):
                admin.permissions.add(p)
