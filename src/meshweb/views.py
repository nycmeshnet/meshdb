from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from flags.state import disable_flag, enable_flag, flag_enabled
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes

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
            (settings.PG_ADMIN_URL, "PG Admin"),
            (settings.FORMS_URL, "Other Forms"),
        ],
        "Developer Tools": [
            ("https://github.com/nycmeshnet/meshdb", "Source Code"),
            ("/api/v1/", "MeshDB Data API"),
            ("/api-docs/swagger/", "API Documentation (Swagger)"),
            ("/api-docs/redoc/", "API Documentation (Redoc)"),
        ],
    }
    context = {"links": links}
    return HttpResponse(template.render(context, request))

def maintenance(request: HttpRequest) -> HttpResponse:
    if not flag_enabled('MAINTENANCE_MODE'):
        return redirect(reverse("main"))
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Please check back later.",
        "redirect": "",
    }
    return HttpResponse(template.render(context, request))

# TODO (wdn): Can I make a "disable maintenance mode" button visible for admins?

@api_view(["POST"])
def enable_maintenance(request: HttpRequest) -> HttpResponse:
    enable_flag("MAINTENANCE_MODE")
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Enabled maintenance mode.",
        "redirect": "maintenance",
    }
    return HttpResponse(template.render(context, request))


@api_view(["POST"])
def disable_maintenance(request: HttpRequest) -> HttpResponse:
    if not flag_enabled("MAINTENANCE_MODE"):
        return redirect("main")
    disable_flag("MAINTENANCE_MODE")
    template = loader.get_template("meshweb/maintenance.html")
    context = {
        "message": "Disabled maintenance mode.",
        "redirect": "main",
    }
    return HttpResponse(template.render(context, request))
