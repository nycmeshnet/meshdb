import uuid
from typing import Optional

from django.db import models
from django.db.models import F, FloatField, IntegerField

from meshapi.models.node import Node


class Device(models.Model):
    class Meta:
        ordering = [F("install_date").desc(nulls_last=True)]

    class DeviceStatus(models.TextChoices):
        INACTIVE = "Inactive"
        ACTIVE = "Active"
        POTENTIAL = "Potential"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    node = models.ForeignKey(
        Node,
        related_name="devices",
        on_delete=models.PROTECT,
        help_text="The logical node this Device is located within. This node's network_number field "
        "corresponds to the static IP address and OSPF ID of this device or the DHCP range it receives an "
        "address from. The network number is also usually found in the device name",
    )

    name = models.CharField(
        default=None,
        blank=True,
        null=True,
        help_text="The name of this device, usually configured as the hostname in the device firmware, "
        "usually in the format nycmesh-xxxx-yyyy-zzzz, where xxxx is the network number for "
        "the node this device is located at, yyyy is the type of the device, and zzzz is the "
        "network number of the other side of the link this device creates (if applicable)",
    )

    status = models.CharField(choices=DeviceStatus.choices, help_text="The current status of this device")

    install_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The date this device first became active on the mesh",
    )
    abandon_date = models.DateField(
        default=None,
        blank=True,
        null=True,
        help_text="The this device was abandoned, unplugged, or removed from service",
    )

    notes = models.TextField(
        default=None,
        blank=True,
        null=True,
        help_text="A free-form text description of this Device, to track any additional information. "
        "For imported Devices, this starts with a formatted block of information about the import process"
        "and original data. However this structure can be changed by admins at any time and should not be relied on"
        "by automated systems. ",
    )

    uisp_id = models.CharField(
        default=None, blank=True, null=True, help_text="The UUID used to indentify this device in UISP (if applicable)"
    )

    @property
    def network_number(self) -> IntegerField | Optional[int]:
        return self.node.network_number

    @property
    def latitude(self) -> FloatField | float:
        return self.node.latitude

    @property
    def longitude(self) -> FloatField | float:
        return self.node.longitude

    @property
    def altitude(self) -> Optional[FloatField | float]:
        return self.node.altitude

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"MeshDB Device ID {self.id}"
