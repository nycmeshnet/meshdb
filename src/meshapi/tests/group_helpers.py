from django.contrib.auth.models import Group
from django.core.management import call_command


def create_groups():
    # Call the manage.py command to create the groups as they will be created at runtime,
    # this also assigns expected permissions
    call_command("create_groups")

    # Fetch the newly created groups and return
    admin_group = Group.objects.get(name="Admin")
    installer_group = Group.objects.get(name="Installer")
    read_only_group = Group.objects.get(name="Read Only")
    return admin_group, installer_group, read_only_group
