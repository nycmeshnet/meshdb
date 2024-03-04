import json
from django.forms import Widget
from django.template import loader
from django.utils.safestring import mark_safe

class PanoramaViewer(Widget):
    template_name="widgets/panorama_viewer.html"

    def get_context(self, name, value, attrs=None):
        # FIXME: Need to parse the value because Django gives it as a string
        # for some reason
        value_as_array = json.loads(value)
        return {'widget': {
            'name': name,
            'value': value_as_array,
        }}

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)
