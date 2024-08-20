import json
import os
from typing import Any, Callable, Dict, Optional

from django import forms
from django.forms import widgets
from django.template import loader
from django.utils.safestring import SafeString, mark_safe
from django_jsonform.widgets import JSONFormWidget


class PanoramaViewer(JSONFormWidget):
    pano_template_name = "widgets/panorama_viewer.html"

    def __init__(self, schema: dict):
        super().__init__(schema)

    def pano_get_context(self, name: str, value: str) -> dict:
        value_as_array = json.loads(value)
        return {
            "widget": {
                "name": name,
                "value": value_as_array,
            }
        }

    def render(
        self, name: str, value: str, attrs: Optional[Dict[str, Any]] = None, renderer: Optional[Any] = None
    ) -> SafeString:
        if "DISALLOW_PANO_EDITS" in os.environ:
            super_template = ""
        else:
            # Render the JSONFormWidget to allow editing of the panoramas
            super_template = super().render(name, value, attrs, renderer)

        # Then, render the panoramas for viewing
        context = self.pano_get_context(name, value)
        pano_template = loader.get_template(self.pano_template_name).render(context)

        template = super_template + pano_template
        return mark_safe(template)

    class Media:
        css = {
            "all": ("widgets/panorama_viewer.css", "widgets/flickity.min.css"),
        }
        js = ["widgets/flickity.pkgd.min.js"]


class ExternalHyperlinkWidget(widgets.TextInput):
    template_name = "widgets/external_link.html"

    def __init__(self, formatter: Callable, title: str = ""):
        self.formatter = formatter
        self.title = title
        super().__init__()

    def get_link_context(self, name: str, value: str) -> dict:
        formatted_value = None
        if value:
            formatted_value = self.formatter(value)
        return {
            "widget": {
                "name": name,
                "value": value,
                "formatted": formatted_value,
                "title": self.title,
            }
        }

    def render(
        self, name: str, value: str, attrs: Optional[Dict[str, Any]] = None, renderer: Optional[Any] = None
    ) -> SafeString:
        context = self.get_link_context(name, value)
        super_context = self.get_context(name, value, attrs)
        super_context["widget"]["value"] = context["widget"]["value"]
        super_context["widget"]["formatted"] = context["widget"]["formatted"]
        return super()._render(self.template_name, super_context, renderer)


class DeviceIPAddressWidget(widgets.TextInput):
    template_name = "widgets/ip_address.html"


class UISPHyperlinkWidget(widgets.TextInput):
    template_name = "widgets/uisp_link.html"


class AutoPopulateLocationWidget(forms.Widget):
    template_name = "widgets/auto_populate_location.html"

    class Media:
        css = {
            "all": ("widgets/auto_populate_location.css",),
        }
        js = ["widgets/auto_populate_location.js"]

    def __init__(self, source: str, attrs: Optional[dict] = None):
        super().__init__(attrs)
        self.source = source

    def get_context(self, name: str, value: str, attrs: Optional[dict] = None) -> dict:
        context = super().get_context(name, value, attrs)
        context["auto_populate_source"] = self.source
        context["auto_populate_url"] = self.source
        return context
