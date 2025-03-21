import logging
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.template import loader
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices
from meshapi.util.uisp_import.sync_handlers import import_and_sync_uisp_devices

from meshapi.util.network_number import NETWORK_NUMBER_MAX

from datadog import statsd
from ddtrace import tracer

@tracer.wrap()
@staff_member_required
def uisp_on_demand_form(request: HttpRequest) -> HttpResponse:

    #return HttpResponse("hi mom", status=200)

    template = loader.get_template("meshweb/uisp_on_demand_form.html")
    context = {"logo": "meshweb/logo.svg"}
    return HttpResponse(template.render(context, request))
