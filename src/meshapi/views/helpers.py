from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from meshapi.models import Install, Node
from meshapi.permissions import HasDisambiguateNumberPermission
from meshapi.serializers import NestedKeyObjectRelatedField
from meshapi.serializers.nested_object_references import InstallNestedRefSerializer

helper_err_response_schema = inline_serializer("ErrorResponse", fields={"detail": serializers.CharField()})

install_serializer_field = InstallNestedRefSerializer()
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
                        "resolved_node": NestedKeyObjectRelatedField(
                            queryset=Node.objects.all(),
                            additional_keys=("network_number",),
                            help_text="The node that we guess this number represents. This is an exact NN match "
                            "if that node exists, otherwise we treat the input number as an install number "
                            "and return the related node",
                        ),
                        "supporting_data": inline_serializer(
                            "DisambiguateNumberSupportingData",
                            fields={
                                "exact_match_recycled_install": InstallNestedRefSerializer(
                                    help_text="An install with the install number exactly matching the requested "
                                    "number, if that install HAS had its install number recycled (or null "
                                    "if none exists). When this field is non-null, exact_match_node will "
                                    "also be populated with that node"
                                ),
                                "exact_match_node": NestedKeyObjectRelatedField(
                                    queryset=Node.objects.all(),
                                    additional_keys=("network_number",),
                                    help_text="A Node with the network number exactly matching the requested number, "
                                    "if it exists",
                                ),
                                "exact_match_nonrecycled_install": InstallNestedRefSerializer(
                                    help_text="An install  with the install number exactly matching the requested "
                                    "number, if that install has NOT had its install number recycled (or null if "
                                    "none exists)"
                                ),
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

        return Response(data=output, status=status.HTTP_200_OK)
