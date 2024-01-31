import json

from django.conf import os
from django.contrib.auth import PermissionDenied
from rest_framework import permissions
from rest_framework.permissions import BasePermission


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


class LegacyNNAssignmentPassword(permissions.BasePermission):
    def has_permission(self, request, view):
        request_json = json.loads(request.body)
        if "password" in request_json and request_json["password"] == os.environ.get("NN_ASSIGN_PSK"):
            return True

        raise PermissionDenied("Authentication Failed.")
