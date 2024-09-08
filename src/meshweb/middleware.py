from pathlib import Path
from django.shortcuts import reverse, redirect

MAINTENANCE_FILE = Path("/tmp/meshdb_maintenance")


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get("PATH_INFO", "")

        if MAINTENANCE_FILE.is_file() and path not in [
            reverse("maintenance"),
            reverse("enable-maintenance"),
            reverse("disable-maintenance"),
        ]:
            response = redirect(reverse("maintenance"))
            return response

        response = self.get_response(request)

        return response
