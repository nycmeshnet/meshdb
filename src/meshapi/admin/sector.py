from django import forms
from django.contrib import admin

from meshapi.admin.admin import device_fieldsets
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Sector


class SectorAdminForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = "__all__"


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    form = SectorAdminForm
    search_fields = ["name__icontains", "model__icontains", "ssid__icontains", "notes__icontains"]
    list_display = [
        "__str__",
        "ssid",
        "name",
        "model",
    ]
    list_filter = [
        "status",
        "install_date",
        "model",
    ]
    inlines = [DeviceLinkInline]
    fieldsets = device_fieldsets + [
        (
            "Sector Attributes",
            {
                "fields": [
                    "radius",
                    "azimuth",
                    "width",
                ]
            },
        ),
    ]  # type: ignore[assignment]
