import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
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


@extend_schema_view(
    summary="Run the UISP Import job for a single Network Number.",
    post=extend_schema(tags=["UISP Import"]),
    responses={
        "200": OpenApiResponse(
            description="API is up and serving traffic",
            response=OpenApiTypes.STR,
        ),
        "400": OpenApiResponse(
            description="User provided invalid input in slug",
            response=OpenApiTypes.STR,
        ),
        "500": OpenApiResponse(
            description="Server error, probbaly a misconfigured environment variable.",
            response=OpenApiTypes.STR,
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def uisp_import_for_nn(request: Request, network_number: int) -> Response:
    logging.info(f"Received uisp import request for NN{network_number}")
    if not network_number:
        status = 404
        m = "Please provide a network number."
        logging.error(m)
        return Response({"detail": m}, status=status)

    try:
        target_nn = int(network_number)  # Because I apparently can't trust nobody
        # Must be in valid range.
        # NETWORK_NUMBER_MIN is set to something meshdb can assign new stuff, but we have lower NNs
        # hence, I hardcode 1
        FIRST_NN = 1
        if target_nn < FIRST_NN or NETWORK_NUMBER_MAX < target_nn:
            status = 404
            m = "Network number is not in valid range."
            logging.error(m)
            return Response({"detail": m}, status=status)
    except ValueError:
        status = 400
        m = f"Network Number must be an integer between {NETWORK_NUMBER_MIN} and {NETWORK_NUMBER_MAX}."
        return Response({"detail": m}, status=status)

    try:
        import_and_sync_uisp_devices(get_uisp_devices(), target_nn)
        import_and_sync_uisp_links(get_uisp_links(), target_nn)
        sync_link_table_into_los_objects(target_nn)
    except Exception as e:
        logging.exception(e)
        status = 500
        m = "An error ocurred while running the import. Please try again later."
        return Response({"detail": m}, status=status)

    logging.info(f"Successfully ran uisp import for NN{network_number}")
    return Response({"detail": "success"}, status=200)
