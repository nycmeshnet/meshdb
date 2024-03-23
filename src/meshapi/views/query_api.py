import os
from typing import Any, Dict, Optional

from drf_spectacular.utils import extend_schema, extend_schema_view
from meshapi.views.lookups import FilterRequiredListAPIView, InstallFilter
from rest_framework import generics
from rest_framework.views import models

from meshapi import permissions
from meshapi.docs import map_query_filters_to_param_annotations, query_form_password_param
from meshapi.models import Building, Install, Member
from meshapi.serializers.query_api import QueryFormSerializer
from django.db.models import Q
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.response import Response

from rest_framework.decorators import api_view, permission_classes

from rest_framework import permissions
from meshapi.permissions import LegacyMeshQueryPassword

"""
Re-implements https://docs.nycmesh.net/installs/query/
Search by address, email, nn, install_number, or bin
Guarded by PSK

However, we return a JSON array, rather than a CSV file
"""


class QueryMemberFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="member.name", lookup_expr="icontains")
    email_address = filters.CharFilter(method="filter_on_all_emails")
    phone_number = filters.CharFilter(field_name="member.phone_number", lookup_expr="icontains")

    def filter_on_all_emails(self, queryset, name, value):
        return queryset.filter(
            Q(member__primary_email_address__icontains=value)
            | Q(member__stripe_email_address__icontains=value)
            | Q(member__additional_email_addresses__icontains=value)
        )

    class Meta:
        model = Install
        fields = []


class QueryMember(FilterRequiredListAPIView):
    queryset = Install.objects.all().prefetch_related("building").prefetch_related("node").prefetch_related("member").order_by("install_number")
    serializer_class = QueryFormSerializer
    filterset_class = QueryMemberFilter
    permission_classes = [LegacyMeshQueryPassword]


class QueryInstallFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="node__network_number", lookup_expr="exact")

    class Meta:
        model = Install
        fields = ["install_number", "member", "building", "status"]


class QueryInstall(FilterRequiredListAPIView):
    queryset = Install.objects.all().prefetch_related("building").prefetch_related("node").prefetch_related("member").order_by("install_number")
    serializer_class = QueryFormSerializer
    filterset_class = QueryInstallFilter
    permission_classes = [LegacyMeshQueryPassword]


class QueryBuildingFilter(filters.FilterSet):
    street_address = filters.CharFilter(field_name="building__street_address", lookup_expr="icontains")
    city = filters.CharFilter(field_name="building__city", lookup_expr="iexact")
    state = filters.CharFilter(field_name="building__state", lookup_expr="iexact")
    zip_code = filters.CharFilter(field_name="building__zip_code", lookup_expr="iexact")
    bin = filters.CharFilter(field_name="building__bin", lookup_expr="iexact")

    class Meta:
        model = Install
        fields = ["bin", "zip_code"]


class QueryBuilding(FilterRequiredListAPIView):
    queryset = Install.objects.all().prefetch_related("building").prefetch_related("node").prefetch_related("member").order_by("install_number")
    serializer_class = QueryFormSerializer
    filterset_class = QueryBuildingFilter
    permission_classes = [LegacyMeshQueryPassword]
