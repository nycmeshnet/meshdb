import typing
from typing import Dict, List, Optional, Tuple, Type

from django.contrib.admin import ModelAdmin
from django.contrib.admin.views.main import ORDER_VAR, ChangeList
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import QuerySet
from django.db.models.expressions import CombinedExpression, Expression
from django.http import HttpRequest

# Trick stolen from https://stackoverflow.com/a/56991089 to make mypy happy about mixin types
if typing.TYPE_CHECKING:
    _Base = ModelAdmin
else:
    _Base = object


class GentleOrderingChangelist(ChangeList):
    def get_ordering(self, request: HttpRequest, qs: QuerySet) -> List[Expression | str]:
        if qs.query.order_by:
            return list(qs.query.order_by)

        return super().get_ordering(request, qs)


class RankedSearchMixin(_Base):
    search_vector: Optional[CombinedExpression | SearchVector] = None

    def get_search_results(self, request: HttpRequest, queryset: QuerySet, search_term: str) -> Tuple[QuerySet, bool]:
        params = dict(request.GET.items())
        explicit_ordering = ORDER_VAR in params and params.get(ORDER_VAR)
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Annotate and order the search results based on the search_vector class variable,
        # this DRAMATICALLY improves search relevancy
        if search_term and self.search_vector and not explicit_ordering:
            # Perform the actual search-relevancy ordering
            # We do the de-duplication that would normally be done by the calling method here instead
            # (and use_distinct to False so that it for sure doesn't happen up there)
            # because the de-duplication method used by the caller requires replacing the queryset
            # which will destroy our ordering
            queryset = self.rank_queryset(queryset, search_term)
            use_distinct = False

        return queryset, use_distinct

    def rank_queryset(self, queryset: QuerySet, search_term: str) -> QuerySet:
        if search_term and self.search_vector:
            return (
                queryset.annotate(rank=SearchRank(self.search_vector, SearchQuery(search_term)))
                .order_by("-rank", "pk")
                .distinct("rank", "pk")
            )
        return queryset

    def get_changelist(self, request: HttpRequest, **kwargs: Dict) -> Type[ChangeList]:
        return GentleOrderingChangelist
