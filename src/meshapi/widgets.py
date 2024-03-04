from django.forms import Widget
from django.template import loader
from django.utils.safestring import mark_safe

class PanoramaViewer(Widget):
    template_name="widgets/panorama_viewer.html"

    def get_context(self, name, value, attrs=None):
        return {'widget': {
            'name': name,
            'value': value.split(","),
        }}

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)
