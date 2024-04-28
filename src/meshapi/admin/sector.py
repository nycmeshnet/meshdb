from django.contrib import admin
from django.contrib.admin.options import forms

from meshapi.models import Sector
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.admin.admin import device_fieldsets

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
    ]
