from django.http import HttpRequest, HttpResponse, HttpResponseRedirect


def explorer_auth_redirect(_: HttpRequest) -> HttpResponse:
    # Auth Redirect to ensure that behavior is consistent with admin panel
    return HttpResponseRedirect("/admin/login/?next=/explorer/")
