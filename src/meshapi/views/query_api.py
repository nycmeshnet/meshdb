from dataclasses import asdict, dataclass
import json
from typing import Dict
from django.db.models import Q
from rest_framework import generics
from rest_framework import generics, filters
from rest_framework.views import APIView, Response, models, status
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
    zip_code: int
    unit: str
    name: str
    email_address: str
    notes: str
    network_number: int
    install_status: str

    @staticmethod
    def from_install(install):
        return QueryResponse(
            install_number=install.install_number,
            street_address=install.building.street_address,
            city=install.building.city,
            state=install.building.state,
            zip_code=install.building.zip_code,
            unit=install.unit,
            name=install.member.name,
            email_address=install.member.email_address,
            notes=f"Install Notes: '{install.notes}', Building Notes: '{install.building.notes}', Contact Notes: '{install.member.contact_notes}'",
            network_number=install.network_number,
            install_status=install.install_status
        )

class QueryView(APIView):
    def filter_on(self, model: type[models.Model], filters: Dict[str, str]):
        query_dict = {k: v for k, v in self.request.query_params.items() if v}
        filter_args = {}
        for k, v in query_dict.items():
            if k in filters.keys():
                if filters[k]:
                    filter_args[f"{k}__{filters[k]}"] = v
                else:
                    filter_args[f"{k}"] = v

        return model.objects.filter(**filter_args)

class QueryBuilding(QueryView):
    def get(self, request, format=None):
        buildings = self.filter_on(Building, {
            "street_address": "icontains",
            "bin": "iexact",
        })

        responses = []
        for building in buildings:
            for install in building.install_set.all():
                responses.append(asdict(QueryResponse.from_install(install)))

        return Response(
            responses,
            status=status.HTTP_200_OK,
        )

class QueryMember(QueryView):
    def get(self, request, format=None):
        members = self.filter_on(Member, {
            "email_address": None, 
        })

        responses = []
        for member in members:
            for install in member.install_set.all():
                responses.append(asdict(QueryResponse.from_install(install)))

        return Response(
            responses,
            status=status.HTTP_200_OK,
        )

class QueryInstall(QueryView):
    def get(self, request, format=None):
        installs = self.filter_on(Install, {
            "network_number": None,
            "install_number": None,
        })

        responses = []
        for install in installs:
            responses.append(asdict(QueryResponse.from_install(install)))

        return Response(
            responses,
            status=status.HTTP_200_OK,
        )

