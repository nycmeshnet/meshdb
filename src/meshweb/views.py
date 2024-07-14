from django.http import HttpRequest, HttpResponse
from django.template import loader
from drf_spectacular.utils import extend_schema
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
            ("https://forms.grandsvc.mesh.nycmesh.net/join/", "Join Form"),
            ("https://los.grandsvc.mesh.nycmesh.net/", "Line of Sight Tool"),
            ("https://map.grandsvc.mesh.nycmesh.net", "Map"),
        ],
        "Volunteer Tools": [
            ("/admin", "Admin Panel"),
            ("/api/v1/geography/whole-mesh.kml", "KML Download"),
            ("https://forms.grandsvc.mesh.nycmesh.net/", "Other Forms"),
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
