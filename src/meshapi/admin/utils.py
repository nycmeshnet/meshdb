from typing import Union
from urllib.parse import urljoin

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.urls import reverse

from meshapi.models import AccessPoint, Device, Sector


def get_admin_url(model: Model, site_base_url: str) -> str:
    """
    Get the admin URL corresponding to the given model
    """
    content_type = ContentType.objects.get_for_model(model.__class__)
    return urljoin(
        site_base_url,
        reverse(
            f"admin:{content_type.app_label}_{content_type.model}_change",
            args=(model.pk,),
        ).replace(
            "panel/", ""
        ),  # Strip "panel" out of admin URL. "Panel" views are meant to be shown
        # inside the admin panel iframe, and likely the user does not want that
    )


def downclass_device(device: Device) -> Union[Device, Sector, AccessPoint]:
    """
    Every sector and AP is also a device because we are using model inheritance. This function takes
    a device object and returns the leaf object that this device corresponds to.

    That is, it looks up the device ID in the sector and AP tables, and returns the appropriate
    object type if it exists. Returns the input device if no such leaf exists
    :param device: the device to use to search for leaf objects
    :return: the leaf object corresponding to this device
    """
    sector = Sector.objects.filter(device_ptr=device).first()
    access_point = AccessPoint.objects.filter(device_ptr=device).first()

    db_object = device
    if sector:
        db_object = sector
    elif access_point:
        db_object = access_point

    return db_object
