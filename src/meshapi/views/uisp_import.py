import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.util.network_number import NETWORK_NUMBER_MAX, NETWORK_NUMBER_MIN
from meshapi.util.uisp_import.fetch_uisp import get_uisp_devices, get_uisp_links
from meshapi.util.uisp_import.sync_handlers import (
    import_and_sync_uisp_devices,
    import_and_sync_uisp_links,
    sync_link_table_into_los_objects,
)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def uisp_import_for_nn(request: Request, network_number: int) -> Response:
    if not network_number:
        status = 400
        m = "Please provide a network number."
        logging.error(m)
        return Response({"detail", m}, status=status)

    try:
        target_nn = int(network_number)  # Because I apparently can't trust nobody
        # Must be in valid range
        if target_nn < NETWORK_NUMBER_MIN or NETWORK_NUMBER_MAX < target_nn:
            status = 400
            m = "Network number is not in valid range."
            logging.error(m)
            return Response({"detail", m}, status=status)
    except ValueError:
        status = 400
        m = f"Network Number must be an integer between {NETWORK_NUMBER_MIN} and {NETWORK_NUMBER_MAX}."
        return Response({"detail": m}, status=status)

    try:
        import_and_sync_uisp_devices(get_uisp_devices(), target_nn)
        import_and_sync_uisp_links(get_uisp_links(), target_nn)
        sync_link_table_into_los_objects()
    except Exception as e:
        logging.exception(e)
        status = 500
        m = f"An error ocurred while running the import. Please try again later."
        return Response({"detail": m}, status=status)

    return Response({"detail": "success"}, status=200)
