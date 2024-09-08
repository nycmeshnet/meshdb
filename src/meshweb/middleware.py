from pathlib import Path
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

MAINTENANCE_FILE = Path("/tmp/meshdb_maintenance")


class MaintenanceModeMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
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
