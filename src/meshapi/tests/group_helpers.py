from django.contrib.auth.models import Group, Permission


def create_installer_group():
    # Set the installer permissions to how we expect admins
    # will set them in the console at runtime
    installer_group, _ = Group.objects.get_or_create(name="Installer")
    installer_group.permissions.add(Permission.objects.get(codename="view_member"))
    installer_group.permissions.add(Permission.objects.get(codename="view_building"))
    installer_group.permissions.add(Permission.objects.get(codename="add_install"))
    installer_group.permissions.add(Permission.objects.get(codename="assign_nn"))
    return installer_group
