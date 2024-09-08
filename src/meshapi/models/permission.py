from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.contenttypes.models import ContentType
from django.db import models


# This is an abstract model that exists only so that we can create a ContentType
# for which can attach permissions to it.
# There is no database table created for it
class Permission(models.Model):
    class Meta:
        abstract = True


def sync_custom_permissions():
    content_type = ContentType.objects.get_for_model(
                                        Permission,
                                        for_concrete_model=False)

    permissions = [
        ("maintenance_mode", "Can toggle maintenance mode"),
    ]

    for codename, name in permissions:
        DjangoPermission.objects.get_or_create(name=name,
                                         codename=codename,
                                         content_type=content_type)

