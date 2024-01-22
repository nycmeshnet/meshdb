from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Creates basic groups"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        models = ['building', 'member', 'install', 'link', 'sector',]
        groups = ['admin', 'installer', 'readonly']
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
                installer.permissions.add(p) # Also give these roles to installer

            # installer
            if act == "change" and obj == 'install' or obj == 'member':
                installer.permissions.add(p)

            # admin
            if obj in models or obj in groups or obj == 'user' or obj == 'token':
                admin.permissions.add(p)

