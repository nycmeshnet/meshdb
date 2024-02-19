import drf_hooks.admin
from django.contrib import admin

from meshapi_hooks.hooks import CelerySerializerHook

admin.site.unregister(CelerySerializerHook)


@admin.register(CelerySerializerHook)
class CelerySerializerHookAdmin(drf_hooks.admin.HookAdmin):
    fields = ("enabled", "user", "target", "event", "headers", "consecutive_failures")
    readonly_fields = ["consecutive_failures"]

    class Meta:
        model = CelerySerializerHook
