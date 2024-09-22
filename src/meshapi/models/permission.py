from django.db import models


class Permission(models.Model):
    class Meta:
        managed = False  # No database table creation or deletion  \
        # operations will be performed for this model.

        default_permissions = ()  # disable "add", "change", "delete"
        # and "view" default permissions

        permissions = (
            ("maintenance_mode", "Can toggle maintenance mode"),
            ("explorer_access", "Can access SQL Explorer"),
        )
