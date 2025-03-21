import logging
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.template import loader

from meshapi.management.commands import replay_join_records
from meshapi.util.join_records import JoinRecordProcessor
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices
from meshapi.util.uisp_import.sync_handlers import import_and_sync_uisp_devices

from meshapi.util.network_number import NETWORK_NUMBER_MAX


@staff_member_required
def join_record_viewer(request: HttpRequest) -> HttpResponse:
    network_number = request.GET.get("network_number")
    if not network_number:
        status = 400
        m = f"({status}) Please provide a network number."
        logging.error(m)
        return HttpResponse(m, status=status)

    if network_number > NETWORK_NUMBER_MAX:
        status = 400
        m = f"({status}) Network number is beyond the max."
        logging.error(m)
        return HttpResponse(m, status=status)

    import_and_sync_uisp_devices(get_uisp_devices(), network_number)
    import_and_sync_uisp_links(get_uisp_links(), network_number)
    sync_link_table_into_los_objects()
