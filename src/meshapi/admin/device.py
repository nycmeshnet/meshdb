from django.contrib import admin
from django.contrib.admin.options import forms

from meshapi.admin.admin import device_fieldsets
from meshapi.admin.inlines import DeviceLinkInline
from meshapi.models import Device
from meshapi.widgets import DeviceIPAddressWidget


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"
        widgets = {
            "ip_address": DeviceIPAddressWidget(),
        }


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
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
    fieldsets = device_fieldsets
    inlines = [DeviceLinkInline]

    def get_queryset(self, request):
        # Get the base queryset
        queryset = super().get_queryset(request)
        # Filter out sectors
        queryset = queryset.exclude(sector__isnull=False)
        return queryset
