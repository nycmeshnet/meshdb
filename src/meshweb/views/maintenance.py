from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from flags.state import disable_flag, enable_flag, flag_enabled
from rest_framework.decorators import api_view, permission_classes

from meshapi.permissions import HasMaintenanceModePermission


def maintenance(request: HttpRequest) -> HttpResponse:
    if not flag_enabled("MAINTENANCE_MODE"):
        return HttpResponseRedirect(reverse("main"))
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Please check back later.",
        "redirect": "",
    }
    return HttpResponse(template.render(context, request))


@extend_schema(exclude=True)  # Don't show on docs page
@api_view(["POST"])
@permission_classes([HasMaintenanceModePermission])
def enable_maintenance(request: HttpRequest) -> HttpResponse:
    enable_flag("MAINTENANCE_MODE")
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Enabled maintenance mode.",
        "redirect": "maintenance",
    }
    return HttpResponse(template.render(context, request))


@extend_schema(exclude=True)  # Don't show on docs page
@api_view(["POST"])
@permission_classes([HasMaintenanceModePermission])
def disable_maintenance(request: HttpRequest) -> HttpResponse:
    if not flag_enabled("MAINTENANCE_MODE"):
        return HttpResponseRedirect("main")
    disable_flag("MAINTENANCE_MODE")
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Disabled maintenance mode.",
        "redirect": "main",
    }
    return HttpResponse(template.render(context, request))
