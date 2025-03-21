from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from datadog import statsd
from ddtrace import tracer

@tracer.wrap()
@api_view(["POST"])
@staff_member_required
def crawl_usip_for_nn(request: Request) -> Response:
    statsd.increment("meshdb.crawl_uisp_for_nn.request", tags=[])
    network_number = request.get("network_number")
    return 200, network_number

    """
    if not network_number:
        status = 400
        m = f"({status}) Please provide a network number."
        logging.error(m)
        return HttpResponse(m, status=status)

    try:
        if int(network_number) > NETWORK_NUMBER_MAX:
            status = 400
            m = f"({status}) Network number is beyond the max."
            logging.error(m)
            return HttpResponse(m, status=status)
    except ValueError:
        status = 400
        m = f"({status}) invalid Network Number."
        return HttpResponse(m, status=status)

    import_and_sync_uisp_devices(get_uisp_devices(), network_number)
    import_and_sync_uisp_links(get_uisp_links(), network_number)
    sync_link_table_into_los_objects()
    """
