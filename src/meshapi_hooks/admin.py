import drf_hooks.admin
from django.contrib import admin

from meshapi_hooks.hooks import CeleryRecursiveSerializerHook

admin.site.unregister(CeleryRecursiveSerializerHook)


@admin.register(CeleryRecursiveSerializerHook)
class CeleryRecursiveSerializerHookAdmin(drf_hooks.admin.HookAdmin):
    fields = ("enabled", "user", "target", "event", "headers", "consecutive_failures")
    readonly_fields = ["consecutive_failures"]

    class Meta:
        model = CeleryRecursiveSerializerHook
