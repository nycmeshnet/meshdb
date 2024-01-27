from dataclasses import dataclass
from rest_framework import generics
from rest_framework import generics, filters
from meshapi.models import Building, Install, Member
from meshapi.serializers import BuildingSerializer, InstallSerializer, MemberSerializer

# https://medium.com/geekculture/make-an-api-search-endpoint-with-django-rest-framework-111f307747b8


class LookupMember(generics.ListAPIView):
    search_fields = ["name", "email_address", "phone_number"]
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    serializer_class = MemberSerializer

    def get_queryset(self):
        # TODO: Validate Parameters?

        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_keyword_arguments_dict = {}
        for k, v in query_dict.items():
            if k == "name":
                filter_keyword_arguments_dict["name__icontains"] = v
            if k == "email_address":
                filter_keyword_arguments_dict["email_address__icontains"] = v
            if k == "phone_number":
                filter_keyword_arguments_dict["phone_number__icontains"] = v
        queryset = Member.objects.filter(**filter_keyword_arguments_dict)
        return queryset


class LookupInstall(generics.ListAPIView):
    # TODO: Add more search fields later
    search_fields = ["install_number", "network_number", "member_id", "building_id"]
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
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


# TODO: "email_address", "network_number", "install_number",

# Powers the Query form using Bin as the "anchor" of sorts.
# If we have the Building, we can get the Installs.
# If we have the Installs, we can get the Members.


@dataclass
class QueryResponse:
    install_number: int
    street_address: str
    city: str
    state: str
    zip: int
    unit: str
    name: str
    email: str
    notes: str
    network_number: int
    install_status: str


class LookupQueryBuilding(generics.ListAPIView):
    search_fields = ["street_address", "bin"]
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    serializer_class = (QuerySerializer)

    def get_queryset(self):
        # First, get the building. I think it's safe to assume we'll only have
        # one building.
        building = self.get_building()

        # Then once we have that, we need to get all the installs related to that
        # building.
        installs = self.get_installs(building)

        responses = []
        for install in installs:
            r: QueryResponse = QueryResponse(
                install_number=install.install_number,
                street_address=building.street_address,
                city=building.city,
                state=building.state,
                zip=building.zip,
                unit=install.unit,
                name=install.member.name,
                email=install.member.email_address,
                notes=install.notes + building.notes + install.member.contact_notes,
                network_number=install.network_number,
                install_status=install.install_status
            )
            responses.append(r)

        return responses

    def get_building(self):
        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_args = {}
        for k, v in query_dict.items():
            if k == "street_address":
                filter_args[f"{k}__icontains"] = v
            elif k == "bin":
                filter_args[f"{k}__exact"] = v

        buildings = Building.objects.filter(**filter_args)
        return buildings

    def get_installs(self, building):
        filter_args = {
            "building__exact": building,
        }
        return Install.objects.filter(**filter_args)
