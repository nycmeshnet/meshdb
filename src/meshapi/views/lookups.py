from rest_framework import generics
from rest_framework import generics, filters
from meshapi.models import Member
from meshapi.serializers import MemberSerializer


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

# @dataclass
# class LookupMemberRequest:
#     name: Optional[str] = field(default=None)
#     phone: Optional[str] = field(default=None) # TODO: search
#     email: Optional[str] = field(default=None)
# 
# @api_view(["GET"])
# def lookup_member(request):
#     request_json = json.loads(request.body)
#     try:
#         r = LookupMemberRequest(**request_json)
#     except TypeError as e:
#         return Response({"Got incomplete request"}, status=status.HTTP_400_BAD_REQUEST)
# 
            #     existing_members = Member.objects.filter(
#         name=r.name,
#         email_address=r.email,
#         phone_number=r.phone,
#     )
# 
#     for m in existing_members:
#         print(m)
# 
#     return Response({"member_id": existing_members[0].id,}, status=status.HTTP_200_OK)
#     
