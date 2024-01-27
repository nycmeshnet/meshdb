from dataclasses import dataclass
from rest_framework import generics
from rest_framework import generics, filters
from rest_framework.views import APIView
from meshapi.models import Building, Install, Member
from meshapi.serializers import BuildingSerializer, InstallSerializer, MemberSerializer

# TODO: "email_address", "network_number", "install_number",

# Powers the Query form using Bin as the "anchor" of sorts.
# If we have the Building, we can get the Installs.
# If we have the Installs, we can get the Members.

"""
Re-implements https://docs.nycmesh.net/installs/query/
Search by address, email, nn, install_number, or bin
Guarded by PSK

Returns:
<Query>:<Query Data>
<Install Number>, <Addy>, <Unit #>, <Name>, <Email>, <Notes>, <NN>, <Install Status>
<Install Number>, <Addy>, <Unit #>, <Name>, <Email>, <Notes>, <NN>, <Install Status>
<Install Number>, <Addy>, <Unit #>, <Name>, <Email>, <Notes>, <NN>, <Install Status>
...

Line 2 is the same no matter what(tm)
"""


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


class QueryBuilding(APIView):
    def get(self, request, format=None):
        # self.request = request

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

        return Building.objects.filter(**filter_args)

    def get_installs(self, building):
        filter_args = {
            "building__exact": building,
        }
        return Install.objects.filter(**filter_args)


class QueryMember(APIView):
    def get(self, request, format=None):
        # First, get the member. That will tell us the install(s), and from the
        # install(s) we can get the building(s).
        member = self.get_member()

        installs = self.get_installs(member)

        responses = []
        for install in installs:
            r: QueryResponse = QueryResponse(
                install_number=install.install_number,
                street_address=install.building.street_address,
                city=install.building.city,
                state=install.building.state,
                zip=install.building.zip,
                unit=install.unit,
                name=install.member.name,
                email=install.member.email_address,
                notes=install.notes + install.building.notes + install.member.contact_notes,
                network_number=install.network_number,
                install_status=install.install_status
            )
            responses.append(r)

        return responses

    def get_member(self):
        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_args = {}
        for k, v in query_dict.items():
            if k == "email":
                filter_args[f"{k}__iexact"] = v

        return Member.objects.filter(**filter_args)

    def get_installs(self, member):
        filter_args = {
            "member__exact": member,
        }
        return Install.objects.filter(**filter_args)

# Getting installs works a little differently.
# If it's an install number, it's going to resolve a single member and a single
# building (probably, hopefully)

# If it's a Network Number, then it could resolve multiple members. Maybe in
# multiple buildings.
class QueryInstall(APIView):
    def get(self, request, format=None):
        installs = self.get_installs()

        responses = []
        for install in installs:
            r: QueryResponse = QueryResponse(
                install_number=install.install_number,
                street_address=install.building.street_address,
                city=install.building.city,
                state=install.building.state,
                zip=install.building.zip,
                unit=install.unit,
                name=install.member.name,
                email=install.member.email_address,
                notes=install.notes + install.building.notes + install.member.contact_notes,
                network_number=install.network_number,
                install_status=install.install_status
            )
            responses.append(r)

        return responses

    def get_installs(self):
        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_args = {}
        for k, v in query_dict.items():
            if k == "network_number" or k == "install_number":
                filter_args[f"{k}__iexact"] = v
        return Install.objects.filter(**filter_args)
