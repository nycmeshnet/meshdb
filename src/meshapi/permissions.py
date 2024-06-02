import json
import os
from typing import Any, Optional

from django.contrib.auth.models import User
from django.db.models import Model
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsReadOnly(BasePermission):
    """
    The request is a read-only request. Add this to any View that needs to be accessible to
    unauthenticated users. Be sure to keep the Django authenticator also (e.g.):
        permission_classes = [permissions.DjangoModelPermissions | IsReadOnly]
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(request.method in permissions.SAFE_METHODS)


class HasDjangoPermission(BasePermission):
    django_permission: str | None = None

    def has_permission(self, request: Request, view: Any) -> bool:
        if not self.django_permission:
            raise NotImplementedError(
                "You must subclass HasDjangoPermission and specify the django_permission attribute"
            )
        return bool(request.user) and request.user.has_perm(self.django_permission)


class HasNNAssignPermission(HasDjangoPermission):
    django_permission = "meshapi.assign_nn"


class HasPanoramaUpdatePermission(HasDjangoPermission):
    django_permission = "meshapi.update_panoramas"


# Janky
class LegacyMeshQueryPassword(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if (
            request.headers["Authorization"]
            and request.headers["Authorization"] == f"Bearer {os.environ.get('QUERY_PSK')}"
        ):
            return True

        raise PermissionDenied("Authentication Failed.")


class LegacyNNAssignmentPassword(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        request_json = json.loads(request.body)
        if "password" in request_json and request_json["password"] == os.environ.get("NN_ASSIGN_PSK"):
            return True

        raise PermissionDenied("Authentication Failed.")


def check_has_model_view_permission(user: Optional[User], model: Model) -> bool:
    if not user:
        # Unauthenticated requests do not have permission by default
        return False

    return user.has_perm(f"{__package__}.view_{model._meta.model_name}")
