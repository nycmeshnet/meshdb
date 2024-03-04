import json
from django.forms import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from django_jsonform.widgets import JSONFormWidget

class PanoramaViewer(JSONFormWidget):
    chom_template_name="widgets/panorama_viewer.html"
    def __init__(self, schema):
        super().__init__(schema) 

    def chom_get_context(self, name, value, attrs=None):
        # FIXME: Need to parse the value because Django gives it as a string
        # for some reason
        value_as_array = json.loads(value)
        return {'widget': {
            'name': name,
            'value': value_as_array,
        }}

    def render(self, name, value, attrs=None, renderer=None):
        super_template = super().render(name, value, attrs, renderer)
        context = self.chom_get_context(name, value, attrs)
        pano_template = loader.get_template(self.chom_template_name).render(context)
        template =  super_template + pano_template
        return mark_safe(template)
