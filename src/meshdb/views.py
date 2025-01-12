from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def admin_iframe_view(request):
    return render(request, "admin/iframed.html")


@staff_member_required
def minimal_example_view(request):
    return render(request, "admin/minimal_example.html")
