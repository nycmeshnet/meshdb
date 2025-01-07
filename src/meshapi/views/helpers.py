import copy

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
    OpenApiParameter,
    extend_schema_field,
)
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from meshapi.models import Install, Node
from meshapi.permissions import HasDisambiguateNumberPermission
from meshapi.serializers import NestedKeyObjectRelatedField

helper_err_response_schema = inline_serializer("ErrorResponse", fields={"detail": serializers.CharField()})

install_serializer_field = NestedKeyObjectRelatedField(
    queryset=Install.objects.all(),
    additional_keys=("install_number",),
)

node_serializer_field = NestedKeyObjectRelatedField(
    queryset=Node.objects.all(),
    additional_keys=("network_number",),
)


# TODO: Fix docs, maybe with custom install serializer?
class DisambiguateInstallOrNetworkNumber(APIView):
    permission_classes = [HasDisambiguateNumberPermission]

    @extend_schema(
        tags=["Helpers"],
        summary="Identify a number as either an NN or an install number (or both) "
        "based on MeshDB data about Installs and/or Nodes with that number",
        parameters=[
            OpenApiParameter(
                "number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="The number to use to look up Installs and Nodes",
                required=True,
            ),
        ],
        responses={
            "200": OpenApiResponse(
                inline_serializer(
                    "DisambiguateNumberSuccessResponse",
                    fields={
                        "resolved_node": node_serializer_field,
                        "supporting_data": inline_serializer(
                            "DisambiguateNumberSupportingData",
                            fields={
                                "exact_match_recycled_install": install_serializer_field,
                                "exact_match_node": node_serializer_field,
                                "exact_match_nonrecycled_install": copy.copy(install_serializer_field),
                            },
                        ),
                    },
                ),
                description="At least one Node or Install exists corresponding to this",
            ),
            "400": OpenApiResponse(
                helper_err_response_schema,
                description="Invalid request",
            ),
            "404": OpenApiResponse(
                helper_err_response_schema,
                description="Requested number could not be found as either an Network or Install number",
            ),
            "500": OpenApiResponse(helper_err_response_schema, description="Unexpected internal error"),
        },
    )
    def get(self, request: Request) -> Response:
        ambiguous_number_str = request.query_params.get("number", "")
        try:
            ambiguous_number = int(ambiguous_number_str)
            if ambiguous_number <= 0:
                raise ValueError()
        except ValueError:
            return Response(
                {"detail": f"Invalid number: '{ambiguous_number_str}'. Must be an integer greater than zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        install_object = Install.objects.filter(install_number=ambiguous_number).first()
        node_object = Node.objects.filter(network_number=ambiguous_number).first()

        if not install_object and not node_object:
            return Response(
                {"detail": f"Provided number: {ambiguous_number} did not correspond to any install or node objects"},
                status=status.HTTP_404_NOT_FOUND,
            )

        resolved_node = node_object if node_object else (install_object.node if install_object else None)

        output = {
            "resolved_node": node_serializer_field.to_representation(resolved_node) if resolved_node else None,
            "supporting_data": {
                "exact_match_recycled_install": (
                    install_serializer_field.to_representation(install_object)
                    if install_object and install_object.status == Install.InstallStatus.NN_REASSIGNED
                    else None
                ),
                "exact_match_nonrecycled_install": (
                    install_serializer_field.to_representation(install_object)
                    if install_object and install_object.status != Install.InstallStatus.NN_REASSIGNED
                    else None
                ),
                "exact_match_node": node_serializer_field.to_representation(node_object) if node_object else None,
            },
        }

        if output["supporting_data"]["exact_match_nonrecycled_install"]:
            output["supporting_data"]["exact_match_nonrecycled_install"]["node"] = (
                node_serializer_field.to_representation(install_object.node) if install_object.node else None
            )
        if output["supporting_data"]["exact_match_recycled_install"]:
            output["supporting_data"]["exact_match_recycled_install"]["node"] = (
                node_serializer_field.to_representation(install_object.node) if install_object.node else None
            )

        return Response(data=output, status=status.HTTP_200_OK)
