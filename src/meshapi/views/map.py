from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.util.map_data import render_link_data, render_node_data, render_sector_data


def should_request_bypass_cache(request: Request) -> bool:
    """
    Check if we should bypass cache for this request, by checking if the caller requested as such,
    via the ?nocache=True parameter.
    :param request: A DRF request object
    :return: A boolean indicating if we should bypass cache for this request
    """
    if request.query_params.get("nocache") == "true":
        return True

    return False


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary='Complete list of all "Nodes" (mostly Installs with some fake installs generated to solve NN re-use), '
        "unpaginated, in the format expected by the website map. (Warning: This endpoint is a legacy format and may be "
        "deprecated/removed in the future)",
    ),
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def map_data_node_list(request: Request) -> Response:
    node_data = render_node_data(bypass_cache=should_request_bypass_cache(request))
    return Response(node_data)


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary="Complete list of all Links, unpaginated, in the format expected by the website map. "
        "(Warning: This endpoint is a legacy format and may be deprecated/removed in the future)",
    ),
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def map_data_link_list(request: Request) -> Response:
    link_data = render_link_data(bypass_cache=should_request_bypass_cache(request))
    return Response(link_data)


@extend_schema_view(
    get=extend_schema(
        tags=["Website Map Data"],
        auth=[],
        summary="Complete list of all Sectors, unpaginated, in the format expected by the website map. "
        "(Warning: This endpoint is a legacy format and may be deprecated/removed in the future)",
    ),
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def map_data_sector_list(request: Request) -> Response:
    sector_data = render_sector_data(bypass_cache=should_request_bypass_cache(request))
    return Response(sector_data)
