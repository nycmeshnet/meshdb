from django.contrib import admin


class MeshDBAdminSite(admin.AdminSite):
    def get_app_list(self, request, app_label=None):
        """Reorder the apps in the admin site.

        By default, django admin apps are order alphabetically.

        To keep things organized, we want all the auth/metadata stuff to be listed before the
        actual models of the meshapi app

        And since django does not offer a simple way to order apps, we have to tinker
        with the default app list, to change the sorting
        """
        apps = super().get_app_list(request, app_label)

        SORT_OVERRIDES = {"auth": "0", "authtoken": "1", "meshapi_hooks": "2"}

        return sorted(
            apps,
            key=lambda x: SORT_OVERRIDES[x["app_label"]] if x["app_label"] in SORT_OVERRIDES else x["name"].lower(),
        )
