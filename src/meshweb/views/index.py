from datadog import statsd
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template import loader


def index(request: HttpRequest) -> HttpResponse:
    statsd.increment("meshdb.views.index", tags=[])
    template = loader.get_template("meshweb/index.html")
    links = {
        ("meshweb/member.png", "Member Tools"): [
            (f"{settings.FORMS_URL}/join/", "Join Form"),
            (settings.LOS_URL, "Line of Sight Tool"),
            (settings.MAP_URL, "Map"),
        ],
        ("meshweb/volunteer.png", "Volunteer Tools"): [
            ("/admin", "Admin Panel"),
            ("/api/v1/geography/whole-mesh.kml", "KML Download"),
            ("/explorer/play", "SQL Explorer"),
            (f"{settings.FORMS_URL}/nn-assign/", "NN Assign Form"),
            (f"{settings.FORMS_URL}/query/", "Query Form"),
            ("/join-records/view/", "Join Record Viewer"),
        ],
        ("meshweb/developer.png", "Developer Tools"): [
            ("https://github.com/nycmeshnet/meshdb", "Source Code"),
            ("/api/v1/", "MeshDB Data API"),
            ("/api-docs/swagger/", "API Docs (Swagger)"),
            ("/api-docs/redoc/", "API Docs (Redoc)"),
        ],
    }
    context = {"links": links, "logo": "meshweb/logo.svg"}
    return HttpResponse(template.render(context, request))
