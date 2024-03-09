from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, generics

from meshapi.models import Building, Install, Member
from meshapi.serializers import BuildingSerializer, InstallSerializer, MemberSerializer

# https://medium.com/geekculture/make-an-api-search-endpoint-with-django-rest-framework-111f307747b8


@extend_schema_view(
    get=extend_schema(
        tags=["Members"],
        parameters=[
            OpenApiParameter(
                "name",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by the name field using substring matching",
                required=False,
            ),
            OpenApiParameter(
                "email_address",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by the email address fields using substring matching",
                required=False,
            ),
            OpenApiParameter(
                "phone_number",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter members by the phone_number field using substring matching",
                required=False,
            ),
        ],
    ),
)
class LookupMember(generics.ListAPIView):
    serializer_class = MemberSerializer

    def get_queryset(self):
        # TODO: Validate Parameters?

        queries = Q()
        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        for k, v in query_dict.items():
            if k == "name":
                queries = queries & Q(name__icontains=v)
            if k == "email_address":
                queries = queries & (
                    Q(primary_email_address__icontains=v)
                    | Q(stripe_email_address__icontains=v)
                    | Q(additional_email_addresses__icontains=v)
                )
            if k == "phone_number":
                queries = queries & Q(phone_number__icontains=v)

        queryset = Member.objects.filter(queries)
        return queryset


@extend_schema_view(
    get=extend_schema(
        tags=["Installs"],
        parameters=[
            OpenApiParameter(
                "install_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by install_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "network_number",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by network_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "member",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by the Member id foreign key field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "building",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by the Building id foreign key field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "install_status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the install_status field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupInstall(generics.ListAPIView):
    # TODO: Add more search fields later
    search_fields = ["install_number", "network_number", "member", "building", "install_status"]
    serializer_class = InstallSerializer

    def get_queryset(self):
        # TODO: Validate Parameters?

        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_keyword_arguments_dict = {}
        for k, v in query_dict.items():
            if k in self.search_fields:
                filter_keyword_arguments_dict[f"{k}__exact"] = v
        queryset = Install.objects.filter(**filter_keyword_arguments_dict)
        return queryset


@extend_schema_view(
    get=extend_schema(
        tags=["Buildings"],
        parameters=[
            OpenApiParameter(
                "install",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter Buildings by install_number using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "bin",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by bin using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "building_status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the building_status field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "street_address",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the street_address field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "city",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the city field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "state",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the state field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "zip_code",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter installs by the zip_code field using strict equality",
                required=False,
            ),
            OpenApiParameter(
                "primary_nn",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Filter installs by the primary_nn field using strict equality",
                required=False,
            ),
        ],
    ),
)
class LookupBuilding(generics.ListAPIView):
    search_fields = [
        "install",
        "bin",
        "building_status",
        "street_address",
        "city",
        "state",
        "zip_code",
        "primary_nn",
    ]
    serializer_class = BuildingSerializer

    def get_queryset(self):
        # TODO: Validate Parameters?

        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_keyword_arguments_dict = {}
        for k, v in query_dict.items():
            if k in self.search_fields:
                filter_keyword_arguments_dict[f"{k}__exact"] = v
        queryset = Building.objects.filter(**filter_keyword_arguments_dict)
        return queryset
