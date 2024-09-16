from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.serializers import BaseSerializer


class OnlyRawBrowsableAPIRenderer(BrowsableAPIRenderer):
    def render_form_for_serializer(self, serializer: BaseSerializer) -> str:
        return ""
