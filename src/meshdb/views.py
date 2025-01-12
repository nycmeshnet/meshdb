from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import HttpResponseRedirect
from django.shortcuts import render


@staff_member_required
def admin_iframe_view(request, path):
    print(path)
    return render(request, "admin/iframed.html")


@staff_member_required
def minimal_example_view(request):
    return render(request, "admin/minimal_example.html")

@staff_member_required
def redirect_admin(request, path):
    # Extract the full path and redirect to /admin/ with the original path as a query parameter
    return HttpResponseRedirect(f"/admin/?next=/{path}")

