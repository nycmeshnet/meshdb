from ddtrace import tracer
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.template import loader


@tracer.wrap()
@staff_member_required
def uisp_on_demand_form(request: HttpRequest) -> HttpResponse:
    template = loader.get_template("meshweb/uisp_on_demand_form.html")
    context = {"logo": "meshweb/logo.svg"}
    return HttpResponse(template.render(context, request))
