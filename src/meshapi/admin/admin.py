from django.contrib import admin

from meshapi.admin.inlines import *

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"

device_fieldsets = [
    (
        "Details",
        {
            "fields": [
                "status",
                "name",
                "ssid",
                "ip_address",
                "node",
            ]
        },
    ),
    (
        "Location",
        {
            "fields": [
                "latitude",
                "longitude",
                "altitude",
            ]
        },
    ),
    (
        "Dates",
        {
            "fields": [
                "install_date",
                "abandon_date",
            ]
        },
    ),
    (
        "Misc",
        {
            "fields": [
                "model",
                "type",
                "uisp_id",
                "notes",
            ]
        },
    ),
]
