from django import forms
from django.contrib import admin

from meshapi.models import Link


class LinkAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = "__all__"
        widgets = {
            "description": forms.TextInput(),
        }


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    form = LinkAdminForm
    search_fields = [
        "from_device__node__name__icontains",
        "to_device__node__name__icontains",
        "from_device__node__buildings__street_address__icontains",
        "to_device__node__buildings__street_address__icontains",
        "from_device__node__network_number__iexact",
        "to_device__node__network_number__iexact",
        "notes__icontains",
    ]
    list_display = ["__str__", "status", "from_device", "to_device", "description"]
    list_filter = ["status", "type"]

    autocomplete_fields = ["from_device", "to_device"]
