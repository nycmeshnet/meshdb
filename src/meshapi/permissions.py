from django.conf import os
from django.contrib.auth import PermissionDenied
from rest_framework import permissions
from rest_framework.permissions import BasePermission

INSTALLER_GROUP = "Installer"
ADMIN_GROUP = "Admin"
READONLY_GROUP = "Read Only"


def is_installer(user):
    return user.groups.filter(name=INSTALLER_GROUP).exists()


def is_admin(user):
    return user.groups.filter(name=ADMIN_GROUP).exists()


def is_readonly(user):
    return user.groups.filter(name=READONLY_GROUP).exists()


perm_denied_generic_msg = "You do not have access to this resource."


class IsReadOnly(BasePermission):
    """
    The request is a read-only request. Add this to any View that needs to be accessible to
    unauthenticated users. Be sure to keep the Django authenticator also (e.g.):
        permission_classes = [permissions.DjangoModelPermissions | IsReadOnly]
    """

    def has_permission(self, request, view):
        return bool(request.method in permissions.SAFE_METHODS)


class HasDjangoPermission(BasePermission):
    django_permission = None

    def has_permission(self, request, view):
        if not self.django_permission:
            raise NotImplementedError(
                "You must subclass HasDjangoPermission and specify the django_permission attribute"
            )
        return request.user and request.user.has_perm(self.django_permission)


class HasNNAssignPermission(HasDjangoPermission):
    django_permission = "meshapi.assign_nn"


# Janky
class LegacyMeshQueryPassword(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.query_params["password"] != os.environ.get("QUERY_PSK"):
            raise PermissionDenied("Authentication Failed.")
        return True
