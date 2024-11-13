from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from flags.state import disable_flag, enable_flag, flag_enabled
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes

from meshapi.permissions import HasMaintenanceModePermission


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def explorer_auth_redirect(request: HttpRequest) -> HttpResponse:
    # Auth Redirect to ensure that behavior is consistent with admin panel
    return HttpResponseRedirect("/admin/login/?next=/explorer/")
