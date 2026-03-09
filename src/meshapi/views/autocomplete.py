from dal_select2.views import Select2QuerySetView
from django.db.models import QuerySet, Q

from meshapi.models import Member


# Used in Install Member many-to-many field inline in the Admin panel
class MemberAutocomplete(Select2QuerySetView):
    def get_queryset(self) -> QuerySet[Member]:
        user = self.request.user
        if not user.is_authenticated:
            return Member.objects.none()

        queryset = Member.objects.all()

        if self.q:
            queryset = queryset.filter(Q(name__istartswith=self.q) | Q(primary_email_address__istartswith=self.q))

        return queryset
