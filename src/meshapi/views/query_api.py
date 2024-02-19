from typing import Any, Dict, Optional

from rest_framework import generics
from rest_framework.views import models

from meshapi import permissions
from meshapi.models import Building, Install, Member
from meshapi.serializers.query_api import QueryFormSerializer

"""
Re-implements https://docs.nycmesh.net/installs/query/
Search by address, email, nn, install_number, or bin
Guarded by PSK

However, we return a JSON array, rather than a CSV file
"""


def filter_model_on_query_params(
    query_params: Dict[str, Any],
    model: type[models.Model],
    permitted_filters: Dict[str, Optional[str]],
    subsitutions: Dict[str, str] = None,
):
    query_dict = {}
    for k, v in query_params.items():
        if v:
            if subsitutions and k in subsitutions:
                query_dict[subsitutions[k]] = v
            else:
                query_dict[k] = v

    filter_args = {}
    for k, v in query_dict.items():
        if k in permitted_filters.keys():
            if permitted_filters[k]:
                filter_args[f"{k}__{permitted_filters[k]}"] = v
            else:
                filter_args[f"{k}"] = v

    return model.objects.filter(**filter_args)


BUILDING_FILTERS = {
    "street_address": "icontains",
    "zip_code": "iexact",
    "city": "icontains",
    "state": "icontains",
    "bin": "iexact",
}


class QueryBuilding(generics.ListAPIView):
    serializer_class = QueryFormSerializer
    pagination_class = None
    permission_classes = [permissions.LegacyMeshQueryPassword]

    def get_queryset(self):
        buildings = filter_model_on_query_params(
            self.request.query_params,
            Building,
            BUILDING_FILTERS,
        )

        output_qs = []
        for building in buildings:
            output_qs.extend(building.installs.all())

        return output_qs


MEMBER_FILTERS = {
    "email_address": None,
}


class QueryMember(generics.ListAPIView):
    serializer_class = QueryFormSerializer
    pagination_class = None
    permission_classes = [permissions.LegacyMeshQueryPassword]

    def get_queryset(self):
        members = filter_model_on_query_params(
            self.request.query_params,
            Member,
            MEMBER_FILTERS,
            {
                "email_address": "primary_email_address",
            },
        )

        output_qs = []
        for member in members:
            output_qs.extend(member.installs.all())

        return output_qs


INSTALL_FILTERS = {
    "network_number": None,
    "install_number": None,
}


class QueryInstall(generics.ListAPIView):
    serializer_class = QueryFormSerializer
    pagination_class = None
    permission_classes = [permissions.LegacyMeshQueryPassword]

    def get_queryset(self):
        return filter_model_on_query_params(
            self.request.query_params,
            Install,
            INSTALL_FILTERS,
        )
