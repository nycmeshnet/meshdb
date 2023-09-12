from rest_framework import permissions

# TODO (willnilges): The docs for this could be better. I'm not really sure how
# to set up perm levels, or how we want to.
# https://www.django-rest-framework.org/api-guide/permissions/
# https://testdriven.io/blog/custom-permission-classes-drf/


class IsMeshMember(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True


class IsMeshInstaller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_installer:
            return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or request.user.is_installer:
            return True
