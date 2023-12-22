from django.contrib.auth import PermissionDenied
from rest_framework import permissions

INSTALLER_GROUP = "Installer"
ADMIN_GROUP = "Admin"
READONLY_GROUP = "ReadOnly"


def is_installer(user):
    return user.groups.filter(name=INSTALLER_GROUP).exists()


def is_admin(user):
    return user.groups.filter(name=ADMIN_GROUP).exists()


def is_readonly(user):
    return user.groups.filter(name=READONLY_GROUP).exists()


perm_denied_generic_msg = "You do not have access to this resource."


# Anyone can list buildings, but only Admins can create them
class BuildingListCreatePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Anyone can retrieve buildings, installers can update them, but only
# Admins can add or delete them.
class BuildingRetrieveUpdateDestroyPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        elif request.method == "PATCH":
            if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
                raise PermissionDenied(perm_denied_generic_msg)
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Anyone can list, but only admins can create
class MemberListCreatePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            if not (
                request.user.is_superuser
                or is_admin(request.user)
                or is_installer(request.user)
                or is_readonly(request.user)
            ):
                raise PermissionDenied(perm_denied_generic_msg)
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Installers can retrieve, but only admins can mutate
class MemberRetrieveUpdateDestroyPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            if not (
                request.user.is_superuser
                or is_admin(request.user)
                or is_installer(request.user)
                or is_readonly(request.user)
            ):
                raise PermissionDenied(perm_denied_generic_msg)
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Anyone can list installs, but only installers or admins can create them
class InstallListCreatePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        else:
            if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Anyone can retrieve installs, installers can update them, only
# admins can delete them
class InstallRetrieveUpdateDestroyPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        elif request.method == "PATCH":
            if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
                raise PermissionDenied(perm_denied_generic_msg)
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


class NetworkNumberAssignmentPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
            raise PermissionDenied(perm_denied_generic_msg)
        return True
