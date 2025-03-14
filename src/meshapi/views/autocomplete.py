from meshapi.models import Member

from dal_select2.views import Select2QuerySetView

class MemberAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        user = self.request.user
        #if not user.is_authenticated:
        #    return Member.objects.none()

        queryset = Member.objects.all()

        if self.q:
            queryset = queryset.filter(name__istartswith=self.q)

        return queryset
