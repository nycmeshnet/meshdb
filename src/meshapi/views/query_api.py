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

"""
Re-implements https://docs.nycmesh.net/installs/query/
Search by address, email, nn, install_number, or bin
Guarded by PSK

However, we return a JSON array, rather than a CSV file
"""

class QueryFilterListAPIView(FilterRequiredListAPIView):
    def get(self, request, *args, **kwargs):
        maybe_auth = self.request.headers['Authorization']
        if maybe_auth != f"Bearer {os.environ.get('QUERY_PSK')}":
            return Response({"detail": "Invalid Password"}, 403)
        return super().get(request, *args, **kwargs)

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

@permission_classes([permissions.AllowAny])
class QueryMember(QueryFilterListAPIView):
    queryset = Install.objects.all().order_by("install_number")
    serializer_class = QueryFormSerializer 
    filterset_class = QueryMemberFilter



class QueryInstallFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="node__network_number", lookup_expr="exact")
    install_number = filters.NumberFilter(field_name="install_number", lookup_expr="exact")

    class Meta:
        model = Install
        fields = ["member", "building", "status"]

@permission_classes([permissions.AllowAny])
class QueryInstall(QueryFilterListAPIView):
    queryset = Install.objects.all().order_by("install_number")
    serializer_class = QueryFormSerializer
    filterset_class = QueryInstallFilter


class QueryBuildingFilter(filters.FilterSet):
    street_address = filters.CharFilter(field_name="building__street_address", lookup_expr="icontains")
    city = filters.CharFilter(field_name="building__city", lookup_expr="iexact")
    state = filters.CharFilter(field_name="building__state", lookup_expr="iexact")
    zip_code = filters.CharFilter(field_name="building__zip_code", lookup_expr="iexact")
    bin = filters.CharFilter(field_name="building__bin", lookup_expr="iexact")

    class Meta:
        model = Install 
        fields = ["bin", "zip_code"]

@permission_classes([permissions.AllowAny])
class QueryBuilding(FilterRequiredListAPIView):
    queryset = Install.objects.all().order_by("install_number")
    serializer_class = QueryFormSerializer 
    filterset_class = QueryBuildingFilter 


