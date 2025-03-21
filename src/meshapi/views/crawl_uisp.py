import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from meshapi.util.network_number import NETWORK_NUMBER_MAX
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links
from meshapi.util.uisp_import.sync_handlers import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def crawl_uisp_for_nn(request, network_number, format=None):
    if not network_number:
        status = 400
        m = "Please provide a network number."
        logging.error(m)
        return Response({"detail", m}, status=status)

    try:
        if int(network_number) > NETWORK_NUMBER_MAX:
            status = 400
            m = "Network number is beyond the max."
            logging.error(m)
            return Response({"detail", m}, status=status)
    except ValueError:
        status = 400
        m = "Invalid Network Number."
        return Response({"detail", m}, status=status)

    import_and_sync_uisp_devices(get_uisp_devices(), network_number)
    import_and_sync_uisp_links(get_uisp_links(), network_number)
    sync_link_table_into_los_objects()

    return Response({"detail": "success"}, status=200)
