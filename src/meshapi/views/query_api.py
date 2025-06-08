import copy
from typing import Any, Iterator, List, Type, Union

from django.db.models import Model, Q, QuerySet
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view

from meshapi.docs import query_form_password_param
from meshapi.models import Install
from meshapi.permissions import LegacyMeshQueryPassword
from meshapi.serializers.query_api import QueryFormSerializer
from meshapi.views.lookups import FilterRequiredListAPIView

"""
Re-implements https://docs.nycmesh.net/installs/query/
Search by address, email, nn, install_number, or bin
Guarded by PSK

However, we return a JSON array, rather than a CSV file
"""


class FakeQuerySet(QuerySet):
    """
    A fake queryset that lets us inject a List of objects in place of a real QuerySet

    This is needed because the default QuerySet implementation de-duplicates the _result_cache
    field automatically, and we need to "spread" the additional members over multiple copies
    of the same "install" object similar to a classic SQL JOIN
    """

    def __init__(self, model: Type[Model], data: List) -> None:
        super().__init__(model)
        self.model = model
        self._result_cache: List = data

    def _clone(self) -> "FakeQuerySet":
        return FakeQuerySet(self.model, self._result_cache)

    def __iter__(self) -> Iterator[Model]:
        yield from self._result_cache

    def __len__(self) -> int:
        return len(self._result_cache)

    def __getitem__(self, k: Union[int | slice]) -> Any:
        return self._result_cache[k]


def multiply_install_queryset_over_all_members(queryset: QuerySet[Install]) -> QuerySet[Install]:
    multiplied_results: List[Install] = []
    for install in queryset:
        multiplied_results.append(install)
        for member in install.additional_members.all():
            # This is an ugly hack to accommodate the query form's limited awareness of our relational model.
            # We manually duplicate the Django model instances and mutate them in a way that is not consistent with
            # the DB, so that the serializer can understand that "for this install, we want you to use one of
            # the additional members as the source of the email address and other member fields"
            duplicated_install = copy.copy(install)
            duplicated_install.member = member
            multiplied_results.append(duplicated_install)

    return FakeQuerySet(queryset.model, multiplied_results)


class QueryMemberFilter(filters.FilterSet):
    name = filters.CharFilter(method="filter_on_member_name")
    email_address = filters.CharFilter(method="filter_on_all_emails")
    phone_number = filters.CharFilter(method="filter_on_all_phone_numbers")

    def filter_on_member_name(self, queryset: QuerySet[Install], field_name: str, value: str) -> QuerySet[Install]:
        return queryset.filter(Q(member__name__icontains=value) | Q(additional_members__name__icontains=value))

    def filter_on_all_emails(self, queryset: QuerySet[Install], field_name: str, value: str) -> QuerySet[Install]:
        return queryset.filter(
            Q(member__primary_email_address__icontains=value)
            | Q(member__stripe_email_address__icontains=value)
            | Q(member__additional_email_addresses__icontains=value)
            | Q(additional_members__primary_email_address__icontains=value)
            | Q(additional_members__stripe_email_address__icontains=value)
            | Q(additional_members__additional_email_addresses__icontains=value)
        )

    def filter_on_all_phone_numbers(self, queryset: QuerySet[Install], name: str, value: str) -> QuerySet[Install]:
        return queryset.filter(
            Q(member__phone_number__icontains=value)
            | Q(member__additional_phone_numbers__icontains=value)
            | Q(additional_members__phone_number__icontains=value)
            | Q(additional_members__member__additional_phone_numbers__icontains=value)
        )

    class Meta:
        model = Install
        fields: List[str] = []


@extend_schema_view(
    get=extend_schema(
        tags=["Legacy Query Form"],
        parameters=[query_form_password_param],
        summary="Query & filter based on Member attributes. "
        "Results are returned as flattened spreadsheet row style output",
        auth=[],
    ),
)
class QueryMember(FilterRequiredListAPIView):
    queryset = (
        Install.objects.all()
        .prefetch_related("building")
        .prefetch_related("node")
        .prefetch_related("member")
        .order_by("install_number")
    )
    serializer_class = QueryFormSerializer
    filterset_class = QueryMemberFilter
    permission_classes = [LegacyMeshQueryPassword]

    def get_queryset(self) -> QuerySet:
        return multiply_install_queryset_over_all_members(super(QueryMember, self).get_queryset())


class QueryInstallFilter(filters.FilterSet):
    network_number = filters.NumberFilter(field_name="node__network_number", lookup_expr="exact")

    class Meta:
        model = Install
        fields = ["install_number", "member", "building", "status"]


@extend_schema_view(
    get=extend_schema(
        tags=["Legacy Query Form"],
        parameters=[query_form_password_param],
        summary="Query & filter based on Install attributes. "
        "Results are returned as flattened spreadsheet row style output",
        auth=[],
    ),
)
class QueryInstall(FilterRequiredListAPIView):
    queryset = (
        Install.objects.all()
        .prefetch_related("building")
        .prefetch_related("node")
        .prefetch_related("member")
        .order_by("install_number")
    )
    serializer_class = QueryFormSerializer
    filterset_class = QueryInstallFilter
    permission_classes = [LegacyMeshQueryPassword]

    def get_queryset(self) -> QuerySet:
        return multiply_install_queryset_over_all_members(super(QueryInstall, self).get_queryset())


class QueryBuildingFilter(filters.FilterSet):
    street_address = filters.CharFilter(field_name="building__street_address", lookup_expr="icontains")
    city = filters.CharFilter(field_name="building__city", lookup_expr="iexact")
    state = filters.CharFilter(field_name="building__state", lookup_expr="iexact")
    zip_code = filters.CharFilter(field_name="building__zip_code", lookup_expr="iexact")
    bin = filters.CharFilter(field_name="building__bin", lookup_expr="iexact")

    class Meta:
        model = Install
        fields = ["bin", "zip_code"]


@extend_schema_view(
    get=extend_schema(
        tags=["Legacy Query Form"],
        parameters=[query_form_password_param],
        summary="Query & filter based on Building attributes. "
        "Results are returned as flattened spreadsheet row style output",
        auth=[],
    ),
)
class QueryBuilding(FilterRequiredListAPIView):
    queryset = (
        Install.objects.all()
        .prefetch_related("building")
        .prefetch_related("node")
        .prefetch_related("member")
        .order_by("install_number")
    )
    serializer_class = QueryFormSerializer
    filterset_class = QueryBuildingFilter
    permission_classes = [LegacyMeshQueryPassword]

    def get_queryset(self) -> QuerySet:
        return multiply_install_queryset_over_all_members(super(QueryBuilding, self).get_queryset())
