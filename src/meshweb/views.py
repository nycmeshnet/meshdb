import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from flags.state import disable_flag, enable_flag, flag_enabled
from ipware import get_client_ip
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes

from meshapi.permissions import HasMaintenanceModePermission


# Home view
@extend_schema(exclude=True)  # Don't show on docs page
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def index(request: HttpRequest) -> HttpResponse:
    template = loader.get_template("meshweb/index.html")
    links = {
        "Member Tools": [
            (f"{settings.FORMS_URL}/join/", "Join Form"),
            (settings.LOS_URL, "Line of Sight Tool"),
            (settings.MAP_URL, "Map"),
        ],
        "Volunteer Tools": [
            ("/admin", "Admin Panel"),
            ("/api/v1/geography/whole-mesh.kml", "KML Download"),
            ("/explorer/play", "SQL Explorer"),
            (settings.FORMS_URL, "Other Forms"),
        ],
        "Developer Tools": [
            ("https://github.com/nycmeshnet/meshdb", "Source Code"),
            ("/api/v1/", "MeshDB Data API"),
            ("/api-docs/swagger/", "API Documentation (Swagger)"),
            ("/api-docs/redoc/", "API Documentation (Redoc)"),
        ],
    }
    request_source_ip, request_source_ip_is_routable = get_client_ip(request)
    logging.info(f"Got source IP, on MeshDB: {request_source_ip}, Routable: {request_source_ip_is_routable}")
    logging.info(f"x_forwarded_for: {request.headers.get('X-Forwarded-For','')}")
    logging.info(f"headers: {request.headers}")

    context = {"links": links}
    return HttpResponse(template.render(context, request))


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def explorer_auth_redirect(request: HttpRequest) -> HttpResponse:
    # Auth Redirect to ensure that behavior is consistent with admin panel
    return HttpResponseRedirect("/admin/login/?next=/explorer/")


@permission_classes([permissions.AllowAny])
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
