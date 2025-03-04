from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@staff_member_required
def admin_iframe_view(request: HttpRequest) -> HttpResponse:
    return render(request, "admin/iframed.html")
