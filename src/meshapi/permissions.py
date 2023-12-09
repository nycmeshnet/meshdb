from django.contrib.auth import PermissionDenied
from rest_framework import permissions


def is_installer(user):
    return user.groups.filter(name="Installer").exists()

def is_admin(user):
    return user.groups.filter(name="Admin").exists()



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
            if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
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
            if not (request.user.is_superuser or is_admin(request.user) or is_installer(request.user)):
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


# Anyone can view requests, but only installers and admins can create them
class RequestListCreatePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True


# Anyone can retrieve requests, but only an admin can do anything else
class RequestRetrieveUpdateDestroyPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        else:
            if not request.user.is_superuser or is_admin(request.user):
                raise PermissionDenied(perm_denied_generic_msg)
            return True
