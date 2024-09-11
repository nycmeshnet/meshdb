from typing import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from flags.state import flag_enabled


class MaintenanceModeMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.META.get("PATH_INFO", "")
        if flag_enabled("MAINTENANCE_MODE") and path not in [
            reverse("maintenance"),
            reverse("maintenance-enable"),
            reverse("maintenance-disable"),
            reverse("rest_framework:login"),
        ]:
            response = HttpResponseRedirect(reverse("maintenance"))
            return response

        response = self.get_response(request)

        return response
