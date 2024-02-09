from django.contrib.admin.apps import AdminConfig


class MeshDBAdminConfig(AdminConfig):
    default_site = "meshdb.admin.MeshDBAdminSite"
