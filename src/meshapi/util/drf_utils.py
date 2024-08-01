from rest_framework.pagination import PageNumberPagination


class CustomSizePageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"  # items per page
